import json
from pathlib import Path
from typing import Dict, Any, List, Optional
import httpx
from aegis.config import settings

_DEFAULT_MOCK_STATE = {
    "checkout-service": {
        "current_version": "2.4.1",  # Starts with faulty version
        "previous_version": "2.4.0",
        "deployed_at": "2026-09-21T11:30:00Z",
        "dependencies": ["postgres", "inventory-service", "payment-service", "redis"],
        "dependency_health": {
            "postgres": True,
            "inventory-service": True,
            "payment-service": True,
            "redis": True,
        },
        "versions": {
            "2.4.0": {
                "db_pool": 50,
                "health": True,
                "error_rate": 0.002,
                "latency_ms": 42.5,
                "logs": ["INFO request received", "INFO inventory checked", "INFO order placed successfully"],
            },
            "2.4.1": {
                "db_pool": 5,  # Fault: Exhausted under load
                "health": False,
                "error_rate": 0.385,
                "latency_ms": 2850.0,
                "logs": [
                    "INFO request received",
                    "ERROR timeout acquiring DB connection from pool (limit=5)",
                    "ERROR connection pool exhausted for checkout-service",
                    "ERROR checkout failed with HTTP 500: DatabaseTimeout",
                ],
            }
        }
    }
}

class AcmeClient:
    """
    Client for AcmeCloud simulated enterprise environment.
    Supports live REST communication or built-in mock simulation (for ITOPS-001 scenario).
    """

    def __init__(self, base_url: str = settings.ACME_CLOUD_API_URL, mock: bool = settings.MOCK_ACME_CLOUD):
        self.base_url = base_url
        self.mock = mock
        self._state_file = Path(__file__).resolve().parent.parent.parent / ".acme_state.json"
        self._last_loaded_mtime: float = 0.0

        # In-memory simulated AcmeCloud state (for ITOPS-001 scenario)
        self._mock_state: Dict[str, Any] = json.loads(json.dumps(_DEFAULT_MOCK_STATE))
        self._load_state()

    def _load_state(self) -> None:
        """Load state from disk if file exists and has been modified."""
        if not self.mock:
            return
        try:
            if self._state_file.is_file():
                mtime = self._state_file.stat().st_mtime
                if mtime > self._last_loaded_mtime:
                    with open(self._state_file, "r", encoding="utf-8") as f:
                        self._mock_state = json.load(f)
                    self._last_loaded_mtime = mtime
        except Exception:
            pass

    def _save_state(self) -> None:
        """Persist state to disk for cross-process synchronization."""
        if not self.mock:
            return
        try:
            with open(self._state_file, "w", encoding="utf-8") as f:
                json.dump(self._mock_state, f, indent=2)
            self._last_loaded_mtime = self._state_file.stat().st_mtime
        except Exception:
            pass

    def set_mock_version(self, service: str, version: str) -> None:
        """Explicitly set mock service version and persist."""
        self._load_state()
        if service in self._mock_state:
            self._mock_state[service]["current_version"] = version
            self._save_state()

    def reset_mock_state(self) -> None:
        """Reset mock state to default initial conditions."""
        self._mock_state = json.loads(json.dumps(_DEFAULT_MOCK_STATE))
        self._save_state()

    async def get_service_health(self, service: str) -> Dict[str, Any]:
        if self.mock:
            self._load_state()
            state = self._mock_state.get(service, {})
            v = state.get("current_version", "unknown")
            v_data = state.get("versions", {}).get(v, {})
            return {
                "service": service,
                "version": v,
                "healthy": v_data.get("health", True),
                "error_rate": v_data.get("error_rate", 0.0),
                "latency_ms": v_data.get("latency_ms", 0.0),
            }

        async with httpx.AsyncClient() as client:
            resp = await client.get(f"{self.base_url}/services/{service}/health")
            resp.raise_for_status()
            return resp.json()

    async def get_metrics(self, service: str, window: str = "15m") -> Dict[str, Any]:
        if self.mock:
            self._load_state()
            state = self._mock_state.get(service, {})
            v = state.get("current_version", "unknown")
            v_data = state.get("versions", {}).get(v, {})
            return {
                "service": service,
                "window": window,
                "error_rate": v_data.get("error_rate", 0.0),
                "latency_p95_ms": v_data.get("latency_ms", 0.0),
                "requests_per_sec": 120.0,
                "db_pool_active": v_data.get("db_pool", 50),
                "db_pool_max": v_data.get("db_pool", 50),
            }
        async with httpx.AsyncClient() as client:
            resp = await client.get(f"{self.base_url}/metrics/{service}?window={window}")
            resp.raise_for_status()
            return resp.json()

    async def get_logs(self, service: str, query: str = "error", window: str = "15m") -> List[str]:
        if self.mock:
            self._load_state()
            state = self._mock_state.get(service, {})
            v = state.get("current_version", "unknown")
            logs = state.get("versions", {}).get(v, {}).get("logs", [])
            return [line for line in logs if any(q in line.lower() for q in query.lower().split())]
        async with httpx.AsyncClient() as client:
            resp = await client.get(f"{self.base_url}/logs/{service}?query={query}&window={window}")
            resp.raise_for_status()
            return resp.json().get("logs", [])

    async def get_cmdb(self, service: str) -> Dict[str, Any]:
        if self.mock:
            self._load_state()
            state = self._mock_state.get(service, {})
            return {
                "service": service,
                "dependencies": state.get("dependencies", []),
                "dependency_health": state.get("dependency_health", {}),
            }
        async with httpx.AsyncClient() as client:
            resp = await client.get(f"{self.base_url}/cmdb/{service}")
            resp.raise_for_status()
            return resp.json()

    async def get_deployment_history(self, service: str) -> Dict[str, Any]:
        if self.mock:
            self._load_state()
            state = self._mock_state.get(service, {})
            return {
                "service": service,
                "current_version": state.get("current_version"),
                "previous_version": state.get("previous_version"),
                "deployed_at": state.get("deployed_at"),
                "recent_deployment": True,
            }
        async with httpx.AsyncClient() as client:
            resp = await client.get(f"{self.base_url}/deployments/{service}")
            resp.raise_for_status()
            return resp.json()

    async def rollback_deployment(self, service: str, target_version: str) -> Dict[str, Any]:
        if self.mock:
            self._load_state()
            if service in self._mock_state:
                old_version = self._mock_state[service]["current_version"]
                self._mock_state[service]["current_version"] = target_version
                self._save_state()
                return {
                    "status": "SUCCESS",
                    "service": service,
                    "previous_version": old_version,
                    "current_version": target_version,
                    "message": f"Successfully rolled back {service} from {old_version} to {target_version}.",
                }
            return {"status": "FAILED", "message": f"Service {service} not found."}
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{self.base_url}/remediation/rollback",
                json={"service": service, "target_version": target_version}
            )
            resp.raise_for_status()
            return resp.json()

acme_client = AcmeClient()
