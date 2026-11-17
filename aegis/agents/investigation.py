from typing import Dict, Any
from aegis.core.state import TelemetryEvidence
from aegis.config import settings
from aegis.acme.client import acme_client
from aegis.mcp.client import mcp_client

class InvestigationAgent:
    """
    Investigation Agent.
    Gathers operational telemetry (metrics, logs, deployments, CMDB) from AcmeCloud
    and packages it into a coherent evidence bundle.
    """

    @classmethod
    async def investigate(cls, service: str) -> TelemetryEvidence:
        # 1. Fetch deployment history
        deploy_info = await acme_client.get_deployment_history(service)
        current_version = deploy_info.get("current_version", "unknown")
        previous_version = deploy_info.get("previous_version")
        recent_deployment = deploy_info.get("recent_deployment", False)

        # 2. Query metrics (via MCP or direct client)
        if settings.USE_MCP:
            metrics = await mcp_client.get_metrics(service, window="15m")
            error_logs = await mcp_client.get_service_logs(service, query="error timeout connection", window="15m")
        else:
            metrics = await acme_client.get_metrics(service, window="15m")
            error_logs = await acme_client.get_logs(service, query="error timeout connection", window="15m")

        # 4. Query CMDB dependencies
        cmdb = await acme_client.get_cmdb(service)
        dependencies = cmdb.get("dependencies", [])
        dep_health = cmdb.get("dependency_health", {})

        return TelemetryEvidence(
            service=service,
            current_version=current_version,
            previous_version=previous_version,
            recent_deployment=recent_deployment,
            metrics=metrics,
            error_logs=error_logs,
            dependencies=dependencies,
            dependency_health=dep_health,
        )

investigation_agent = InvestigationAgent()
