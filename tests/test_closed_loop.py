import pytest
import asyncio
from aegis.core.state import IncidentState
from aegis.policy.engine import policy_engine
from aegis.graph.workflow import aegis_graph, remediate_node, verify_node
from aegis.acme.client import acme_client

def test_policy_engine_guardrails():
    # 1. Read-only actions must be allowed immediately
    eval_ro = policy_engine.evaluate(action="get_metrics", target_service="checkout-service")
    assert eval_ro.decision == "ALLOW"
    assert eval_ro.requires_approval is False

    # 2. Forbidden actions must be denied
    eval_forbidden = policy_engine.evaluate(action="delete_incident", target_service="checkout-service")
    assert eval_forbidden.decision == "DENY"
    assert eval_forbidden.risk_level == "FORBIDDEN"

    # 3. High risk rollback in production without approval must require approval
    eval_rollback = policy_engine.evaluate(
        action="rollback_deployment",
        target_service="checkout-service",
        environment="production",
        has_approval=False
    )
    assert eval_rollback.decision == "REQUIRE_APPROVAL"
    assert eval_rollback.requires_approval is True

    # 4. Rollback with approval must be allowed
    eval_approved = policy_engine.evaluate(
        action="rollback_deployment",
        target_service="checkout-service",
        environment="production",
        has_approval=True
    )
    assert eval_approved.decision == "ALLOW"

def test_closed_loop_incident_resolution():
    async def _run():
        acme_client.set_mock_version("checkout-service", "2.4.1")
        state = IncidentState(
            incident_id="TEST-INC-001",
            service="checkout-service",
            severity="P1",
            title="High error rate on checkout",
            description="Checkout service failing with 500 errors"
        )

        # Run workflow up to approval boundary
        output = await aegis_graph.ainvoke(state)
        state = IncidentState(**{**state.model_dump(), **output})

        assert state.status == "PENDING_APPROVAL"
        assert state.diagnosis is not None
        assert state.diagnosis.recommended_action == "rollback_deployment"
        assert state.diagnosis.action_parameters["target_version"] == "2.4.0"

        # Operator approves
        state.approval_granted = True
        state.approved_by = "TestOperator"

        # Resume: Remediate -> Verify
        rem_output = await remediate_node(state)
        state = IncidentState(**{**state.model_dump(), **rem_output})
        assert state.remediation.status == "SUCCESS"

        ver_output = await verify_node(state)
        state = IncidentState(**{**state.model_dump(), **ver_output})
        assert state.verification.status == "SUCCESS"
        assert state.status == "RESOLVED"

    asyncio.run(_run())
