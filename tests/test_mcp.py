import pytest
import asyncio
from aegis.mcp.server import (
    mcp_server,
    get_service_logs,
    get_metrics,
    get_service_health,
    rollback_deployment,
    get_incident_state,
    list_incidents,
    service_health_resource,
    incident_resource,
    all_incidents_resource,
)
from aegis.mcp.client import AcmeMCPClient, mcp_client
from aegis.core.state import IncidentState
from aegis.graph.workflow import aegis_graph, remediate_node, verify_node


def test_mcp_server_direct_tools():
    async def _run():
        from aegis.acme.client import acme_client
        acme_client.set_mock_version("checkout-service", "2.4.1")

        # 1. get_metrics
        metrics = await get_metrics(service="checkout-service", window="15m")
        assert metrics["service"] == "checkout-service"
        assert "error_rate" in metrics
        assert "latency_p95_ms" in metrics
        assert "db_pool_active" in metrics

        # 2. get_service_logs
        logs = await get_service_logs(service="checkout-service", query="error", window="15m")
        assert isinstance(logs, list)
        assert len(logs) > 0
        assert any("error" in line.lower() or "pool" in line.lower() for line in logs)

        # 3. get_service_health
        health = await get_service_health(service="checkout-service")
        assert health["service"] == "checkout-service"
        assert health["version"] == "2.4.1"
        assert health["healthy"] is False

        # 4. get_incident_state known incident (must NOT leak ground truth)
        inc = await get_incident_state("INC-001")
        assert inc["incident_id"] == "INC-001"
        assert inc["service"] == "checkout-service"
        assert inc["severity"] == "P1"
        assert "recommended_action" not in inc
        assert "target_version" not in inc

        # 5. list_incidents
        incidents = await list_incidents()
        assert isinstance(incidents, list)
        assert len(incidents) >= 2
        assert any(i["incident_id"] == "INC-001" for i in incidents)

        # 6. get_incident_state unknown incident
        inc_unknown = await get_incident_state("INC-999")
        assert inc_unknown["status"] == "NOT_FOUND"

        # 7. rollback_deployment
        rb = await rollback_deployment(service="checkout-service", target_version="2.4.0")
        assert rb["status"] == "SUCCESS"
        assert rb["current_version"] == "2.4.0"

        # 8. get_service_health after rollback
        health_after = await get_service_health(service="checkout-service")
        assert health_after["healthy"] is True
        assert health_after["version"] == "2.4.0"

    asyncio.run(_run())


def test_mcp_server_resources():
    async def _run():
        health_json = await service_health_resource("checkout-service")
        assert "checkout-service" in health_json
        assert "healthy" in health_json

        inc_json = await incident_resource("INC-001")
        assert "INC-001" in inc_json

        all_inc_json = await all_incidents_resource()
        assert "INC-001" in all_inc_json
        assert "ITOPS-001" in all_inc_json

    asyncio.run(_run())


def test_mcp_client_adapter_direct():
    async def _run():
        from aegis.acme.client import acme_client
        acme_client.set_mock_version("checkout-service", "2.4.1")

        client = AcmeMCPClient(transport="direct")

        # List tools
        tools = await client.list_tools()
        tool_names = [t["name"] for t in tools]
        assert "get_service_logs" in tool_names
        assert "get_metrics" in tool_names
        assert "get_service_health" in tool_names
        assert "rollback_deployment" in tool_names
        assert "get_incident_state" in tool_names
        assert "list_incidents" in tool_names

        # get_metrics via client
        metrics = await client.get_metrics("checkout-service")
        assert metrics["service"] == "checkout-service"

        # get_service_logs via client
        logs = await client.get_service_logs("checkout-service", query="error")
        assert isinstance(logs, list)

        # get_service_health via client
        health = await client.get_service_health("checkout-service")
        assert health["service"] == "checkout-service"

        # rollback via client
        rb = await client.rollback_deployment("checkout-service", "2.4.0")
        assert rb["status"] == "SUCCESS"
        assert rb["current_version"] == "2.4.0"

        # get_incident_state via client
        inc = await client.get_incident_state("INC-001")
        assert inc["incident_id"] == "INC-001"

        # list_incidents via client
        incs = await client.list_incidents()
        assert len(incs) >= 2

    asyncio.run(_run())


def test_mcp_client_adapter_stdio():
    """Verify that out-of-process stdio transport works and state persists across subprocesses."""
    async def _run():
        from aegis.acme.client import acme_client
        acme_client.set_mock_version("checkout-service", "2.4.1")

        client = AcmeMCPClient(transport="stdio")

        # 1. List tools over stdio
        tools = await client.list_tools()
        tool_names = [t["name"] for t in tools]
        assert "get_service_logs" in tool_names
        assert "get_metrics" in tool_names
        assert "rollback_deployment" in tool_names
        assert "get_incident_state" in tool_names

        # 2. get_metrics over stdio
        metrics = await client.get_metrics("checkout-service")
        assert metrics["service"] == "checkout-service"
        assert metrics["error_rate"] > 0.1

        # 3. rollback_deployment over stdio (spawns subprocess)
        rb = await client.rollback_deployment("checkout-service", "2.4.0")
        assert rb["status"] == "SUCCESS"
        assert rb["current_version"] == "2.4.0"

        # 4. get_metrics in a subsequent subprocess (verifying cross-process state persistence)
        metrics_after = await client.get_metrics("checkout-service")
        assert metrics_after["error_rate"] < 0.01

        # 5. get_service_health in a subsequent subprocess
        health_after = await client.get_service_health("checkout-service")
        assert health_after["healthy"] is True
        assert health_after["version"] == "2.4.0"

    asyncio.run(_run())


def test_closed_loop_with_mcp_integration():
    """Verify that Aegis end-to-end closed loop runs with MCP client active."""
    async def _run():
        # Reset mock state to faulty version
        from aegis.acme.client import acme_client
        acme_client.set_mock_version("checkout-service", "2.4.1")

        state = IncidentState(
            incident_id="INC-001",
            service="checkout-service",
            severity="P1",
            title="High 5xx Error Rate on Checkout Service",
            description="Checkout service failing with 500 errors and connection pool exhaustion.",
        )

        # 1. Run graph up to approval boundary
        output = await aegis_graph.ainvoke(state)
        state = IncidentState(**{**state.model_dump(), **output})

        assert state.status == "PENDING_APPROVAL"
        assert state.diagnosis.recommended_action == "rollback_deployment"
        assert state.diagnosis.action_parameters["target_version"] == "2.4.0"

        # 2. Operator approval
        state.approval_granted = True
        state.approved_by = "LeadSRE"

        # 3. Remediate (invokes needle_executor -> mcp_client -> mcp_server)
        rem_output = await remediate_node(state)
        state = IncidentState(**{**state.model_dump(), **rem_output})
        assert state.remediation.status == "SUCCESS"

        # 4. Verify (invokes verify_node -> mcp_client.get_service_health)
        ver_output = await verify_node(state)
        state = IncidentState(**{**state.model_dump(), **ver_output})
        assert state.verification.status == "SUCCESS"
        assert state.status == "RESOLVED"

    asyncio.run(_run())

