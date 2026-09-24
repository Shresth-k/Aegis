"""
AcmeCloud MCP Server.
Provides standardized Model Context Protocol (MCP) tools and resources for:
1. Log inspection (get_service_logs)
2. Telemetry metrics retrieval (get_metrics)
3. Deployment remediation (rollback_deployment)
4. Incident lifecycle state inspection (get_incident_state)
"""

from __future__ import annotations

import sys
import os
import json
import shutil
import subprocess
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone

# Support MCP 2.x (MCPServer) with fallback to FastMCP and in-memory mock
try:
    from mcp.server.mcpserver import MCPServer as FastMCP
except ImportError:
    try:
        from mcp.server.fastmcp import FastMCP
    except ImportError:
        class ToolInfo:
            def __init__(self, name: str, description: str = "", inputSchema: Optional[Dict[str, Any]] = None):
                self.name = name
                self.description = description
                self.inputSchema = inputSchema or {}

        class FastMCP:
            def __init__(self, name="acmecloud", instructions=""):
                self.name = name
                self.instructions = instructions
                self._tools = {}
                self._resources = {}

            def tool(self, name=None):
                def decorator(fn):
                    tool_name = name or fn.__name__
                    self._tools[tool_name] = fn
                    return fn
                return decorator

            def resource(self, uri=None):
                def decorator(fn):
                    res_name = uri or fn.__name__
                    self._resources[res_name] = fn
                    return fn
                return decorator

            async def list_tools(self):
                return [
                    ToolInfo(name=name, description=fn.__doc__ or "")
                    for name, fn in self._tools.items()
                ]

            async def call_tool(self, name: str, arguments: dict):
                fn = self._tools.get(name)
                if not fn:
                    raise ValueError(f"Tool {name} not found")
                import inspect
                if inspect.iscoroutinefunction(fn):
                    return await fn(**arguments)
                return fn(**arguments)

            def run(self, *args, **kwargs):
                pass

from aegis.config import settings
from aegis.acme.client import acme_client

# Initialize AcmeCloud MCP Server
mcp_server = FastMCP(
    name="acmecloud",
    instructions="AcmeCloud Enterprise Operational MCP Server. Provides tools for telemetry, logs, rollback, and incident state.",
)

# Operational incident store backing get_incident_state
_DEFAULT_INCIDENTS: Dict[str, Dict[str, Any]] = {
    "INC-001": {
        "incident_id": "INC-001",
        "service": "checkout-service",
        "environment": "production",
        "severity": "P1",
        "status": "OPEN",
        "summary": "High 5xx Error Rate and connection timeouts on checkout-service following 2.4.1 release.",
        "created_at": "2026-09-21T11:35:00Z",
        "active_version": "2.4.1",
    },
    "ITOPS-001": {
        "incident_id": "ITOPS-001",
        "service": "checkout-service",
        "environment": "production",
        "severity": "P1",
        "status": "OPEN",
        "summary": "Scenario ITOPS-001: Connection pool starvation under load in checkout-service v2.4.1.",
        "created_at": "2026-09-21T11:30:00Z",
        "active_version": "2.4.1",
    },
    "INC-002": {
        "incident_id": "INC-002",
        "service": "payment-gateway",
        "environment": "production",
        "severity": "P1",
        "status": "OPEN",
        "summary": "Payment gateway socket timeout and upstream circuit breaker open.",
        "created_at": "2026-09-21T12:00:00Z",
        "active_version": "2.4.4",
    },
    "INC-003": {
        "incident_id": "INC-003",
        "service": "inventory-service",
        "environment": "production",
        "severity": "P2",
        "status": "OPEN",
        "summary": "Elevated Redis memory pressure and cache eviction cascade.",
        "created_at": "2026-09-21T12:15:00Z",
        "active_version": "2.4.2",
    },
}

_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
_INCIDENTS_FILE = _PROJECT_ROOT / ".acme_incidents.json"
_last_incidents_mtime: float = 0.0
_incidents_store: Dict[str, Dict[str, Any]] = json.loads(json.dumps(_DEFAULT_INCIDENTS))


def _load_incidents() -> Dict[str, Dict[str, Any]]:
    global _incidents_store, _last_incidents_mtime
    try:
        if _INCIDENTS_FILE.is_file():
            mtime = _INCIDENTS_FILE.stat().st_mtime
            if mtime > _last_incidents_mtime:
                with open(_INCIDENTS_FILE, "r", encoding="utf-8") as f:
                    _incidents_store = json.load(f)
                _last_incidents_mtime = mtime
    except Exception:
        pass
    return _incidents_store


def _save_incidents(data: Optional[Dict[str, Any]] = None) -> None:
    global _incidents_store, _last_incidents_mtime
    try:
        if data is not None:
            _incidents_store = data
        with open(_INCIDENTS_FILE, "w", encoding="utf-8") as f:
            json.dump(_incidents_store, f, indent=2)
        _last_incidents_mtime = _INCIDENTS_FILE.stat().st_mtime
    except Exception:
        pass


@mcp_server.tool()
async def get_service_logs(
    service: str,
    query: str = "error",
    window: str = "15m",
) -> List[str]:
    """
    Retrieve service log entries matching query filters and time window from AcmeCloud.

    Args:
        service: Name of the target service (e.g. 'checkout-service').
        query: Filter query string (e.g. 'error', 'timeout', 'connection').
        window: Time window string (e.g. '15m', '1h').

    Returns:
        List of matching log line strings.
    """
    return await acme_client.get_logs(service=service, query=query, window=window)


@mcp_server.tool()
async def get_metrics(
    service: str,
    window: str = "15m",
) -> Dict[str, Any]:
    """
    Fetch operational telemetry metrics for a service (error rate, p95 latency,
    request volume, and database connection pool statistics).

    Args:
        service: Name of the service to inspect (e.g. 'checkout-service').
        window: Metric aggregation window (e.g. '15m', '5m').

    Returns:
        Dictionary containing error_rate, latency_p95_ms, requests_per_sec, and db_pool statistics.
    """
    return await acme_client.get_metrics(service=service, window=window)


@mcp_server.tool()
async def get_service_health(
    service: str,
) -> Dict[str, Any]:
    """
    Retrieve operational health status and basic metrics for a service in AcmeCloud.

    Args:
        service: Name of the target service (e.g. 'checkout-service').

    Returns:
        Dictionary containing service name, version, healthy status, error_rate, and latency_ms.
    """
    return await acme_client.get_service_health(service)


@mcp_server.tool()
async def rollback_deployment(
    service: str,
    target_version: str,
) -> Dict[str, Any]:
    """
    Execute a deployment rollback for a service to a specified target version in AcmeCloud.
    Updates the active deployment version and restores operational health.

    Args:
        service: Name of the service to rollback (e.g. 'checkout-service').
        target_version: The target version to deploy (e.g. '2.4.0').

    Returns:
        Dictionary with status ('SUCCESS' or 'FAILED'), previous_version, current_version, and message.
    """
    # 1. Apply rollback in AcmeClient
    result = await acme_client.rollback_deployment(service=service, target_version=target_version)

    # 2. Update active incidents associated with this service
    incidents = _load_incidents()
    for inc_id, inc_data in incidents.items():
        if inc_data.get("service") == service and inc_data.get("status") == "OPEN":
            inc_data["status"] = "RESOLVED"
            inc_data["active_version"] = target_version
            inc_data["resolved_at"] = datetime.now(timezone.utc).isoformat()
    _save_incidents()

    # 3. If Docker Compose controller is available and not pure mock, attempt container recreation
    docker_applied = False
    docker_detail = None
    if not settings.MOCK_ACME_CLOUD:
        try:
            acme_dir = _PROJECT_ROOT / "acmecloud"
            compose_file = acme_dir / "docker-compose.yml"
            deployments_root = acme_dir / "simulator" / "deployments"
            if compose_file.is_file() and deployments_root.is_dir():
                if str(acme_dir) not in sys.path:
                    sys.path.insert(0, str(acme_dir))
                from simulator.scenarios.deployment import DockerComposeDeploymentController
                controller = DockerComposeDeploymentController(
                    compose_file=compose_file,
                    deployments_root=deployments_root,
                    project_root=acme_dir,
                )
                dep_res = controller.deploy(service, target_version)
                docker_applied = True
                docker_detail = f"Docker Compose recreated {dep_res.service} with {dep_res.deployment_file.name}"
        except Exception as exc:
            docker_detail = f"Docker Compose notice: {exc}"
            if settings.DEBUG:
                print(f"[AcmeCloud MCP] Docker Compose rollback notice: {exc}")

    result["execution_mode"] = "DOCKER_COMPOSE" if docker_applied else "SIMULATED_STATE"
    if docker_detail:
        result["docker_detail"] = docker_detail

    return result


@mcp_server.tool()
async def docker_ps(all_containers: bool = False) -> List[Dict[str, Any]]:
    """
    Inspect containers on the host Docker daemon.
    Returns status, image, and port mappings for services like acmecloud-checkout and postgres.

    Args:
        all_containers: If True, list all stopped and running containers (-a).

    Returns:
        List of container metadata objects.
    """
    docker_bin = shutil.which("docker")
    if not docker_bin:
        from aegis.acme.client import acme_client
        acme_client._load_state()
        state = acme_client._mock_state.get("checkout-service", {})
        curr_ver = state.get("current_version", "2.4.0")
        is_healthy = state.get("versions", {}).get(curr_ver, {}).get("health", True)
        return [
            {
                "ID": "c8f190ab4e12",
                "Names": "acmecloud-checkout",
                "Image": f"us-central1-docker.pkg.dev/aegis-509604/aegis-repo/acme-checkout:v{curr_ver}",
                "Status": f"Up 18 minutes ({'Healthy' if is_healthy else 'Degraded - Elevated Latency/Errors'})",
                "Ports": "0.0.0.0:8080->8080/tcp",
                "State": "running",
            },
            {
                "ID": "d4a77e119bc3",
                "Names": "acmecloud-postgres",
                "Image": "postgres:15-alpine",
                "Status": "Up 2 hours (Healthy)",
                "Ports": "0.0.0.0:5432->5432/tcp",
                "State": "running",
            },
            {
                "ID": "f9011ba42e5a",
                "Names": "acmecloud-prometheus",
                "Image": "prom/prometheus:v2.48.0",
                "Status": "Up 2 hours (Healthy)",
                "Ports": "0.0.0.0:9090->9090/tcp",
                "State": "running",
            }
        ]

    cmd = [docker_bin, "ps", "--format", "{{json .}}"]
    if all_containers:
        cmd.insert(2, "-a")

    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
        if proc.returncode != 0:
            return [{"status": "ERROR", "message": proc.stderr.strip() or "Failed to run docker ps"}]

        containers = []
        for line in proc.stdout.strip().split("\n"):
            line = line.strip()
            if line:
                try:
                    containers.append(json.loads(line))
                except Exception:
                    containers.append({"raw": line})
        return containers
    except Exception as exc:
        return [{"status": "ERROR", "message": str(exc)}]


@mcp_server.tool()
async def docker_logs(container_name: str, tail: int = 50) -> List[str]:
    """
    Retrieve real-time stdout and stderr logs directly from a Docker container.

    Args:
        container_name: Target container name or ID (e.g. 'acmecloud-checkout', 'acmecloud-postgres').
        tail: Number of trailing log lines to retrieve (default: 50).

    Returns:
        List of log line strings.
    """
    docker_bin = shutil.which("docker")
    if not docker_bin:
        from aegis.acme.client import acme_client
        service_name = "checkout-service" if "checkout" in container_name else "postgres"
        logs = await acme_client.get_logs(service=service_name, query="", window="15m")
        if logs:
            return logs[-tail:]
        return [f"Container {container_name} is operating normally with no critical error logs."]

    cmd = [docker_bin, "logs", "--tail", str(tail), container_name]
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
        output = (proc.stdout or "") + (proc.stderr or "")
        return [line for line in output.split("\n") if line.strip()]
    except Exception as exc:
        return [f"Error retrieving docker logs for {container_name}: {exc}"]


@mcp_server.tool()
async def docker_restart_container(container_name: str) -> Dict[str, Any]:
    """
    Restart an individual container via the host Docker daemon.

    Args:
        container_name: Target container name (e.g. 'acmecloud-checkout').

    Returns:
        Dictionary with status ('SUCCESS' or 'FAILED') and details.
    """
    docker_bin = shutil.which("docker")
    if not docker_bin:
        from aegis.acme.client import acme_client
        service_name = "checkout-service" if "checkout" in container_name else ("postgres" if "postgres" in container_name else container_name)
        res = await acme_client.restart_service(service_name)
        return {
            "status": "SUCCESS",
            "container": container_name,
            "message": res.get("message", f"Container {container_name} restarted successfully."),
        }

    cmd = [docker_bin, "restart", container_name]
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        if proc.returncode == 0:
            return {
                "status": "SUCCESS",
                "container": container_name,
                "message": f"Container {container_name} restarted successfully.",
            }
        return {
            "status": "FAILED",
            "container": container_name,
            "message": proc.stderr.strip() or "Restart command returned non-zero code.",
        }
    except Exception as exc:
        return {"status": "FAILED", "container": container_name, "message": str(exc)}


@mcp_server.tool()
async def get_incident_state(
    incident_id: str,
) -> Dict[str, Any]:
    """
    Query the current status, severity, timeline, and details of an operational incident.

    Args:
        incident_id: Identifier of the incident (e.g. 'INC-001', 'ITOPS-001').

    Returns:
        Dictionary containing incident_id, service, environment, severity, status, summary, and timestamps.
    """
    incidents = _load_incidents()
    if incident_id in incidents:
        return dict(incidents[incident_id])

    # Check acmecloud simulator InMemoryIncidentStore if imported
    try:
        acme_dir = _PROJECT_ROOT / "acmecloud"
        if str(acme_dir) not in sys.path:
            sys.path.insert(0, str(acme_dir))
        from simulator.scenarios.incident import InMemoryIncidentStore
    except Exception:
        pass

    # Fallback for unknown incident
    return {
        "incident_id": incident_id,
        "status": "NOT_FOUND",
        "message": f"Incident {incident_id} not found in AcmeCloud incident store.",
    }


@mcp_server.tool()
async def list_incidents() -> List[Dict[str, Any]]:
    """
    List all operational incidents in AcmeCloud.

    Returns:
        List of incident records.
    """
    incidents = _load_incidents()
    return list(incidents.values())


@mcp_server.resource("acme://services/{service}/health")
async def service_health_resource(service: str) -> str:
    """Read the current operational health of a service."""
    health = await acme_client.get_service_health(service)
    return json.dumps(health, indent=2)


@mcp_server.resource("acme://incidents")
async def all_incidents_resource() -> str:
    """Read all operational incident records."""
    incidents = _load_incidents()
    return json.dumps(list(incidents.values()), indent=2)


@mcp_server.resource("acme://incidents/{incident_id}")
async def incident_resource(incident_id: str) -> str:
    """Read an operational incident record."""
    inc = await get_incident_state(incident_id)
    return json.dumps(inc, indent=2)


if __name__ == "__main__":
    # Run the MCP server over stdio
    mcp_server.run()
