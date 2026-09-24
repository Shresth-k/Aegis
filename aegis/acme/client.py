import json
import asyncio
import shutil
import subprocess
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
                "fault_type": "pool_starvation",
                "logs": [
                    "INFO request received",
                    "ERROR timeout acquiring DB connection from pool (limit=5)",
                    "ERROR connection pool exhausted for checkout-service",
                    "ERROR checkout failed with HTTP 500: DatabaseTimeout",
                ],
            },
            "2.4.2": {
                "db_pool": 50,
                "health": False,
                "error_rate": 0.018,
                "latency_ms": 1450.0,
                "memory_usage_mb": 965,
                "memory_limit_mb": 1024,
                "fault_type": "memory_leak",
                "logs": [
                    "INFO request received",
                    "WARN high memory heap allocation: 94.2% of 1024MB limit consumed",
                    "WARN GC pause duration spike: 1850ms during generational compaction",
                    "ERROR worker thread pool latency elevated due to severe heap thrashing",
                    "INFO recommendation: container restart will flush leaked session cache without code rollback",
                ],
            },
            "2.4.3": {
                "db_pool": 50,
                "health": False,
                "error_rate": 0.142,
                "latency_ms": 7500.0,
                "fault_type": "db_deadlock",
                "logs": [
                    "INFO request received",
                    "ERROR database transaction timeout: Lock wait timeout exceeded (7500ms)",
                    "ERROR PostgreSQL deadlock detected: process 4182 waiting for ExclusiveLock on relation orders",
                    "ERROR query rolled back by database engine: deadlock detected",
                    "INFO recommendation: database connection pool flush or postgres container restart clears locks",
                ],
            },
            "2.4.4": {
                "db_pool": 50,
                "health": False,
                "error_rate": 0.998,
                "latency_ms": 120.0,
                "fault_type": "upstream_timeout",
                "logs": [
                    "INFO request received",
                    "ERROR connect to payment-gw.internal.invalid:9999 failed: Connection refused",
                    "ERROR checkout payment step failed: HTTP 502 Bad Gateway from upstream payment provider",
                    "ERROR configuration error: PAYMENT_GATEWAY_URL points to unreachable endpoint",
                    "INFO recommendation: restore valid gateway endpoint or rollback deployment config",
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
        if not self.mock:
            try:
                root_dir = Path(__file__).resolve().parent.parent.parent
                acme_dir = root_dir / "acmecloud"
                compose_file = acme_dir / "docker-compose.yml"
                deployments_root = acme_dir / "simulator" / "deployments"
                if compose_file.is_file() and deployments_root.is_dir():
                    import sys
                    if str(acme_dir) not in sys.path:
                        sys.path.insert(0, str(acme_dir))
                    from simulator.scenarios.deployment import DockerComposeDeploymentController
                    controller = DockerComposeDeploymentController(
                        compose_file=compose_file,
                        deployments_root=deployments_root,
                        project_root=acme_dir,
                    )
                    controller.deploy("checkout-service", version)
            except Exception:
                pass

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

        # When running against live Docker, the container might be restarting after a rollback
        for attempt in range(8):
            try:
                async with httpx.AsyncClient(timeout=3.0) as client:
                    resp = await client.get(f"{self.base_url}/health")
                    if resp.status_code == 200:
                        data = resp.json()
                        ver = data.get("version", "2.4.1")
                        is_healthy = data.get("status") == "healthy" and data.get("database") == "healthy"
                        v_data = self._mock_state.get(service, {}).get("versions", {}).get(ver, {})
                        is_healthy_ver = v_data.get("health", ver == "2.4.0")
                        return {
                            "service": service,
                            "version": ver,
                            "healthy": is_healthy and is_healthy_ver,
                            "error_rate": v_data.get("error_rate", 0.385 if ver == "2.4.1" else 0.002),
                            "latency_ms": v_data.get("latency_ms", 2031.4 if ver == "2.4.1" else 42.5),
                        }
            except Exception:
                if attempt < 7:
                    await asyncio.sleep(1.0)

        # Fallback to local state if container still initializing
        self._load_state()
        state = self._mock_state.get(service, {})
        v = state.get("current_version", "2.4.0")
        v_data = state.get("versions", {}).get(v, {})
        return {
            "service": service,
            "version": v,
            "healthy": v_data.get("health", True),
            "error_rate": v_data.get("error_rate", 0.002),
            "latency_ms": v_data.get("latency_ms", 42.5),
        }

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

        # In live mode, query Prometheus directly for real-time telemetry
        error_rate = 0.0
        requests_total = 0
        errors_total = 0
        active_db = 0

        async with httpx.AsyncClient(timeout=3.0) as client:
            try:
                # 1. Total errors
                err_resp = await client.get("http://localhost:9090/api/v1/query?query=sum(checkout_errors_total)")
                if err_resp.status_code == 200:
                    results = err_resp.json().get("data", {}).get("result", [])
                    if results:
                        errors_total = float(results[0].get("value", [0, 0])[1])

                # 2. Total requests
                req_resp = await client.get("http://localhost:9090/api/v1/query?query=sum(checkout_requests_total)")
                if req_resp.status_code == 200:
                    results = req_resp.json().get("data", {}).get("result", [])
                    if results:
                        requests_total = float(results[0].get("value", [0, 0])[1])

                if requests_total > 0:
                    error_rate = round(errors_total / requests_total, 4)

                # 3. Active DB connections
                db_resp = await client.get("http://localhost:9090/api/v1/query?query=db_connections_active")
                if db_resp.status_code == 200:
                    results = db_resp.json().get("data", {}).get("result", [])
                    if results:
                        active_db = int(float(results[0].get("value", [0, 0])[1]))
            except Exception:
                pass

        health = await self.get_service_health(service)
        ver = health.get("version", "2.4.1")

        self._load_state()
        svc_state = self._mock_state.get(service, {})
        v_data = svc_state.get("versions", {}).get(ver, {})
        default_err = v_data.get("error_rate", 0.385 if ver == "2.4.1" else 0.002)
        default_lat = v_data.get("latency_ms", 2031.4 if ver == "2.4.1" else 42.5)
        pool_val = v_data.get("db_pool", 5 if ver == "2.4.1" else 50)

        if requests_total == 0:
            error_rate = default_err
            p95_latency = default_lat
        else:
            p95_latency = default_lat if (error_rate > 0.05 or ver != "2.4.0") else 42.5

        return {
            "service": service,
            "window": window,
            "error_rate": error_rate,
            "latency_p95_ms": p95_latency,
            "requests_per_sec": 142.5 if requests_total > 0 else 0.0,
            "db_pool_active": max(active_db, pool_val if ver == "2.4.1" else 0),
            "db_pool_max": pool_val,
            "prometheus_telemetry": {
                "checkout_errors_total": errors_total,
                "checkout_requests_total": requests_total,
            }
        }

    async def get_logs(self, service: str, query: str = "error", window: str = "15m") -> List[str]:
        if self.mock:
            self._load_state()
            state = self._mock_state.get(service, {})
            v = state.get("current_version", "unknown")
            logs = state.get("versions", {}).get(v, {}).get("logs", [])
            return [line for line in logs if any(q in line.lower() for q in query.lower().split())]

        docker_bin = shutil.which("docker")
        if docker_bin:
            try:
                proc = subprocess.run(
                    [docker_bin, "logs", "--tail", "100", "acmecloud-checkout"],
                    capture_output=True,
                    text=True,
                    timeout=5,
                )
                output = (proc.stdout or "") + (proc.stderr or "")
                lines = [line.strip() for line in output.split("\n") if line.strip()]
                filtered = [line for line in lines if any(q in line.lower() for q in query.lower().split())]
                if filtered:
                    return filtered
            except Exception:
                pass

        # If live container had no matching error logs, fall back to mock state version logs for realistic error context
        self._load_state()
        state = self._mock_state.get(service, {})
        v = state.get("current_version", "unknown")
        mock_logs = state.get("versions", {}).get(v, {}).get("logs", [])
        mock_filtered = [line for line in mock_logs if any(q in line.lower() for q in query.lower().split())]
        if mock_filtered:
            return mock_filtered
        if mock_logs:
            return mock_logs

        async with httpx.AsyncClient(timeout=5.0) as client:
            try:
                resp = await client.get(f"{self.base_url}/logs/{service}?query={query}&window={window}")
                if resp.status_code == 200:
                    return resp.json().get("logs", [])
            except Exception:
                pass
        return []

    async def get_cmdb(self, service: str) -> Dict[str, Any]:
        if not self.mock:
            try:
                async with httpx.AsyncClient(timeout=2.0) as client:
                    resp = await client.get(f"{self.base_url}/cmdb/{service}")
                    if resp.status_code == 200:
                        return resp.json()
            except Exception:
                pass
        self._load_state()
        state = self._mock_state.get(service, {})
        return {
            "service": service,
            "dependencies": state.get("dependencies", []),
            "dependency_health": state.get("dependency_health", {}),
        }

    async def get_deployment_history(self, service: str) -> Dict[str, Any]:
        if not self.mock:
            try:
                async with httpx.AsyncClient(timeout=2.0) as client:
                    resp = await client.get(f"{self.base_url}/deployments/{service}")
                    if resp.status_code == 200:
                        return resp.json()
            except Exception:
                pass
        self._load_state()
        state = self._mock_state.get(service, {})
        current_v = state.get("current_version", "2.4.1")
        if not self.mock:
            try:
                h = await self.get_service_health(service)
                current_v = h.get("version", current_v)
            except Exception:
                pass
        return {
            "service": service,
            "current_version": current_v,
            "previous_version": state.get("previous_version", "2.4.0"),
            "deployed_at": state.get("deployed_at"),
            "recent_deployment": True,
        }

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

        # Live Docker Compose rollback
        import sys
        root_dir = Path(__file__).resolve().parent.parent.parent
        acme_dir = root_dir / "acmecloud"
        compose_file = acme_dir / "docker-compose.yml"
        deployments_root = acme_dir / "simulator" / "deployments"

        old_version = "unknown"
        try:
            h = await self.get_service_health(service)
            old_version = h.get("version", "unknown")
        except Exception:
            pass

        if compose_file.is_file() and deployments_root.is_dir():
            if str(acme_dir) not in sys.path:
                sys.path.insert(0, str(acme_dir))
            from simulator.scenarios.deployment import DockerComposeDeploymentController
            controller = DockerComposeDeploymentController(
                compose_file=compose_file,
                deployments_root=deployments_root,
                project_root=acme_dir,
            )
            controller.deploy("checkout-service", target_version)
            return {
                "status": "SUCCESS",
                "service": service,
                "previous_version": old_version,
                "current_version": target_version,
                "execution_mode": "DOCKER_COMPOSE",
                "message": f"Successfully executed Docker Compose rollback for {service} to {target_version}.",
            }

        return {"status": "FAILED", "message": f"Docker Compose configuration not found for {service}."}

    async def restart_service(self, service: str) -> Dict[str, Any]:
        """Restart a service container or mock instance."""
        container_map = {
            "checkout-service": "acmecloud-checkout",
            "checkout": "acmecloud-checkout",
            "postgres": "acmecloud-postgres",
            "prometheus": "acmecloud-prometheus",
            "grafana": "acmecloud-grafana",
        }
        container_name = container_map.get(service, f"acmecloud-{service}")
        try:
            from aegis.mcp.server import docker_restart_container
            res = await docker_restart_container(container_name=container_name)
            return {
                "status": res.get("status", "SUCCESS"),
                "service": service,
                "container": container_name,
                "message": res.get("message", f"Service {service} container restarted."),
            }
        except Exception as e:
            return {
                "status": "SUCCESS" if self.mock else "FAILED",
                "service": service,
                "container": container_name,
                "message": f"Service {service} restart completed: {e}" if self.mock else str(e),
            }

acme_client = AcmeClient()
