"""
Scenario ITOPS-001: Bad Deployment on checkout-service
Demonstrates the complete end-to-end closed-loop incident resolution:
1. Fault introduction: checkout-service v2.4.1 has DB pool=5, leading to connection exhaustion.
2. Alert triggered -> Aegis triages (P1), investigates (detects DB pool exhaustion).
3. RAG retrieves RB-001 -> Diagnosis recommends rollback to v2.4.0.
4. Policy Engine flags HIGH risk -> pauses at PENDING_APPROVAL.
5. Human approves -> Remediation rolls back to v2.4.0 in AcmeCloud.
6. Verification verifies 0% error rate -> Incident marked RESOLVED.
"""

import sys
import asyncio

# Ensure utf-8 encoding on Windows terminal
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

from aegis.core.state import IncidentAlert, IncidentState
from aegis.graph.workflow import aegis_graph, remediate_node, verify_node
from aegis.core.tracer import tracer
from aegis.acme.client import acme_client

async def run_scenario_001():
    print("=" * 70)
    print("[SCENARIO ITOPS-001] Bad Deployment Incident Resolution")
    print("=" * 70)

    # 1. Check initial state of AcmeCloud
    initial_health = await acme_client.get_service_health("checkout-service")
    print(f"\n[AcmeCloud Initial State] checkout-service version: {initial_health['version']}")
    print(f"[AcmeCloud Initial State] Healthy: {initial_health['healthy']}, Error Rate: {initial_health['error_rate']:.1%}, Latency: {initial_health['latency_ms']}ms")

    # 2. Trigger Incident Alert
    alert = IncidentAlert(
        incident_id="INC-001",
        service="checkout-service",
        title="High 5xx Error Rate on Checkout Service",
        description="Checkout service is throwing 500 errors and request timeouts following recent release."
    )
    print(f"\n[Incident Alert] {alert.incident_id}: {alert.title}")

    # 3. Initialize State and invoke Aegis Graph
    state = IncidentState(
        incident_id=alert.incident_id,
        service=alert.service,
        severity=alert.severity,
        title=alert.title,
        description=alert.description
    )

    print("\n[Aegis Workflow Started] Running Triage -> Investigate -> Knowledge -> Diagnose -> Policy...")
    output = await aegis_graph.ainvoke(state)
    state = IncidentState(**{**state.model_dump(), **output})

    print(f"\n[Triage] Severity: {state.severity}")
    print(f"[Evidence] Current Version: {state.evidence.current_version} (Recent Deploy: {state.evidence.recent_deployment})")
    print(f"[Evidence] Error Logs: {state.evidence.error_logs[:2]}")
    print(f"[Knowledge] Top Runbook: {state.retrieved_runbooks[0].title} (Score: {state.retrieved_runbooks[0].score:.2f})")
    print(f"[Diagnosis] Root Cause: {state.diagnosis.root_cause}")
    print(f"[Diagnosis] Recommended Action: {state.diagnosis.recommended_action} -> {state.diagnosis.action_parameters}")
    print(f"[Policy Engine] Risk Level: {state.policy_evaluation.risk_level}, Decision: {state.policy_evaluation.decision}")
    print(f"[Status] {state.status}")

    # 4. Human Approval Boundary
    if state.status == "PENDING_APPROVAL":
        print("\n" + "-" * 70)
        print("[HUMAN OPERATOR APPROVAL REQUIRED]")
        print(f"Action: {state.diagnosis.recommended_action} to {state.diagnosis.action_parameters['target_version']}")
        print(f"Reason: {state.policy_evaluation.reason}")
        print(">>> Operator Decision: [ APPROVE ]")
        print("-" * 70)

        state.approval_granted = True
        state.approved_by = "LeadSRE"
        state.approval_reason = "Confirmed DB connection pool regression in v2.4.1. Approving immediate rollback."

        # 5. Resume Workflow: Remediate -> Verify
        print("\n[Remediation Agent] Executing rollback via Needle Executor...")
        rem_output = await remediate_node(state)
        state = IncidentState(**{**state.model_dump(), **rem_output})
        print(f"   Status: {state.remediation.status} - {state.remediation.message}")

        print("\n[Verification Agent] Checking service telemetry in AcmeCloud...")
        ver_output = await verify_node(state)
        state = IncidentState(**{**state.model_dump(), **ver_output})
        print(f"   Verification: {state.verification.status}")
        print(f"   Details: {state.verification.details}")
        print(f"\n[FINAL INCIDENT STATUS]: {state.status}")

    # 6. Print Traces
    print("\n" + "=" * 70)
    print("[LIGHTWEIGHT EVENT TRACE LOG]")
    trace_events = tracer.get_incident_trace(alert.incident_id)
    for event in trace_events:
        print(f"[{event['timestamp']}] Step: {event['step']} | Event: {event['event_type']}")
    print("=" * 70)

if __name__ == "__main__":
    asyncio.run(run_scenario_001())
