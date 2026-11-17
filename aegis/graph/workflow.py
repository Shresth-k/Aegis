import asyncio
from typing import Dict, Any, Callable, List, Optional
from uuid import uuid4
from aegis.core.state import (
    IncidentState,
    PolicyEvaluation,
    RemediationResult,
    VerificationResult
)
from aegis.core.tracer import tracer
from aegis.triage.jev_triage import jev_triage
from aegis.agents.investigation import investigation_agent
from aegis.rag.retriever import runbook_retriever
from aegis.rag.jev_reranker import jev_reranker
from aegis.agents.diagnosis import diagnosis_agent
from aegis.policy.engine import policy_engine
from aegis.config import settings
from aegis.executor.needle_executor import needle_executor
from aegis.acme.client import acme_client
from aegis.mcp.client import mcp_client

END = "__END__"


class AegisStateGraph:
    """
    Lightweight, high-performance asynchronous state graph engine.
    Mirrors LangGraph semantics without heavy framework dependencies,
    enabling sub-millisecond node transitions and clear auditability.
    """

    def __init__(self, state_schema):
        self.state_schema = state_schema
        self.nodes: Dict[str, Callable] = {}
        self.edges: Dict[str, str] = {}
        self.conditional_edges: Dict[str, tuple[Callable, Dict[str, str]]] = {}
        self.entry_point: Optional[str] = None

    def add_node(self, name: str, func: Callable):
        self.nodes[name] = func

    def set_entry_point(self, name: str):
        self.entry_point = name

    def add_edge(self, from_node: str, to_node: str):
        self.edges[from_node] = to_node

    def add_conditional_edges(self, from_node: str, condition_func: Callable, path_map: Dict[str, str]):
        self.conditional_edges[from_node] = (condition_func, path_map)

    def compile(self):
        return self

    async def ainvoke(self, state: IncidentState, on_event: Optional[Callable[[str, str, IncidentState], Any]] = None) -> Dict[str, Any]:
        current_node = self.entry_point
        state_dict = state.model_dump()
        run_id = uuid4().hex
        event_index = 0

        while current_node and current_node != END:
            node_fn = self.nodes.get(current_node)
            if not node_fn:
                break

            # Execute node
            current_state = self.state_schema(**state_dict)
            execution_id = f"{state.incident_id}:{run_id}:{event_index}"
            event_index += 1
            tracer.log_event(state.incident_id, current_node, "AGENT_STARTED", {
                "execution_id": execution_id,
                "name": current_node,
                "kind": "agent",
                "args": {"incident_id": state.incident_id, "service": state.service},
            })
            if on_event:
                await on_event(current_node, "start", current_state)
            try:
                updates = await node_fn(current_state)
            except Exception as exc:
                tracer.log_event(state.incident_id, current_node, "AGENT_COMPLETED", {
                    "execution_id": execution_id,
                    "name": current_node,
                    "kind": "agent",
                    "status": "FAILED",
                    "flow_status": "ESCALATED",
                    "output": {"error": str(exc)},
                })
                raise
            if updates:
                state_dict.update(updates)
                # Keep the incident object in the API's live store current while
                # awaited agents run. This preserves partial progress if a later
                # tool fails and lets the incident SSE stream report real state.
                for field_name, value in updates.items():
                    setattr(state, field_name, value)
                current_state = self.state_schema(**state_dict)
            tracer.log_event(state.incident_id, current_node, "AGENT_COMPLETED", {
                "execution_id": execution_id,
                "name": current_node,
                "kind": "agent",
                "status": "DONE",
                "flow_status": updates.get("status") if updates else current_state.status,
                "output": updates or {},
            })
            if on_event:
                await on_event(current_node, "complete", current_state)

            # Check conditional edge
            if current_node in self.conditional_edges:
                cond_fn, path_map = self.conditional_edges[current_node]
                decision = cond_fn(current_state)
                next_node = path_map.get(decision, END)
            else:
                next_node = self.edges.get(current_node, END)

            current_node = next_node

        return state_dict

# --- Graph Nodes ---

async def triage_node(state: IncidentState) -> Dict[str, Any]:
    severity, domain, conf = await jev_triage.triage_incident(
        title=state.title,
        description=state.description,
        service=state.service
    )
    tracer.log_event(state.incident_id, "triage", "TRIAGE_COMPLETE", {
        "severity": severity,
        "domain": domain,
        "confidence": conf
    })
    return {"severity": severity, "status": "INVESTIGATING"}

async def investigate_node(state: IncidentState) -> Dict[str, Any]:
    evidence = await investigation_agent.investigate(service=state.service)
    tracer.log_event(state.incident_id, "investigate", "EVIDENCE_COLLECTED", {
        "current_version": evidence.current_version,
        "error_rate": evidence.metrics.get("error_rate"),
        "log_count": len(evidence.error_logs)
    })
    return {"evidence": evidence}

async def knowledge_node(state: IncidentState) -> Dict[str, Any]:
    query = f"{state.service} {state.title} {state.description}"
    docs = await runbook_retriever.search(query=query, top_k=3)
    symptoms = " ".join(state.evidence.error_logs) if state.evidence else state.description
    reranked_docs = await jev_reranker.rerank(incident_symptoms=symptoms, documents=docs)
    tracer.log_event(state.incident_id, "knowledge", "RUNBOOKS_RETRIEVED", {
        "count": len(reranked_docs),
        "top_doc": reranked_docs[0].title if reranked_docs else None
    })
    return {"retrieved_runbooks": reranked_docs}

async def diagnose_node(state: IncidentState) -> Dict[str, Any]:
    diagnosis = await diagnosis_agent.diagnose(
        evidence=state.evidence,
        runbooks=state.retrieved_runbooks
    )
    tracer.log_event(state.incident_id, "diagnose", "DIAGNOSIS_PRODUCED", {
        "root_cause": diagnosis.root_cause,
        "confidence": diagnosis.confidence,
        "recommended_action": diagnosis.recommended_action
    })
    return {"diagnosis": diagnosis, "status": "DIAGNOSED"}

async def policy_node(state: IncidentState) -> Dict[str, Any]:
    if state.diagnosis.recommended_action == "escalate_to_human":
        tracer.log_event(state.incident_id, "policy", "POLICY_EVALUATED", {
            "action": "escalate_to_human",
            "risk_level": "MEDIUM",
            "decision": "DENY",
            "requires_approval": False,
            "reason": "Diagnosis could not recommend a supported automated remediation."
        })
        return {
            "policy_evaluation": PolicyEvaluation(
                action="escalate_to_human",
                risk_level="MEDIUM",
                decision="DENY",
                requires_approval=False,
                reason="Diagnosis could not recommend a supported automated remediation."
            ),
            "status": "ESCALATED"
        }
    evaluation = policy_engine.evaluate(
        action=state.diagnosis.recommended_action,
        target_service=state.service,
        environment="production",
        severity=state.severity,
        has_approval=bool(state.approval_granted)
    )
    tracer.log_event(state.incident_id, "policy", "POLICY_EVALUATED", {
        "action": evaluation.action,
        "risk_level": evaluation.risk_level,
        "decision": evaluation.decision,
        "requires_approval": evaluation.requires_approval
    })
    
    new_status = (
        "PENDING_APPROVAL" if evaluation.decision == "REQUIRE_APPROVAL"
        else "REMEDIATING" if evaluation.decision == "ALLOW"
        else "ESCALATED"
    )
    return {"policy_evaluation": evaluation, "status": new_status}

def should_execute_remediation(state: IncidentState) -> str:
    if not state.policy_evaluation or state.policy_evaluation.decision == "DENY":
        return "pause_for_approval"
    if state.policy_evaluation.decision == "REQUIRE_APPROVAL" and not state.approval_granted:
        return "pause_for_approval"
    return "execute_remediation"


def should_verify_remediation(state: IncidentState) -> str:
    return "verify" if state.remediation and state.remediation.status == "SUCCESS" else END

async def remediate_node(state: IncidentState) -> Dict[str, Any]:
    action = state.diagnosis.recommended_action
    params = state.diagnosis.action_parameters

    if action == "rollback_deployment":
        if not state.policy_evaluation or state.policy_evaluation.action != action:
            raise RuntimeError("Rollback has no matching recorded policy evaluation")
        if state.policy_evaluation.decision == "DENY":
            raise RuntimeError("Policy denied this rollback")
        if state.policy_evaluation.decision == "REQUIRE_APPROVAL" and not state.approval_granted:
            raise RuntimeError("Rollback approval has not been recorded")
    
    if action == "rollback_deployment":
        res = await needle_executor.execute_rollback(
            service=params.get("service", state.service),
            target_version=params.get("target_version", "2.4.0")
        )
        remediation = RemediationResult(
            action=action,
            target_service=state.service,
            parameters=params,
            status="SUCCESS" if res.get("status") == "SUCCESS" else "FAILED",
            message=res.get("message", "Rollback executed.")
        )
    else:
        remediation = RemediationResult(
            action=action,
            target_service=state.service,
            parameters=params,
            status="SKIPPED",
            message=f"Action {action} skipped or unhandled."
        )

    next_status = "VERIFYING" if remediation.status == "SUCCESS" else "ESCALATED"
    tracer.log_event(state.incident_id, "remediation", "REMEDIATION_EXECUTED", {
        "action": remediation.action,
        "status": remediation.status,
        "message": remediation.message
    })
    return {"remediation": remediation, "status": next_status}

async def verify_node(state: IncidentState) -> Dict[str, Any]:
    if settings.USE_MCP:
        health_data = await mcp_client.get_service_health(state.service)
    else:
        health_data = await acme_client.get_service_health(state.service)
    is_healthy = health_data.get("healthy", False)
    err_rate = health_data.get("error_rate", 0.0)
    lat_ms = health_data.get("latency_ms", 0.0)
    current_v = health_data.get("version", "unknown")

    success = is_healthy and err_rate < 0.01

    verification = VerificationResult(
        is_healthy=is_healthy,
        error_rate=err_rate,
        latency_ms=lat_ms,
        service_version=current_v,
        status="SUCCESS" if success else "FAILED",
        details=f"Service {state.service} version is {current_v}, error rate={err_rate:.2%}, latency={lat_ms:.1f}ms."
    )

    tracer.log_event(state.incident_id, "verification", "VERIFICATION_COMPLETE", {
        "status": verification.status,
        "details": verification.details
    })

    new_status = "RESOLVED" if success else "ESCALATED"
    return {"verification": verification, "status": new_status}

def create_aegis_workflow():
    workflow = AegisStateGraph(IncidentState)

    workflow.add_node("triage", triage_node)
    workflow.add_node("investigate", investigate_node)
    workflow.add_node("knowledge", knowledge_node)
    workflow.add_node("diagnose", diagnose_node)
    workflow.add_node("policy", policy_node)
    workflow.add_node("remediate", remediate_node)
    workflow.add_node("verify", verify_node)

    workflow.set_entry_point("triage")
    workflow.add_edge("triage", "investigate")
    workflow.add_edge("investigate", "knowledge")
    workflow.add_edge("knowledge", "diagnose")
    workflow.add_edge("diagnose", "policy")

    workflow.add_conditional_edges(
        "policy",
        should_execute_remediation,
        {
            "pause_for_approval": END,
            "execute_remediation": "remediate"
        }
    )

    workflow.add_conditional_edges("remediate", should_verify_remediation, {
        "verify": "verify",
        END: END
    })
    workflow.add_edge("verify", END)

    return workflow.compile()

aegis_graph = create_aegis_workflow()
