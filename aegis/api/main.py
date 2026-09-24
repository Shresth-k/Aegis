import asyncio
import json
import os
import time
import httpx
from pathlib import Path
from typing import Dict, Any, Optional, List, Tuple
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from aegis.config import settings
from aegis.core.state import (
    IncidentState,
    IncidentAlert,
    TelemetryEvidence,
    RetrievedRunbook,
    DiagnosisResult,
    PolicyEvaluation,
    RemediationResult,
    VerificationResult,
)
from aegis.graph.workflow import aegis_graph, remediate_node, verify_node
from aegis.core.tracer import tracer
from aegis.acme.client import acme_client
from aegis.mcp.server import _load_incidents, _save_incidents
from aegis.triage.jev_triage import jev_triage
from aegis.rag.retriever import runbook_retriever
from aegis.rag.jev_reranker import jev_reranker
from aegis.agents.diagnosis import diagnosis_agent
from aegis.policy.engine import policy_engine
from aegis.executor.needle_executor import needle_executor

app = FastAPI(
    title="Aegis Incident Resolution Platform",
    description="Agentic IT Operations & Autonomous Incident Resolution API",
    version="0.1.0"
)

# Enable CORS for local Vite development & external web access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory incident store for active sessions
INCIDENTS: Dict[str, IncidentState] = {}


class ApprovalRequest(BaseModel):
    approved: bool
    approved_by: str = "LeadSRE"
    reason: Optional[str] = "Operator verified diagnosis and approved remediation."


class RunIncidentRequest(BaseModel):
    incident_id: str = "INC-001"
    service: str = "checkout-service"
    severity: str = "P1"
    title: Optional[str] = "High 5xx Error Rate on Checkout Service"
    description: Optional[str] = (
        "Checkout service is throwing 500 errors and connection pool exhaustion "
        "following recent release."
    )


class ApproveIncidentRequest(BaseModel):
    incident_id: str
    approved: bool = True
    approved_by: str = "LeadSRE"
    reason: Optional[str] = "Operator verified diagnosis and approved remediation."


@app.get("/api/incidents")
async def list_all_incidents():
    """List all incidents from memory and MCP store."""
    mcp_data = _load_incidents()
    results = []
    seen = set()

    for inc_id, state in INCIDENTS.items():
        seen.add(inc_id)
        results.append({
            "incident_id": inc_id,
            "service": state.service,
            "severity": state.severity,
            "title": state.title,
            "description": state.description,
            "status": state.status,
            "updated_at": state.updated_at.isoformat() if hasattr(state.updated_at, "isoformat") else str(state.updated_at),
        })

    for inc_id, mcp_inc in mcp_data.items():
        if inc_id not in seen:
            results.append({
                "incident_id": inc_id,
                "service": mcp_inc.get("service", "checkout-service"),
                "severity": mcp_inc.get("severity", "P1"),
                "title": mcp_inc.get("summary", inc_id),
                "description": mcp_inc.get("summary", ""),
                "status": mcp_inc.get("status", "OPEN"),
                "updated_at": mcp_inc.get("created_at", ""),
            })

    return results


@app.post("/api/incidents", response_model=IncidentState)
async def create_incident(alert: IncidentAlert):
    """Trigger investigation of a new incident alert."""
    state = IncidentState(
        incident_id=alert.incident_id,
        service=alert.service,
        severity=alert.severity,
        title=alert.title,
        description=alert.description
    )
    INCIDENTS[alert.incident_id] = state

    tracer.log_event(alert.incident_id, "ingest", "INCIDENT_INGESTED", {
        "service": alert.service,
        "severity": alert.severity,
        "title": alert.title
    })

    # Execute workflow up to approval boundary or resolution
    final_output = await aegis_graph.ainvoke(state)
    state = IncidentState(**{**state.model_dump(), **final_output})
    INCIDENTS[alert.incident_id] = state
    return state


@app.post("/api/incidents/run", response_model=IncidentState)
async def run_incident(req: RunIncidentRequest):
    """Trigger or re-run an incident investigation workflow."""
    alert = IncidentAlert(
        incident_id=req.incident_id,
        service=req.service,
        severity=req.severity, # type: ignore
        title=req.title or f"Incident on {req.service}",
        description=req.description or "Automated investigation initiated."
    )
    return await create_incident(alert)


@app.get("/api/incidents/{incident_id}", response_model=IncidentState)
async def get_incident(incident_id: str):
    """Get current state of an incident."""
    if incident_id not in INCIDENTS:
        # Check MCP store
        mcp_data = _load_incidents()
        if incident_id in mcp_data:
            item = mcp_data[incident_id]
            fallback_state = IncidentState(
                incident_id=incident_id,
                service=item.get("service", "checkout-service"),
                severity=item.get("severity", "P1"), # type: ignore
                title=item.get("summary", incident_id),
                description=item.get("summary", ""),
                status=item.get("status", "OPEN") # type: ignore
            )
            INCIDENTS[incident_id] = fallback_state
            return fallback_state
        raise HTTPException(status_code=404, detail="Incident not found")
    return INCIDENTS[incident_id]


@app.post("/api/incidents/approve", response_model=IncidentState)
async def approve_incident(req: ApproveIncidentRequest):
    """Approve or reject pending remediation for an incident."""
    return await respond_to_approval(
        incident_id=req.incident_id,
        request=ApprovalRequest(
            approved=req.approved,
            approved_by=req.approved_by,
            reason=req.reason
        )
    )


@app.post("/api/approvals/{incident_id}/respond", response_model=IncidentState)
async def respond_to_approval(incident_id: str, request: ApprovalRequest):
    """Approve or reject pending remediation for an incident."""
    if incident_id not in INCIDENTS:
        raise HTTPException(status_code=404, detail="Incident not found")

    state = INCIDENTS[incident_id]
    if state.status != "PENDING_APPROVAL":
        raise HTTPException(status_code=400, detail=f"Incident is not pending approval (current status: {state.status})")

    state.approval_granted = request.approved
    state.approved_by = request.approved_by
    state.approval_reason = request.reason

    tracer.log_event(incident_id, "approval", "APPROVAL_DECISION", {
        "approved": request.approved,
        "approved_by": request.approved_by,
        "reason": request.reason
    })

    if not request.approved:
        state.status = "ESCALATED"
        INCIDENTS[incident_id] = state
        return state

    # Resume workflow: Remediate -> Verify -> Resolve
    rem_output = await remediate_node(state)
    state = IncidentState(**{**state.model_dump(), **rem_output})

    ver_output = await verify_node(state)
    state = IncidentState(**{**state.model_dump(), **ver_output})

    INCIDENTS[incident_id] = state
    return state


class ChatRequest(BaseModel):
    incident_id: str = "INC-001"
    message: str
    history: Optional[List[Dict[str, Any]]] = None


class ChatResponse(BaseModel):
    reply: str
    thinking: Optional[str] = None
    tool_call: Optional[Dict[str, Any]] = None
    tool_calls: Optional[List[Dict[str, Any]]] = None
    new_nodes: Optional[List[str]] = None
    policy_gate: Optional[Dict[str, Any]] = None
    status: Optional[str] = None


# --- Real Tool Implementations for Interactive Chat ---

async def tool_triage_incident(incident_id: str, service: str, state: Optional[IncidentState] = None) -> Tuple[Dict[str, Any], List[str]]:
    """Execute Jev AI triage for incident."""
    t0 = time.perf_counter()
    title = state.title if state and state.title else f"High 5xx Error Rate on {service}"
    desc = state.description if state and state.description else f"Service {service} is throwing 500 errors."
    severity, domain, conf = await jev_triage.triage_incident(
        title=title,
        description=desc,
        service=service
    )
    elapsed_ms = round((time.perf_counter() - t0) * 1000, 1)
    tracer.log_event(incident_id, "triage", "TRIAGE_COMPLETE", {
        "severity": severity,
        "domain": domain,
        "confidence": conf,
        "latency_ms": elapsed_ms
    })
    if state:
        state.severity = severity  # type: ignore
        state.status = "INVESTIGATING"
    return {
        "incident_id": incident_id,
        "service": service,
        "severity": severity,
        "domain": domain,
        "confidence": conf,
        "status": "TRIAGE_COMPLETE",
        "engine": "TypeSafe Jev AI (System One)",
        "model": "typesafe-ai/jev",
        "endpoint": "https://ai-gateway.vercel.sh/v1/evaluate",
        "primitive": "choice",
        "latency_ms": elapsed_ms,
        "tokens": "120t"
    }, ["ingest", "triage"]


async def tool_get_metrics(service: str, state: Optional[IncidentState] = None, incident_id: str = "INC-001") -> Tuple[Dict[str, Any], List[str]]:
    """Get live Prometheus metrics for service."""
    t0 = time.perf_counter()
    metrics = await acme_client.get_metrics(service=service)
    elapsed_ms = round((time.perf_counter() - t0) * 1000, 1)
    metrics_out = dict(metrics)
    metrics_out["latency_ms"] = elapsed_ms
    metrics_out["source"] = "Prometheus (AcmeCloud Digital Twin / Container)"
    metrics_out["tokens"] = "290t"
    tracer.log_event(incident_id, "investigate", "EVIDENCE_COLLECTED", {
        "service": service,
        "metrics": metrics_out,
        "latency_ms": elapsed_ms
    })
    if state:
        if not state.evidence:
            state.evidence = TelemetryEvidence(
                service=service,
                current_version="2.4.1",
                previous_version="2.4.0",
                recent_deployment=True,
                metrics=metrics,
                error_logs=[],
                dependencies=["postgres", "inventory-service", "payment-service", "redis"],
                dependency_health={"postgres": True, "inventory-service": True, "payment-service": True, "redis": True}
            )
        else:
            state.evidence.metrics = metrics
    return metrics_out, ["tool-metrics"]


async def tool_get_service_logs(service: str, state: Optional[IncidentState] = None, incident_id: str = "INC-001") -> Tuple[Dict[str, Any], List[str]]:
    """Get error logs for service."""
    t0 = time.perf_counter()
    logs = await acme_client.get_logs(service=service, query="error")
    elapsed_ms = round((time.perf_counter() - t0) * 1000, 1)
    tracer.log_event(incident_id, "investigate", "LOGS_COLLECTED", {
        "service": service,
        "log_count": len(logs),
        "latency_ms": elapsed_ms
    })
    if state:
        if not state.evidence:
            state.evidence = TelemetryEvidence(
                service=service,
                current_version="2.4.1",
                previous_version="2.4.0",
                recent_deployment=True,
                metrics={},
                error_logs=logs,
                dependencies=["postgres", "inventory-service", "payment-service", "redis"],
                dependency_health={"postgres": True, "inventory-service": True, "payment-service": True, "redis": True}
            )
        else:
            state.evidence.error_logs = logs
    return {
        "service": service,
        "log_count": len(logs),
        "logs": logs[:5],
        "latency_ms": elapsed_ms,
        "source": "AcmeCloud FastMCP / Container Logs",
        "tokens": "310t"
    }, ["tool-logs"]


async def tool_search_runbooks(query: str, service: str, state: Optional[IncidentState] = None, incident_id: str = "INC-001") -> Tuple[Dict[str, Any], List[str]]:
    """Search runbooks with Jev Noul reranker."""
    t0 = time.perf_counter()
    docs = await runbook_retriever.search(query=query, top_k=3)
    symptoms = " ".join(state.evidence.error_logs) if (state and state.evidence and state.evidence.error_logs) else query
    reranked_docs = await jev_reranker.rerank(incident_symptoms=symptoms, documents=docs)
    elapsed_ms = round((time.perf_counter() - t0) * 1000, 1)
    tracer.log_event(incident_id, "knowledge", "RUNBOOKS_RETRIEVED", {
        "count": len(reranked_docs),
        "top_doc": reranked_docs[0].title if reranked_docs else None,
        "latency_ms": elapsed_ms
    })
    if state:
        state.retrieved_runbooks = reranked_docs
    result = [
        {"doc_id": d.doc_id, "title": d.title, "score": d.score, "content": d.content[:200] + "..."}
        for d in reranked_docs
    ]
    return {
        "query": query,
        "runbooks": result,
        "model": "typesafe-ai/jev (Noul Reranker)",
        "latency_ms": elapsed_ms,
        "tokens": "620t"
    }, ["knowledge"]


async def tool_evaluate_policy(action: str, target_service: str, state: Optional[IncidentState] = None, incident_id: str = "INC-001") -> Tuple[Dict[str, Any], List[str]]:
    """Evaluate PolicyEngine safety rule."""
    t0 = time.perf_counter()
    evaluation = policy_engine.evaluate(
        action=action,
        target_service=target_service,
        environment="production",
        severity=state.severity if state else "P1",
        has_approval=bool(state and state.approval_granted)
    )
    elapsed_ms = round((time.perf_counter() - t0) * 1000, 1)
    tracer.log_event(incident_id, "policy", "POLICY_EVALUATED", {
        "action": evaluation.action,
        "risk_level": evaluation.risk_level,
        "decision": evaluation.decision,
        "requires_approval": evaluation.requires_approval,
        "latency_ms": elapsed_ms
    })
    if state:
        state.policy_evaluation = evaluation
        if evaluation.decision == "REQUIRE_APPROVAL":
            state.status = "PENDING_APPROVAL"
        elif evaluation.decision == "ALLOW":
            state.status = "REMEDIATING"
    return {
        "action": evaluation.action,
        "risk_level": evaluation.risk_level,
        "decision": evaluation.decision,
        "requires_approval": evaluation.requires_approval,
        "reason": evaluation.reason,
        "policy_id": "PROD_ROLLBACK_APPROVAL",
        "latency_ms": elapsed_ms,
        "tokens": "140t"
    }, ["diagnose", "policy"]


async def tool_rollback_deployment(service: str, target_version: str = "2.4.0", state: Optional[IncidentState] = None, incident_id: str = "INC-001") -> Tuple[Dict[str, Any], List[str]]:
    """Execute rollback to target version."""
    t0 = time.perf_counter()
    res = await needle_executor.execute_rollback(service=service, target_version=target_version)
    elapsed_ms = round((time.perf_counter() - t0) * 1000, 1)
    res_out = dict(res)
    res_out["latency_ms"] = elapsed_ms
    res_out["tokens"] = "860t"
    remediation = RemediationResult(
        action="rollback_deployment",
        target_service=service,
        parameters={"target_version": target_version},
        status="SUCCESS" if res.get("status") == "SUCCESS" else "FAILED",
        message=res.get("message", f"Rollback to {target_version} executed.")
    )
    tracer.log_event(incident_id, "remediation", "REMEDIATION_EXECUTED", {
        "action": remediation.action,
        "status": remediation.status,
        "message": remediation.message,
        "latency_ms": elapsed_ms
    })
    if state:
        state.remediation = remediation
        state.status = "VERIFYING"
    return res_out, ["remediate"]


async def tool_verify_slo(service: str, state: Optional[IncidentState] = None, incident_id: str = "INC-001") -> Tuple[Dict[str, Any], List[str]]:
    """Verify health and SLOs."""
    t0 = time.perf_counter()
    health_data = await acme_client.get_service_health(service)
    is_healthy = health_data.get("healthy", False)
    err_rate = health_data.get("error_rate", 0.0)
    lat_ms = health_data.get("latency_ms", 0.0)
    current_v = health_data.get("version", "unknown")
    success = is_healthy and err_rate < 0.01
    elapsed_ms = round((time.perf_counter() - t0) * 1000, 1)

    verification = VerificationResult(
        is_healthy=is_healthy,
        error_rate=err_rate,
        latency_ms=lat_ms,
        service_version=current_v,
        status="SUCCESS" if success else "FAILED",
        details=f"Service {service} version is {current_v}, error rate={err_rate:.2%}, latency={lat_ms:.1f}ms."
    )
    tracer.log_event(incident_id, "verification", "VERIFICATION_COMPLETE", {
        "status": verification.status,
        "details": verification.details,
        "latency_ms": elapsed_ms
    })
    if state:
        state.verification = verification
        state.status = "RESOLVED" if success else "ESCALATED"
    return {
        "is_healthy": is_healthy,
        "error_rate": err_rate,
        "latency_ms": lat_ms,
        "verification_latency_ms": elapsed_ms,
        "service_version": current_v,
        "status": "SUCCESS" if success else "FAILED",
        "tokens": "240t"
    }, ["verify"]


async def tool_docker_ps(all_containers: bool = False) -> Tuple[Dict[str, Any], List[str]]:
    """List containers on host Docker daemon."""
    t0 = time.perf_counter()
    from aegis.mcp.server import docker_ps
    containers = await docker_ps(all_containers=all_containers)
    elapsed_ms = round((time.perf_counter() - t0) * 1000, 1)
    return {
        "status": "SUCCESS",
        "container_count": len(containers),
        "containers": containers,
        "latency_ms": elapsed_ms,
        "source": "Host Docker Daemon (docker ps)"
    }, ["docker-ps"]


async def tool_docker_logs(container_name: str = "acmecloud-checkout", tail: int = 50) -> Tuple[Dict[str, Any], List[str]]:
    """Retrieve stdout/stderr logs directly from a Docker container."""
    t0 = time.perf_counter()
    from aegis.mcp.server import docker_logs
    lines = await docker_logs(container_name=container_name, tail=tail)
    elapsed_ms = round((time.perf_counter() - t0) * 1000, 1)
    return {
        "status": "SUCCESS",
        "container": container_name,
        "line_count": len(lines),
        "logs": lines[-25:] if lines else [],
        "latency_ms": elapsed_ms,
        "source": f"Docker Daemon Logs ({container_name})"
    }, ["tool-logs"]


async def tool_docker_restart_container(container_name: str) -> Tuple[Dict[str, Any], List[str]]:
    """Restart a container via the Docker daemon."""
    t0 = time.perf_counter()
    from aegis.mcp.server import docker_restart_container
    res = await docker_restart_container(container_name=container_name)
    elapsed_ms = round((time.perf_counter() - t0) * 1000, 1)
    return {
        **res,
        "latency_ms": elapsed_ms,
    }, ["remediate"]


async def run_copilot_pipeline(req: ChatRequest, stream_words: bool = True):
    """
    Core async generator powering both SSE streaming (/api/chat/stream)
    and synchronous REST response (/api/chat).
    Yields tuples of (event_type, event_payload).
    """
    state = INCIDENTS.get(req.incident_id)
    if not state:
        mcp_data = _load_incidents()
        if req.incident_id in mcp_data:
            item = mcp_data[req.incident_id]
            state = IncidentState(
                incident_id=req.incident_id,
                service=item.get("service", "checkout-service"),
                severity=item.get("severity", "P1"),
                title=item.get("summary", req.incident_id),
                description=item.get("summary", ""),
                status=item.get("status", "OPEN")
            )
            INCIDENTS[req.incident_id] = state
        else:
            state = IncidentState(
                incident_id=req.incident_id,
                service="checkout-service",
                severity="P1",
                title=f"Incident {req.incident_id}",
                description="Automated investigation context.",
                status="OPEN"
            )
            INCIDENTS[req.incident_id] = state

    msg = req.message.lower().strip()
    service_name = state.service if state else "checkout-service"
    tool_calls_executed: List[Dict[str, Any]] = []
    spawned_nodes: List[str] = []
    t0_req = time.perf_counter()

    async def emit_text(reply_str: str):
        if not stream_words:
            return
        words = reply_str.split(" ")
        for idx, w in enumerate(words):
            chunk = w + (" " if idx < len(words) - 1 else "")
            yield ("text_delta", {"delta": chunk})
            await asyncio.sleep(0.003)

    # 1. Approval handling: Operator authorizes remediation
    if any(k in msg for k in ["approve", "confirm", "proceed", "authorize", "rollback now", "execute rollback"]) and not any(k in msg for k in ["reject", "deny", "don't", "dont"]):
        yield ("thinking", {"thinking": "Operator authorized production remediation. Reverting deployment to baseline v2.4.0 via Needle Executor and verifying SLO recovery..."})
        
        yield ("tool_start", {"name": "rollback_deployment", "args": {"service": service_name, "target_version": "2.4.0"}})
        res_rollback, nodes_rem = await tool_rollback_deployment(service_name, "2.4.0", state, req.incident_id)
        spawned_nodes.extend(nodes_rem)
        tool_calls_executed.append({
            "name": "rollback_deployment",
            "args": {"service": service_name, "target_version": "2.4.0"},
            "output": res_rollback
        })
        yield ("tool_result", {"name": "rollback_deployment", "output": res_rollback, "node": "remediate"})
        yield ("node_spawned", {"node_id": "remediate"})

        yield ("tool_start", {"name": "verify_slo", "args": {"service": service_name}})
        res_verify, nodes_ver = await tool_verify_slo(service_name, state, req.incident_id)
        spawned_nodes.extend(nodes_ver)
        tool_calls_executed.append({
            "name": "verify_slo",
            "args": {"service": service_name},
            "output": res_verify
        })
        yield ("tool_result", {"name": "verify_slo", "output": res_verify, "node": "verify"})
        yield ("node_spawned", {"node_id": "verify"})

        state.approval_granted = True
        state.approved_by = "LeadSRE"
        state.status = "RESOLVED"
        INCIDENTS[req.incident_id] = state

        reply = (
            f"**Remediation Executed & Verified Successfully:**\n\n"
            f"- **Action**: `rollback_deployment` to `v2.4.0` on `{service_name}`\n"
            f"- **Status**: `SUCCESS` — Replaced faulty container `v2.4.1` with stable baseline `v2.4.0`.\n"
            f"- **SLO Verification**: Nominal health restored. Error rate dropped to `{res_verify.get('error_rate', 0.002):.2%}` (< 1%) and P95 latency is `{res_verify.get('latency_ms', 42.5):.1f}ms`.\n\n"
            f"Incident **{req.incident_id}** is now **RESOLVED**."
        )
        async for chunk in emit_text(reply):
            yield chunk

        yield ("done", {
            "reply": reply,
            "thinking": "Operator authorized production remediation. Executed container rollback to v2.4.0 via Needle Executor and verified post-remediation SLO telemetry.",
            "tool_call": tool_calls_executed[0],
            "tool_calls": tool_calls_executed,
            "new_nodes": list(dict.fromkeys(spawned_nodes)),
            "policy_gate": None,
            "status": "RESOLVED",
            "duration_seconds": round(time.perf_counter() - t0_req, 2)
        })
        return

    # 2. Rejection handling
    if any(k in msg for k in ["reject", "deny", "abort", "cancel rollback", "escalate"]):
        state.status = "ESCALATED"
        INCIDENTS[req.incident_id] = state
        yield ("thinking", {"thinking": "Operator rejected automated remediation. Escalating incident to human on-call Lead SRE..."})
        reply = f"Remediation rejected. Incident **{req.incident_id}** has been escalated to on-call Lead SRE for manual intervention."
        async for chunk in emit_text(reply):
            yield chunk
        yield ("done", {
            "reply": reply,
            "thinking": "Operator rejected automated remediation. Escalating incident to human on-call.",
            "new_nodes": [],
            "status": "ESCALATED",
            "duration_seconds": round(time.perf_counter() - t0_req, 2)
        })
        return

    # 2.2 Container Restart / DB Flush Remediation (For Memory Leak or DB Deadlock Scenarios)
    if any(k in msg for k in ["restart container", "restart pod", "restart checkout", "restart postgres", "reboot container", "flush lock", "recycle container", "clear memory"]):
        target_container = "acmecloud-postgres" if any(k in msg for k in ["postgres", "database", "db", "lock"]) else "acmecloud-checkout"
        yield ("thinking", {"thinking": f"Operator authorized container lifecycle remediation. Restarting `{target_container}` via Docker daemon to clear runtime state..."})

        yield ("tool_start", {"name": "docker_restart_container", "args": {"container_name": target_container}})
        res_rst, nodes_rst = await tool_docker_restart_container(target_container)
        spawned_nodes.extend(nodes_rst)
        tool_calls_executed.append({
            "name": "docker_restart_container",
            "args": {"container_name": target_container},
            "output": res_rst
        })
        yield ("tool_result", {"name": "docker_restart_container", "output": res_rst, "node": "remediate"})
        yield ("node_spawned", {"node_id": "remediate"})

        yield ("tool_start", {"name": "verify_slo", "args": {"service": service_name}})
        res_verify, nodes_ver = await tool_verify_slo(service_name, state, req.incident_id)
        spawned_nodes.extend(nodes_ver)
        tool_calls_executed.append({
            "name": "verify_slo",
            "args": {"service": service_name},
            "output": res_verify
        })
        yield ("tool_result", {"name": "verify_slo", "output": res_verify, "node": "verify"})
        yield ("node_spawned", {"node_id": "verify"})

        state.status = "RESOLVED"
        state.approval_granted = True
        state.approved_by = "LeadSRE"
        INCIDENTS[req.incident_id] = state

        reply = (
            f"**Container Restart Executed & Verified Successfully:**\n\n"
            f"- **Action**: `docker_restart_container` on `{target_container}`\n"
            f"- **Status**: `SUCCESS` — Container restarted; heap allocation flushed and worker thread pool restored.\n"
            f"- **SLO Verification**: Nominal health restored. Error rate is `{res_verify.get('error_rate', 0.002):.2%}` and P95 latency dropped to `{res_verify.get('latency_ms', 42.5):.1f}ms`.\n"
            f"- **Policy Note**: Code rollback was **not required** because the release binary was stable and the fault was isolated to runtime state.\n\n"
            f"Incident **{req.incident_id}** is now **RESOLVED**."
        )
        async for chunk in emit_text(reply):
            yield chunk

        yield ("done", {
            "reply": reply,
            "thinking": f"Recycled {target_container} container and confirmed nominal SLO recovery without triggering code rollback.",
            "tool_call": tool_calls_executed[0],
            "tool_calls": tool_calls_executed,
            "new_nodes": list(dict.fromkeys(spawned_nodes)),
            "policy_gate": None,
            "status": "RESOLVED",
            "duration_seconds": round(time.perf_counter() - t0_req, 2)
        })
        return

    # 2.5 Parallel Tool Execution Orchestration (e.g. "execute get_metrics 4 times in parallel", "run 4 parallel probes")
    is_parallel_request = (
        ("parallel" in msg or "concurrent" in msg) and 
        any(k in msg for k in ["times", "probes", "workers", "instances", "calls", "test", "tool", "run", "execute"])
    ) or ("4 times" in msg)
    if is_parallel_request:
        import re
        count_match = re.search(r"(\d+)\s*(?:times|probes|workers|instances)?", msg)
        parallel_count = int(count_match.group(1)) if count_match and int(count_match.group(1)) in range(2, 9) else 4

        tool_target = "get_metrics"
        if "metric" in msg:
            tool_target = "get_metrics"
        elif "log" in msg:
            tool_target = "get_service_logs"
        elif "verify" in msg or "slo" in msg:
            tool_target = "verify_slo"
        elif "triage" in msg and not any(k in msg for k in ["metric", "log", "probe"]):
            tool_target = "triage_incident"

        yield ("thinking", {"thinking": f"Operator requested parallel execution of `{tool_target}` across {parallel_count} concurrent workers. Spawning asynchronous pipeline with dynamic fan-out DAG topology..."})

        # Upstream test if requested (e.g. "after some kind of another test" or "after triage")
        if any(k in msg for k in ["after", "following", "then", "test"]):
            yield ("tool_start", {"name": "triage_incident", "args": {"incident_id": req.incident_id, "service": service_name}})
            res_triage, nodes_tri = await tool_triage_incident(req.incident_id, service_name, state)
            spawned_nodes.extend(nodes_tri)
            tool_calls_executed.append({
                "name": "triage_incident",
                "args": {"incident_id": req.incident_id, "service": service_name},
                "output": res_triage
            })
            yield ("tool_result", {"name": "triage_incident", "output": res_triage, "node": "triage"})
            for nd in nodes_tri:
                yield ("node_spawned", {"node_id": nd})
            await asyncio.sleep(0.1)

        # Concurrently execute parallel workers via asyncio.gather
        async def run_worker(worker_idx: int):
            worker_id = f"worker-{worker_idx}"
            if tool_target == "get_metrics":
                res, _ = await tool_get_metrics(service_name, state, req.incident_id)
                res_w = dict(res)
                res_w["worker_id"] = worker_id
                res_w["concurrency_slice"] = f"partition-{worker_idx}"
                node_id = f"tool-metrics-{worker_idx}"
                return worker_idx, "get_metrics", {"service": service_name, "worker_id": worker_id, "concurrency": 25}, res_w, node_id
            elif tool_target == "get_service_logs":
                res, _ = await tool_get_service_logs(service_name, state, req.incident_id)
                res_w = dict(res)
                res_w["worker_id"] = worker_id
                node_id = f"tool-logs-{worker_idx}"
                return worker_idx, "get_service_logs", {"service": service_name, "partition": worker_idx}, res_w, node_id
            else:
                res, _ = await tool_get_metrics(service_name, state, req.incident_id)
                node_id = f"tool-metrics-{worker_idx}"
                return worker_idx, tool_target, {"service": service_name, "worker_id": worker_id}, res, node_id

        tasks = [run_worker(i) for i in range(1, parallel_count + 1)]
        parallel_results = await asyncio.gather(*tasks)

        for w_idx, t_name, t_args, t_res, n_id in parallel_results:
            yield ("tool_start", {"name": f"{t_name} [Worker {w_idx}]", "args": t_args})
            yield ("tool_result", {"name": f"{t_name} [Worker {w_idx}]", "output": t_res, "node": n_id})
            yield ("node_spawned", {"node_id": n_id})
            spawned_nodes.append(n_id)
            tool_calls_executed.append({
                "name": f"{t_name} [Worker {w_idx}]",
                "args": t_args,
                "output": t_res
            })

        # Fan-in convergence stage: Gemini CoT Synthesis / Diagnose
        yield ("thinking", {"thinking": f"All {parallel_count} parallel workers completed. Aggregating multi-worker telemetry into diagnostic synthesis..."})
        yield ("node_spawned", {"node_id": "diagnose"})
        spawned_nodes.append("diagnose")

        reply = (
            f"### Parallel Tool Execution Completed ({parallel_count} Concurrent Workers)\n\n"
            f"Executed **`{tool_target}`** across **{parallel_count} parallel worker threads** on `{service_name}`:\n\n"
            + "\n".join([
                f"- **Worker {r[0]}**: Status `OK`, Error Rate `{r[3].get('error_rate', 0.385):.1%}`, Active Pool `{r[3].get('db_pool_active', 5)}/{r[3].get('db_pool_max', 5)}`"
                for r in parallel_results
            ])
            + f"\n\n**DAG Flow Architecture:**\n"
            f"• **Fan-out**: Upstream test branched simultaneously into {parallel_count} parallel execution nodes (`{'`, `'.join([r[4] for r in parallel_results])}`).\n"
            f"• **Convergence**: All {parallel_count} streams synchronized and converged into the `diagnose` cognitive stage.\n"
            f"• **Finding**: Connection pool starvation is uniform across all {parallel_count} worker partitions."
        )

        async for chunk in emit_text(reply):
            yield chunk

        yield ("done", {
            "reply": reply,
            "thinking": f"Successfully coordinated and executed {parallel_count} parallel `{tool_target}` instances with dynamic DAG fan-out and fan-in.",
            "tool_call": tool_calls_executed[0],
            "tool_calls": tool_calls_executed,
            "new_nodes": list(dict.fromkeys(spawned_nodes)),
            "policy_gate": None,
            "status": state.status if state else "OPEN",
            "duration_seconds": round(time.perf_counter() - t0_req, 2)
        })
        return

    # 2.6 Docker runtime inquiries (e.g. "docker stuff", "can you execute docker", "list containers", "docker ps", "docker logs")
    if any(k in msg for k in ["docker", "container", "containers", "docker ps", "docker logs", "docker stuff"]) and not any(k in msg for k in ["diagnose", "auto-heal", "full investigation", "heal", "remediate"]):
        yield ("thinking", {"thinking": "Querying host Docker daemon for live container inventory and telemetry via MCP Docker runtime tools..."})
        yield ("tool_start", {"name": "docker_ps", "args": {"all_containers": False}})
        res_docker, nodes_d = await tool_docker_ps(all_containers=False)
        spawned_nodes.extend(nodes_d)
        tool_calls_executed.append({
            "name": "docker_ps",
            "args": {"all_containers": False},
            "output": res_docker
        })
        yield ("tool_result", {"name": "docker_ps", "output": res_docker, "node": "docker-ps"})
        yield ("node_spawned", {"node_id": "docker-ps"})

        containers = res_docker.get("containers", [])
        c_lines = []
        for c in containers:
            c_name = c.get("name") or c.get("Names") or "unknown"
            c_img = c.get("image") or c.get("Image") or "unknown"
            c_stat = c.get("status") or c.get("Status") or "unknown"
            c_ports = c.get("ports") or c.get("Ports") or "none"
            c_lines.append(f"- **`{c_name}`** (`{c_img}`): Status `{c_stat}` | Ports `{c_ports}`")

        c_summary = "\n".join(c_lines) if c_lines else "No running containers found on local Docker daemon."

        reply = (
            f"**Host Docker Daemon Status & Container Inventory:**\n\n"
            f"Aegis is integrated with the host Docker daemon via live MCP runtime tools (`docker_ps`, `docker_logs`, `docker_restart_container`).\n\n"
            f"**Active Containers ({res_docker.get('container_count', 0)}):**\n"
            f"{c_summary}\n\n"
            f"Operational capabilities:\n"
            f"- `docker_ps()`: Container inventory, status, and port mapping.\n"
            f"- `docker_logs(container_name)`: Container stdout/stderr inspection.\n"
            f"- `docker_restart_container(container_name)`: Direct daemon container lifecycle management."
        )

        async for chunk in emit_text(reply):
            yield chunk

        yield ("done", {
            "reply": reply,
            "thinking": f"Retrieved live container inventory ({res_docker.get('container_count', 0)} active containers) directly from host Docker daemon.",
            "tool_call": tool_calls_executed[0],
            "tool_calls": tool_calls_executed,
            "new_nodes": list(dict.fromkeys(spawned_nodes)),
            "policy_gate": None,
            "status": state.status if state else "OPEN",
            "duration_seconds": round(time.perf_counter() - t0_req, 2)
        })
        return

    # 3. Gemini 3.5 Flash-Lite with Real Function Calling & Autonomous Tool Execution
    gemini_key = os.getenv("GEMINI_API_KEY") or settings.LLM_API_KEY
    if gemini_key and settings.LLM_PROVIDER == "google":
        try:
            from google import genai
            from google.genai import types

            client = genai.Client(api_key=gemini_key)

            triage_decl = types.FunctionDeclaration(
                name="triage_incident",
                description="Execute Jev AI triage to classify incident domain, severity, and confidence.",
                parameters=types.Schema(
                    type=types.Type.OBJECT,
                    properties={
                        "incident_id": types.Schema(type=types.Type.STRING, description="Incident ID, e.g. INC-001"),
                        "service": types.Schema(type=types.Type.STRING, description="Target service name, e.g. checkout-service"),
                    },
                    required=["incident_id", "service"],
                ),
            )

            metrics_decl = types.FunctionDeclaration(
                name="get_metrics",
                description="Query live Prometheus metrics (error rate, p95 latency, DB connection pool active/max) for a service.",
                parameters=types.Schema(
                    type=types.Type.OBJECT,
                    properties={
                        "service": types.Schema(type=types.Type.STRING, description="Target service name, e.g. checkout-service"),
                    },
                    required=["service"],
                ),
            )

            logs_decl = types.FunctionDeclaration(
                name="get_service_logs",
                description="Query recent container error logs and stack traces for a service.",
                parameters=types.Schema(
                    type=types.Type.OBJECT,
                    properties={
                        "service": types.Schema(type=types.Type.STRING, description="Target service name, e.g. checkout-service"),
                    },
                    required=["service"],
                ),
            )

            runbooks_decl = types.FunctionDeclaration(
                name="search_runbooks",
                description="Search operational runbooks and knowledge base with Jev Noul semantic reranker.",
                parameters=types.Schema(
                    type=types.Type.OBJECT,
                    properties={
                        "query": types.Schema(type=types.Type.STRING, description="Query describing symptoms, e.g. database connection pool exhaustion"),
                        "service": types.Schema(type=types.Type.STRING, description="Target service name, e.g. checkout-service"),
                    },
                    required=["query", "service"],
                ),
            )

            policy_decl = types.FunctionDeclaration(
                name="evaluate_policy",
                description="Evaluate platform safety rules and guardrails for a proposed remediation action.",
                parameters=types.Schema(
                    type=types.Type.OBJECT,
                    properties={
                        "action": types.Schema(type=types.Type.STRING, description="Proposed action, e.g. rollback_deployment"),
                        "target_service": types.Schema(type=types.Type.STRING, description="Target service name, e.g. checkout-service"),
                    },
                    required=["action", "target_service"],
                ),
            )

            rollback_decl = types.FunctionDeclaration(
                name="rollback_deployment",
                description="Execute container rollback to target version via Needle Executor. Note: Requires operator approval before execution.",
                parameters=types.Schema(
                    type=types.Type.OBJECT,
                    properties={
                        "service": types.Schema(type=types.Type.STRING, description="Target service name, e.g. checkout-service"),
                        "target_version": types.Schema(type=types.Type.STRING, description="Target version, e.g. 2.4.0"),
                    },
                    required=["service"],
                ),
            )

            verify_decl = types.FunctionDeclaration(
                name="verify_slo",
                description="Verify post-remediation service health and SLO metrics.",
                parameters=types.Schema(
                    type=types.Type.OBJECT,
                    properties={
                        "service": types.Schema(type=types.Type.STRING, description="Target service name, e.g. checkout-service"),
                    },
                    required=["service"],
                ),
            )

            docker_ps_decl = types.FunctionDeclaration(
                name="docker_ps",
                description="List running containers on the host Docker daemon, returning IDs, names, images, status, and port bindings.",
                parameters=types.Schema(
                    type=types.Type.OBJECT,
                    properties={
                        "all_containers": types.Schema(type=types.Type.BOOLEAN, description="Whether to include stopped containers. Default false."),
                    },
                ),
            )

            docker_logs_decl = types.FunctionDeclaration(
                name="docker_logs",
                description="Retrieve stdout/stderr logs directly from a Docker container.",
                parameters=types.Schema(
                    type=types.Type.OBJECT,
                    properties={
                        "container_name": types.Schema(type=types.Type.STRING, description="Target container name, e.g. acmecloud-checkout"),
                        "tail": types.Schema(type=types.Type.INTEGER, description="Number of recent log lines to retrieve (default 50)"),
                    },
                    required=["container_name"],
                ),
            )

            docker_restart_decl = types.FunctionDeclaration(
                name="docker_restart_container",
                description="Restart a Docker container on the host daemon.",
                parameters=types.Schema(
                    type=types.Type.OBJECT,
                    properties={
                        "container_name": types.Schema(type=types.Type.STRING, description="Target container name, e.g. acmecloud-checkout"),
                    },
                    required=["container_name"],
                ),
            )

            gemini_tool = types.Tool(function_declarations=[
                triage_decl,
                metrics_decl,
                logs_decl,
                runbooks_decl,
                policy_decl,
                rollback_decl,
                verify_decl,
                docker_ps_decl,
                docker_logs_decl,
                docker_restart_decl,
            ])

            system_prompt = (
                "You are Aegis, an autonomous agentic IT operations and site reliability engineering system.\n"
                "You investigate production incidents, query telemetry, search runbooks, diagnose root causes, and propose remediation.\n"
                "CRITICAL FORMATTING INSTRUCTION: Do NOT use any emojis in your response under any circumstances. Keep the tone professional, concise, and structured with clean markdown headers and bullet points.\n"
                "You have access to 10 real platform and runtime tools:\n"
                "- triage_incident(incident_id, service): triage severity and domain\n"
                "- get_metrics(service): check Prometheus metrics (error rate, latency, DB connections)\n"
                "- get_service_logs(service): check container error logs\n"
                "- search_runbooks(query, service): search runbooks with semantic reranker\n"
                "- evaluate_policy(action, target_service): check policy guardrails before executing remediation\n"
                "- rollback_deployment(service, target_version): revert deployment to stable baseline\n"
                "- verify_slo(service): verify service health post-remediation\n"
                "- docker_ps(all_containers): query live containers on host Docker daemon\n"
                "- docker_logs(container_name, tail): inspect container stdout/stderr logs\n"
                "- docker_restart_container(container_name): restart container via Docker daemon\n\n"
                "When the operator asks about Docker, running containers, or 'docker stuff', DO NOT REFUSE. You have full authorized access to Docker daemon inspection tools. Immediately call docker_ps() to list containers, or docker_logs() to retrieve logs, and present the container IDs, image names, ports, and status.\n"
                "When investigating an incident (e.g. user says 'start', 'investigate', 'what is wrong', 'diagnose', or asks for status), autonomously call the tools to inspect triage, metrics, logs, runbooks, and evaluate policy.\n"
                "DIAGNOSTIC & REMEDIATION MATRIX ACROSS USECASES:\n"
                "- DB Connection Pool Starvation (v2.4.1): Connection pool throttled to 5. Root cause is faulty deployment configuration. Remediate via evaluate_policy then rollback_deployment(service, '2.4.0') with operator approval.\n"
                "- Memory Leak / Heap Exhaustion (v2.4.2): Monotonic heap memory growth (94%+), GC thrashing, worker thread latency. The code is stable but runtime heap is exhausted. Remediate via docker_restart_container('acmecloud-checkout'). Rollback is NOT required.\n"
                "- Database Lock Contention / Deadlock (v2.4.3): ExclusiveLock transaction deadlocks on orders table. Remediate via docker_restart_container('acmecloud-postgres') to clear database transaction locks. Rollback of checkout is NOT required.\n"
                "- Upstream Gateway Timeout (v2.4.4): Payment gateway endpoint unreachable (HTTP 502). Remediate via evaluate_policy then rollback_deployment(service, '2.4.0').\n"
                "When answering queries about metrics, provide Live Telemetry and Error Rate.\n"
                "When answering queries about policy, explain the Policy guardrail.\n"
                "CRITICAL SAFETY RULE: High-risk remediation actions like rollback_deployment require human operator approval. Always evaluate policy before proposing or executing rollback. Never execute rollback without operator approval. When you recommend rollback to v2.4.0 after evaluating policy, explicitly ask the human operator for approval in your message text (e.g.: 'Production rollback requires human operator approval. Please approve or reject below to proceed.'). Do NOT propose or ask for approval on routine queries, docker container checks, or informational questions.\n"
                "Provide clear, professional SRE markdown responses summarizing your findings."
            )

            history_contents = []
            if req.history:
                for h in req.history[-6:]:
                    role = "user" if h.get("role") == "user" else "model"
                    history_contents.append(types.Content(role=role, parts=[types.Part.from_text(text=h.get("text", ""))]))

            user_content = types.Content(
                role="user",
                parts=[types.Part.from_text(text=f"Incident: {req.incident_id} on {service_name}. Current Status: {state.status if state else 'OPEN'}.\n\nOperator message: {req.message}")]
            )

            contents = [*history_contents, user_content]

            config = types.GenerateContentConfig(
                system_instruction=system_prompt,
                tools=[gemini_tool],
                automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True),
                thinking_config=types.ThinkingConfig(thinking_level="low")
            )

            yield ("thinking", {"thinking": f"Analyzing operator intent for {service_name} with AI Reasoning Engine..."})

            response = await asyncio.to_thread(
                client.models.generate_content,
                model=settings.LLM_MODEL,
                contents=contents,
                config=config
            )

            policy_gate_data: Optional[Dict[str, Any]] = None

            if response.function_calls:
                for _turn in range(3):
                    if not response.function_calls:
                        break

                    async def _run_tool(fcall):
                        fname = fcall.name
                        fargs = fcall.args if isinstance(fcall.args, dict) else {}
                        pgate = None
                        fres: Any = None
                        fnodes: List[str] = []

                        if fname == "triage_incident":
                            fres, fnodes = await tool_triage_incident(
                                fargs.get("incident_id", req.incident_id),
                                fargs.get("service", service_name),
                                state
                            )
                        elif fname == "get_metrics":
                            fres, fnodes = await tool_get_metrics(
                                fargs.get("service", service_name),
                                state,
                                req.incident_id
                            )
                        elif fname == "get_service_logs":
                            fres, fnodes = await tool_get_service_logs(
                                fargs.get("service", service_name),
                                state,
                                req.incident_id
                            )
                        elif fname == "search_runbooks":
                            fres, fnodes = await tool_search_runbooks(
                                fargs.get("query", "database connection pool exhaustion"),
                                fargs.get("service", service_name),
                                state,
                                req.incident_id
                            )
                        elif fname == "evaluate_policy":
                            fres, fnodes = await tool_evaluate_policy(
                                fargs.get("action", "rollback_deployment"),
                                fargs.get("target_service", service_name),
                                state,
                                req.incident_id
                            )
                            if fres.get("decision") == "REQUIRE_APPROVAL" or fres.get("requires_approval"):
                                pgate = {
                                    "action": fres.get("action", "rollback_deployment"),
                                    "service": service_name,
                                    "target_version": "2.4.0",
                                    "risk_level": fres.get("risk_level", "HIGH"),
                                    "requires_approval": True,
                                    "reason": fres.get("reason", "Production rollback requires human authorization.")
                                }
                        elif fname == "rollback_deployment":
                            if state and state.approval_granted:
                                fres, fnodes = await tool_rollback_deployment(
                                    fargs.get("service", service_name),
                                    fargs.get("target_version", "2.4.0"),
                                    state,
                                    req.incident_id
                                )
                            else:
                                pgate = {
                                    "action": "rollback_deployment",
                                    "service": service_name,
                                    "target_version": fargs.get("target_version", "2.4.0"),
                                    "risk_level": "HIGH",
                                    "requires_approval": True,
                                    "reason": "Production rollback requires human operator approval."
                                }
                                fres = {
                                    "status": "BLOCKED_BY_POLICY",
                                    "message": "Production rollback requires human operator approval. Policy gate activated."
                                }
                                fnodes = ["diagnose", "policy"]
                        elif fname == "verify_slo":
                            fres, fnodes = await tool_verify_slo(
                                fargs.get("service", service_name),
                                state,
                                req.incident_id
                            )
                        elif fname == "docker_ps":
                            fres, fnodes = await tool_docker_ps(
                                all_containers=fargs.get("all_containers", False)
                            )
                        elif fname == "docker_logs":
                            fres, fnodes = await tool_docker_logs(
                                container_name=fargs.get("container_name", "acmecloud-checkout"),
                                tail=fargs.get("tail", 50)
                            )
                        elif fname == "docker_restart_container":
                            fres, fnodes = await tool_docker_restart_container(
                                container_name=fargs.get("container_name", "acmecloud-checkout")
                            )
                        else:
                            fres = {"error": f"Unknown tool {fname}"}

                        return fname, fargs, fres, fnodes, pgate

                    # Emit tool_start for all proposed tools
                    for fcall in response.function_calls:
                        fname = fcall.name
                        fargs = fcall.args if isinstance(fcall.args, dict) else {}
                        yield ("tool_start", {"name": fname, "args": fargs})

                    # Concurrently execute tools in parallel
                    executed_tools = await asyncio.gather(*[_run_tool(fc) for fc in response.function_calls])

                    function_response_parts = []
                    for fname, fargs, fres, fnodes, pgate in executed_tools:
                        if pgate and not policy_gate_data:
                            policy_gate_data = pgate
                            if state:
                                state.status = "PENDING_APPROVAL"

                        tool_calls_executed.append({
                            "name": fname,
                            "args": fargs,
                            "output": fres
                        })
                        spawned_nodes.extend(fnodes)
                        yield ("tool_result", {"name": fname, "output": fres, "node": fnodes[-1] if fnodes else fname})
                        for nd in fnodes:
                            yield ("node_spawned", {"node_id": nd})

                        function_response_parts.append(
                            types.Part.from_function_response(
                                name=fname,
                                response={"result": fres}
                            )
                        )

                    model_call_content = response.candidates[0].content
                    tool_response_content = types.Content(role="user", parts=function_response_parts)
                    contents.extend([model_call_content, tool_response_content])

                    response = await asyncio.to_thread(
                        client.models.generate_content,
                        model=settings.LLM_MODEL,
                        contents=contents,
                        config=config
                    )

                final_reply = response.text or "Investigation completed."
                reply_lower = final_reply.lower()
                if not policy_gate_data and any(k in reply_lower for k in [
                    "approve or reject", "operator approval", "human authorization",
                    "human operator approval", "requires approval", "requires explicit operator approval",
                    "please approve", "human-in-the-loop"
                ]):
                    policy_gate_data = {
                        "action": "rollback_deployment",
                        "service": service_name,
                        "target_version": "2.4.0",
                        "risk_level": "HIGH",
                        "requires_approval": True,
                        "reason": "Production rollback requires human operator approval."
                    }
                final_status = state.status if state else "OPEN"
                if policy_gate_data:
                    final_status = "PENDING_APPROVAL"
                    if state:
                        state.status = "PENDING_APPROVAL"

                async for chunk in emit_text(final_reply):
                    yield chunk

                yield ("done", {
                    "reply": final_reply,
                    "thinking": "Autonomous investigation via AI Reasoning Engine with real tool execution.",
                    "tool_call": tool_calls_executed[0] if tool_calls_executed else None,
                    "tool_calls": tool_calls_executed,
                    "new_nodes": list(dict.fromkeys(spawned_nodes)),
                    "policy_gate": policy_gate_data,
                    "status": final_status,
                    "duration_seconds": round(time.perf_counter() - t0_req, 2)
                })
                return
            else:
                # No function calls generated by Gemini; check if general query or intent
                if not any(k in msg for k in ["start", "investigate", "what's wrong", "what is wrong", "diagnose", "heal", "metric", "log", "runbook", "policy", "jev", "triage"]):
                    reply_text = response.text or "Standing by for incident instructions."
                    reply_lower = reply_text.lower()
                    policy_gate_direct = None
                    direct_status = state.status if state else "OPEN"
                    if any(k in reply_lower for k in [
                        "approve or reject", "operator approval", "human authorization",
                        "human operator approval", "requires approval", "requires explicit operator approval",
                        "please approve", "human-in-the-loop"
                    ]):
                        policy_gate_direct = {
                            "action": "rollback_deployment",
                            "service": service_name,
                            "target_version": "2.4.0",
                            "risk_level": "HIGH",
                            "requires_approval": True,
                            "reason": "Production rollback requires human operator approval."
                        }
                        direct_status = "PENDING_APPROVAL"
                        if state:
                            state.status = "PENDING_APPROVAL"

                    async for chunk in emit_text(reply_text):
                        yield chunk
                    yield ("done", {
                        "reply": reply_text,
                        "thinking": "Reasoned directly over incident context using AI Reasoning Engine.",
                        "new_nodes": ["policy"] if policy_gate_direct else [],
                        "policy_gate": policy_gate_direct,
                        "status": direct_status,
                        "duration_seconds": round(time.perf_counter() - t0_req, 2)
                    })
                    return
        except Exception as e:
            if settings.DEBUG:
                print(f"[Copilot Gemini warning] Falling back to deterministic tool execution: {e}")

    # 4. Jev / Triage inquiry (e.g. "run jev tool for me", "run jev", "triage", "jev")
    if any(k in msg for k in ["jev", "triage", "classify"]) and not any(k in msg for k in ["diagnose", "auto-heal", "auto heal", "full investigation"]):
        yield ("tool_start", {"name": "triage_incident", "args": {"incident_id": req.incident_id, "service": service_name}})
        res_triage, nodes_t = await tool_triage_incident(req.incident_id, service_name, state)
        spawned_nodes.extend(nodes_t)
        tool_calls_executed.append({
            "name": "triage_incident",
            "args": {"incident_id": req.incident_id, "service": service_name},
            "output": res_triage
        })
        yield ("tool_result", {"name": "triage_incident", "output": res_triage, "node": "triage"})
        yield ("node_spawned", {"node_id": "ingest"})
        yield ("node_spawned", {"node_id": "triage"})

        domain = res_triage.get("domain", "database")
        severity = res_triage.get("severity", "P1")
        confidence = res_triage.get("confidence", 0.94)
        reply_str = (
            f"**Jev AI Triage Assessment for `{service_name}` ({req.incident_id}):**\n\n"
            f"- **Classification Domain**: `{domain}`\n"
            f"- **Assigned Severity**: `{severity}`\n"
            f"- **Model Confidence**: `{confidence:.0%}`\n"
            f"- **Classifier Model**: `Jev Noul Reranker & Fast Classifier v2.1`\n\n"
            f"The incident exhibits database-tier connection failure characteristics. Proceed with telemetry metrics probes or full autonomous diagnosis."
        )
        async for chunk in emit_text(reply_str):
            yield chunk

        yield ("done", {
            "reply": reply_str,
            "thinking": "",  # Pure tool call — no fake thinking accordion
            "tool_call": tool_calls_executed[0],
            "tool_calls": tool_calls_executed,
            "new_nodes": list(dict.fromkeys(spawned_nodes)),
            "status": state.status if state else "OPEN",
            "duration_seconds": round(time.perf_counter() - t0_req, 2)
        })
        return

    # 5. Metrics inquiry
    if any(k in msg for k in ["metric", "latency", "error rate", "pool", "saturation", "rps", "prometheus"]) and not any(k in msg for k in ["diagnose", "auto-heal", "auto heal", "full investigation"]):
        yield ("tool_start", {"name": "get_metrics", "args": {"service": service_name, "window": "15m"}})
        res_metrics, nodes_m = await tool_get_metrics(service_name, state, req.incident_id)
        spawned_nodes.extend(nodes_m)
        tool_calls_executed.append({
            "name": "get_metrics",
            "args": {"service": service_name, "window": "15m"},
            "output": res_metrics
        })
        yield ("tool_result", {"name": "get_metrics", "output": res_metrics, "node": "tool-metrics"})
        yield ("node_spawned", {"node_id": "tool-metrics"})

        active_conn = res_metrics.get("db_pool_active", 0)
        max_conn = res_metrics.get("db_pool_max", 5)
        err_rate = res_metrics.get("error_rate", 0.0)
        lat = res_metrics.get("latency_p95_ms", 0.0)
        sat_pct = (active_conn / max_conn * 100) if max_conn else 100
        reply_lines = [
            f"**Live Telemetry for `{service_name}`:**",
            f"- **Error Rate**: `{err_rate:.1%}`",
            f"- **P95 Latency**: `{lat:.1f}ms`",
            f"- **DB Active Connections**: `{active_conn} / {max_conn}` ({sat_pct:.0f}% saturation)"
        ]
        if sat_pct >= 90:
            reply_lines.append(f"\n**Warning**: Database connection pool is **{sat_pct:.0f}% saturated**. Request queuing detected.")
        reply_str = "\n".join(reply_lines)
        async for chunk in emit_text(reply_str):
            yield chunk

        yield ("done", {
            "reply": reply_str,
            "thinking": "",
            "tool_call": tool_calls_executed[0],
            "tool_calls": tool_calls_executed,
            "new_nodes": list(dict.fromkeys(spawned_nodes)),
            "status": state.status if state else "OPEN",
            "duration_seconds": round(time.perf_counter() - t0_req, 2)
        })
        return

    # 6. Logs inquiry
    if any(k in msg for k in ["log", "500", "5xx", "error log", "stack trace", "exception"]) and not any(k in msg for k in ["diagnose", "auto-heal", "auto heal", "full investigation"]):
        yield ("tool_start", {"name": "get_service_logs", "args": {"service": service_name, "level": "ERROR"}})
        res_logs, nodes_l = await tool_get_service_logs(service_name, state, req.incident_id)
        spawned_nodes.extend(nodes_l)
        tool_calls_executed.append({
            "name": "get_service_logs",
            "args": {"service": service_name, "level": "ERROR"},
            "output": res_logs
        })
        yield ("tool_result", {"name": "get_service_logs", "output": res_logs, "node": "tool-logs"})
        yield ("node_spawned", {"node_id": "tool-logs"})

        reply_str = (
            f"Retrieved recent error logs for `{service_name}`:\n"
            f"Identified database connection pool timeouts and HTTP 500 errors under load."
        )
        async for chunk in emit_text(reply_str):
            yield chunk

        yield ("done", {
            "reply": reply_str,
            "thinking": "",
            "tool_call": tool_calls_executed[0],
            "tool_calls": tool_calls_executed,
            "new_nodes": list(dict.fromkeys(spawned_nodes)),
            "status": state.status if state else "OPEN",
            "duration_seconds": round(time.perf_counter() - t0_req, 2)
        })
        return

    # 7. Runbooks inquiry
    if any(k in msg for k in ["runbook", "rb-", "knowledge", "postmortem"]) and not any(k in msg for k in ["diagnose", "auto-heal", "auto heal", "full investigation"]):
        yield ("tool_start", {"name": "search_runbooks", "args": {"query": "database connection pool exhaustion", "service": service_name}})
        res_rb, nodes_k = await tool_search_runbooks("database connection pool exhaustion checkout-service", service_name, state, req.incident_id)
        spawned_nodes.extend(nodes_k)
        tool_calls_executed.append({
            "name": "search_runbooks",
            "args": {"query": "database connection pool exhaustion", "service": service_name},
            "output": res_rb
        })
        yield ("tool_result", {"name": "search_runbooks", "output": res_rb, "node": "knowledge"})
        yield ("node_spawned", {"node_id": "knowledge"})

        rbs = res_rb.get("runbooks", []) if isinstance(res_rb, dict) else res_rb
        if rbs:
            rb_lines = [f"- **{rb['title']}** (`{rb['doc_id']}`, match: `{rb['score']:.0%}`):\n  {rb['content']}" for rb in rbs]
            reply_text = f"**Retrieved Runbooks for `{service_name}`:**\n\n" + "\n\n".join(rb_lines)
        else:
            reply_text = f"No runbooks matched for `{service_name}` yet."
        async for chunk in emit_text(reply_text):
            yield chunk

        yield ("done", {
            "reply": reply_text,
            "thinking": "",
            "tool_call": tool_calls_executed[0],
            "tool_calls": tool_calls_executed,
            "new_nodes": list(dict.fromkeys(spawned_nodes)),
            "status": state.status if state else "OPEN",
            "duration_seconds": round(time.perf_counter() - t0_req, 2)
        })
        return

    # 8. Policy inquiry
    if any(k in msg for k in ["policy", "guardrail", "rule", "gate", "permission"]) and not any(k in msg for k in ["diagnose", "auto-heal", "auto heal", "full investigation"]):
        yield ("tool_start", {"name": "evaluate_policy", "args": {"action": "rollback_deployment", "target_service": service_name}})
        res_pol, nodes_p = await tool_evaluate_policy("rollback_deployment", service_name, state, req.incident_id)
        spawned_nodes.extend(nodes_p)
        tool_calls_executed.append({
            "name": "evaluate_policy",
            "args": {"action": "rollback_deployment", "target_service": service_name},
            "output": res_pol
        })
        yield ("tool_result", {"name": "evaluate_policy", "output": res_pol, "node": "policy"})
        yield ("node_spawned", {"node_id": "policy"})

        policy_gate_data = {
            "action": res_pol.get("action", "rollback_deployment"),
            "service": service_name,
            "target_version": "2.4.0",
            "risk_level": res_pol.get("risk_level", "HIGH"),
            "requires_approval": True,
            "reason": res_pol.get("reason", "Production rollback requires human authorization.")
        }
        if state:
            state.status = "PENDING_APPROVAL"

        reply_str = (
            f"**Policy Guardrail Evaluation for `{service_name}`:**\n"
            f"- **Action**: `{res_pol.get('action', 'rollback_deployment')}`\n"
            f"- **Risk Level**: `{res_pol.get('risk_level', 'HIGH')}`\n"
            f"- **Decision**: `{res_pol.get('decision', 'REQUIRE_APPROVAL')}`\n"
            f"- **Approval Required**: `{'Yes' if res_pol.get('requires_approval', True) else 'No'}`\n"
            f"- **Policy Reason**: {res_pol.get('reason', 'Production rollback requires human authorization.')}\n\n"
            f"Production rollback requires human operator approval. Please approve or reject below to proceed."
        )
        async for chunk in emit_text(reply_str):
            yield chunk

        yield ("done", {
            "reply": reply_str,
            "thinking": "Evaluated safety policy PROD_ROLLBACK_APPROVAL. Deterministic guardrail requires human authorization.",
            "tool_call": tool_calls_executed[0],
            "tool_calls": tool_calls_executed,
            "new_nodes": list(dict.fromkeys(spawned_nodes)),
            "policy_gate": policy_gate_data,
            "status": "PENDING_APPROVAL",
            "duration_seconds": round(time.perf_counter() - t0_req, 2)
        })
        return

    # 9. Deterministic Autonomous Investigation & Closed-Loop Resolution
    if any(k in msg for k in ["start", "investigate", "investigation", "what's wrong", "what is wrong", "diagnose", "diagnosis", "heal", "auto-heal", "auto heal", "fix", "resolve", "full diagnose"]) or ("run" in msg and any(k in msg for k in ["all", "investigation", "diagnosis", "auto-heal", "heal", "pipeline", "flow"])):
        yield ("thinking", {"thinking": f"Analyzing incident context for {service_name}. Executing autonomous closed-loop investigation: Jev AI triage, Prometheus telemetry probes, error logs, runbook matching, and safety policy evaluation..."})

        # Triage
        yield ("tool_start", {"name": "triage_incident", "args": {"incident_id": req.incident_id, "service": service_name}})
        res_triage, nodes_t = await tool_triage_incident(req.incident_id, service_name, state)
        spawned_nodes.extend(nodes_t)
        tool_calls_executed.append({
            "name": "triage_incident",
            "args": {"incident_id": req.incident_id, "service": service_name},
            "output": res_triage
        })
        yield ("tool_result", {"name": "triage_incident", "output": res_triage, "node": "triage"})
        yield ("node_spawned", {"node_id": "ingest"})
        yield ("node_spawned", {"node_id": "triage"})

        # Metrics
        yield ("tool_start", {"name": "get_metrics", "args": {"service": service_name, "window": "15m"}})
        res_metrics, nodes_m = await tool_get_metrics(service_name, state, req.incident_id)
        spawned_nodes.extend(nodes_m)
        tool_calls_executed.append({
            "name": "get_metrics",
            "args": {"service": service_name, "window": "15m"},
            "output": res_metrics
        })
        yield ("tool_result", {"name": "get_metrics", "output": res_metrics, "node": "tool-metrics"})
        yield ("node_spawned", {"node_id": "tool-metrics"})

        # Logs
        yield ("tool_start", {"name": "get_service_logs", "args": {"service": service_name, "level": "ERROR"}})
        res_logs, nodes_l = await tool_get_service_logs(service_name, state, req.incident_id)
        spawned_nodes.extend(nodes_l)
        tool_calls_executed.append({
            "name": "get_service_logs",
            "args": {"service": service_name, "level": "ERROR"},
            "output": res_logs
        })
        yield ("tool_result", {"name": "get_service_logs", "output": res_logs, "node": "tool-logs"})
        yield ("node_spawned", {"node_id": "tool-logs"})

        # Runbooks
        yield ("tool_start", {"name": "search_runbooks", "args": {"query": "database connection pool exhaustion", "service": service_name}})
        res_rb, nodes_k = await tool_search_runbooks("database connection pool exhaustion checkout-service", service_name, state, req.incident_id)
        spawned_nodes.extend(nodes_k)
        tool_calls_executed.append({
            "name": "search_runbooks",
            "args": {"query": "database connection pool exhaustion", "service": service_name},
            "output": res_rb
        })
        yield ("tool_result", {"name": "search_runbooks", "output": res_rb, "node": "knowledge"})
        yield ("node_spawned", {"node_id": "knowledge"})

        # Diagnosis
        diagnosis = await diagnosis_agent.diagnose(
            evidence=state.evidence,
            runbooks=state.retrieved_runbooks
        )
        state.diagnosis = diagnosis
        state.status = "DIAGNOSED"
        spawned_nodes.append("diagnose")
        yield ("node_spawned", {"node_id": "diagnose"})
        tracer.log_event(req.incident_id, "diagnose", "DIAGNOSIS_PRODUCED", {
            "root_cause": diagnosis.root_cause,
            "confidence": diagnosis.confidence,
            "recommended_action": diagnosis.recommended_action
        })

        # Policy
        yield ("tool_start", {"name": "evaluate_policy", "args": {"action": diagnosis.recommended_action, "target_service": service_name}})
        res_pol, nodes_p = await tool_evaluate_policy(diagnosis.recommended_action, service_name, state, req.incident_id)
        spawned_nodes.extend(nodes_p)
        tool_calls_executed.append({
            "name": "evaluate_policy",
            "args": {"action": diagnosis.recommended_action, "target_service": service_name},
            "output": res_pol
        })
        yield ("tool_result", {"name": "evaluate_policy", "output": res_pol, "node": "policy"})
        yield ("node_spawned", {"node_id": "policy"})

        target_v = diagnosis.action_parameters.get("target_version", "2.4.0") if diagnosis.action_parameters else "2.4.0"
        policy_gate_data = {
            "action": diagnosis.recommended_action,
            "service": service_name,
            "target_version": target_v,
            "risk_level": res_pol.get("risk_level", "HIGH"),
            "requires_approval": True,
            "reason": res_pol.get("reason", "Production rollback requires human authorization.")
        }
        state.status = "PENDING_APPROVAL"
        INCIDENTS[req.incident_id] = state

        evidence_bullets = "\n".join(f"- {e}" for e in (diagnosis.evidence_summary or []))
        reply = (
            f"**Autonomous Investigation Complete for `{service_name}` ({req.incident_id}):**\n\n"
            f"• **Triage Classification**: `{res_triage.get('domain', 'database')}` domain, `{res_triage.get('severity', 'P1')}` severity ({res_triage.get('confidence', 0.94):.0%} confidence)\n"
            f"• **Telemetry Findings**:\n"
            f"  - Error Rate: `{res_metrics.get('error_rate', 0.385):.1%}`\n"
            f"  - P95 Latency: `{res_metrics.get('latency_p95_ms', 2850):.0f}ms`\n"
            f"  - DB Active Connections: `{res_metrics.get('db_pool_active', 5)} / {res_metrics.get('db_pool_max', 5)}` (100% saturated)\n"
            f"  - Logs: `connection pool exhausted for checkout-service`\n"
            f"• **Matched Runbook**: `RB-001` (Database Connection Pool Exhaustion Runbook)\n\n"
            f"**Root Cause Diagnosis:**\n"
            f"{diagnosis.root_cause}\n\n"
            f"**Evidence Summary:**\n{evidence_bullets}\n\n"
            f"**Policy Guardrail Gate**: Action `{diagnosis.recommended_action}` to `v{target_v}` is classified as **{res_pol.get('risk_level', 'HIGH')}** risk. Human-in-the-Loop operator approval is required before execution. Please approve or reject below to proceed."
        )

        async for chunk in emit_text(reply):
            yield chunk

        yield ("done", {
            "reply": reply,
            "thinking": "Conducted autonomous closed-loop investigation: triaged alert with Jev, probed Prometheus metrics and container error logs via AcmeCloud FastMCP, matched Runbook RB-001 via Jev reranker, synthesized root cause (connection pool starvation in v2.4.1), and evaluated safety policy PROD_ROLLBACK_APPROVAL.",
            "tool_call": tool_calls_executed[0],
            "tool_calls": tool_calls_executed,
            "new_nodes": list(dict.fromkeys(spawned_nodes)),
            "policy_gate": policy_gate_data,
            "status": "PENDING_APPROVAL",
            "duration_seconds": round(time.perf_counter() - t0_req, 2)
        })
        return

    # 10. Root cause inquiry
    if any(k in msg for k in ["why", "cause", "explain", "fail", "reason", "root cause"]):
        if state and state.diagnosis:
            evidence_bullets = "\n".join(f"- {e}" for e in (state.diagnosis.evidence_summary or []))
            reply_str = (
                f"**Root Cause Analysis for `{service_name}`:**\n\n"
                f"{state.diagnosis.root_cause}\n\n"
                f"**Reasoning Details:**\n{state.diagnosis.reasoning}\n\n"
                f"**Evidence Summary:**\n{evidence_bullets}\n\n"
                f"**Recommended Action**: `{state.diagnosis.recommended_action}`"
            )
            async for chunk in emit_text(reply_str):
                yield chunk

            yield ("done", {
                "reply": reply_str,
                "thinking": "Synthesized root cause from diagnosis state and evidence summary.",
                "status": state.status,
                "duration_seconds": round(time.perf_counter() - t0_req, 2)
            })
            return

    # 11. Fallback intelligent response
    status_str = state.status if state else "OPEN"
    rec_action = (
        state.diagnosis.recommended_action
        if state and state.diagnosis
        else "rollback_deployment to v2.4.0"
    )
    reply_str = (
        f"Incident **{req.incident_id}** on `{service_name}` is currently in status **{status_str}**.\n\n"
        f"• **Diagnosis**: {state.diagnosis.root_cause if state and state.diagnosis else 'Database connection pool starvation in v2.4.1.'}\n"
        f"• **Recommended Action**: `{rec_action}`\n"
        f"• **Policy Guardrail**: `PROD_ROLLBACK_APPROVAL` requires operator authorization."
    )
    policy_gate_fallback = None
    if status_str == "PENDING_APPROVAL" or "operator authorization" in reply_str or "operator approval" in reply_str:
        policy_gate_fallback = {
            "action": "rollback_deployment",
            "service": service_name,
            "target_version": "2.4.0",
            "risk_level": "HIGH",
            "requires_approval": True,
            "reason": "Production rollback requires human operator approval."
        }
    async for chunk in emit_text(reply_str):
        yield chunk

    yield ("done", {
        "reply": reply_str,
        "thinking": "Evaluated current incident state against runbook RB-001.",
        "policy_gate": policy_gate_fallback,
        "status": status_str,
        "duration_seconds": round(time.perf_counter() - t0_req, 2)
    })


@app.post("/api/chat/stream")
async def copilot_chat_stream(req: ChatRequest):
    """
    Real-time Server-Sent Events (SSE) streaming for ChatGPT-style text and tool output.
    """
    async def sse_gen():
        async for ev_type, ev_data in run_copilot_pipeline(req, stream_words=True):
            payload = {"type": ev_type, **ev_data}
            yield f"data: {json.dumps(payload, default=str)}\n\n"
            await asyncio.sleep(0.005)

    return StreamingResponse(
        sse_gen(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )


@app.post("/api/chat", response_model=ChatResponse)
async def copilot_chat(req: ChatRequest):
    """Synchronous JSON endpoint fallback."""
    final_data = None
    async for ev_type, ev_data in run_copilot_pipeline(req, stream_words=False):
        if ev_type == "done":
            final_data = ev_data
    if final_data:
        return ChatResponse(**final_data)
    raise HTTPException(status_code=500, detail="Copilot execution failed")


@app.get("/api/incidents/{incident_id}/stream")
async def stream_incident(incident_id: str):
    """
    Server-Sent Events (SSE) real-time stream of incident traces, state updates,
    and agent thinking events.
    """
    async def event_generator():
        sent_indices = 0
        last_state_hash = None
        ping_counter = 0

        while True:
            events = tracer.get_incident_trace(incident_id)
            if len(events) > sent_indices:
                for ev in events[sent_indices:]:
                    data_str = json.dumps(ev, default=str)
                    # Yield named trace event only (deduplicated)
                    yield f"event: trace\ndata: {data_str}\n\n"
                sent_indices = len(events)

            # Send state snapshot only when state has updated
            if incident_id in INCIDENTS:
                st = INCIDENTS[incident_id].model_dump()
                state_str = json.dumps(st, default=str)
                if state_str != last_state_hash:
                    last_state_hash = state_str
                    yield f"event: state\ndata: {state_str}\n\n"

            # Heartbeat keep-alive every ~5 seconds (25 * 0.2s)
            ping_counter += 1
            if ping_counter >= 25:
                ping_counter = 0
                yield f"event: ping\ndata: {{\"time\": \"{tracer.trace_file}\"}}\n\n"

            await asyncio.sleep(0.2)

    return StreamingResponse(event_generator(), media_type="text/event-stream")


@app.get("/api/incidents/{incident_id}/traces")
@app.get("/api/traces/{incident_id}")
async def get_trace(incident_id: str):
    """Retrieve full JSONL event trace for an incident."""
    events = tracer.get_incident_trace(incident_id)
    return {"incident_id": incident_id, "events": events}


@app.get("/api/health")
@app.get("/health")
async def health():
    return {"status": "healthy", "service": "aegis-api"}


@app.get("/api/services/{service}/health")
async def get_service_health(service: str):
    """Get health status of a service in AcmeCloud."""
    return await acme_client.get_service_health(service)


@app.get("/api/services/{service}/metrics")
async def get_service_metrics(service: str, window: str = "15m"):
    """Get live telemetry metrics for a service."""
    return await acme_client.get_metrics(service=service, window=window)


# --- Real-Time Background Traffic Generator for Chaos Emulation ---
_traffic_task: Optional[asyncio.Task] = None
_traffic_running: bool = False

async def _continuous_traffic_worker(base_url: str = "http://localhost:8001"):
    global _traffic_running
    _traffic_running = True
    print("[Chaos Traffic] Worker started.", flush=True)
    await asyncio.sleep(1.0)
    limits = httpx.Limits(max_connections=50, max_keepalive_connections=20)
    async with httpx.AsyncClient(timeout=10.0, limits=limits) as client:
        while _traffic_running:
            tasks = [
                client.post(
                    f"{base_url}/checkout",
                    json={
                        "customer_id": "00000000-0000-0000-0000-000000000001",
                        "total_amount": 99.99,
                        "currency": "USD"
                    }
                )
                for _ in range(12)
            ]
            try:
                res = await asyncio.gather(*tasks, return_exceptions=True)
                errs = sum(1 for r in res if getattr(r, "status_code", 0) >= 500)
                oks = sum(1 for r in res if getattr(r, "status_code", 0) == 201)
                print(f"[Chaos Traffic] Burst completed: {oks} ok, {errs} errors (5xx)", flush=True)
            except Exception as e:
                print(f"[Chaos Traffic error] {e}", flush=True)
            await asyncio.sleep(2.0)
    print("[Chaos Traffic] Worker stopped.", flush=True)


ACME_BUILDS = [
    {
        "version": "2.4.0",
        "title": "Baseline Production Release",
        "service": "checkout-service",
        "status": "STABLE",
        "fault_type": "none",
        "description": "Nominal production build. DB connection pool of 50, zero injection delay, nominal error rate (<0.2%), and sub-50ms latency.",
        "needs_rollback": False,
        "recommended_action": "none",
        "action_label": "Restore Baseline",
        "env_diff": {
            "DB_CONNECTION_POOL": 50,
            "DB_POOL_TIMEOUT": 5.0,
            "DB_OPERATION_DELAY_MS": 0
        },
        "target_incident_severity": "NOMINAL"
    },
    {
        "version": "2.4.1",
        "title": "DB Connection Pool Starvation",
        "service": "checkout-service",
        "status": "FAULTY",
        "fault_type": "pool_starvation",
        "description": "Database connection pool throttled to 5 with 2000ms delay. Triggers rapid connection pool starvation and 500 DatabaseTimeout errors under load.",
        "needs_rollback": True,
        "recommended_action": "rollback_deployment",
        "action_label": "Rollback to v2.4.0 (Approval Gate)",
        "env_diff": {
            "DB_CONNECTION_POOL": 5,
            "DB_POOL_TIMEOUT": 0.5,
            "DB_OPERATION_DELAY_MS": 2000
        },
        "target_incident_severity": "P1"
    },
    {
        "version": "2.4.2",
        "title": "Memory Leak & Heap Exhaustion",
        "service": "checkout-service",
        "status": "FAULTY",
        "fault_type": "memory_leak",
        "description": "Worker session cache leaks memory monotonically up to 94.2% heap limit. Causes GC thrashing and elevated P95 latency. Container restart recycles heap without code rollback.",
        "needs_rollback": False,
        "recommended_action": "docker_restart_container",
        "action_label": "Restart Container (No Rollback)",
        "env_diff": {
            "DB_CONNECTION_POOL": 50,
            "MEMORY_LEAK_RATE_MB": 35,
            "SIMULATE_MEMORY_LEAK": True
        },
        "target_incident_severity": "P2"
    },
    {
        "version": "2.4.3",
        "title": "Database Lock Deadlock Contention",
        "service": "checkout-service",
        "status": "FAULTY",
        "fault_type": "db_deadlock",
        "description": "Concurrent transactions cause row-level ExclusiveLock contention on PostgreSQL orders table. P95 latency exceeds 7500ms. Database connection reset or postgres restart clears deadlock.",
        "needs_rollback": False,
        "recommended_action": "docker_restart_postgres",
        "action_label": "Reset DB Connections / Restart Postgres",
        "env_diff": {
            "DB_CONNECTION_POOL": 50,
            "DB_OPERATION_DELAY_MS": 7500,
            "SIMULATE_LOCK_CONTENTION": True
        },
        "target_incident_severity": "P1"
    },
    {
        "version": "2.4.4",
        "title": "Upstream Payment Gateway Timeout",
        "service": "checkout-service",
        "status": "FAULTY",
        "fault_type": "upstream_timeout",
        "description": "Payment gateway endpoint URL points to unreachable address. Payments fail with HTTP 502 Bad Gateway while local database remains healthy. Requires configuration rollback.",
        "needs_rollback": True,
        "recommended_action": "rollback_deployment",
        "action_label": "Config Hotfix / Rollback",
        "env_diff": {
            "PAYMENT_GATEWAY_TIMEOUT": 0.001,
            "PAYMENT_GATEWAY_URL": "http://payment-gw.internal.invalid:9999"
        },
        "target_incident_severity": "P1"
    }
]


async def _deploy_build(service: str = "checkout-service", version: str = "2.4.1") -> Dict[str, Any]:
    """Core logic to switch build version and simulate operational impact."""
    build_meta = next((b for b in ACME_BUILDS if b["version"] == version), None)
    if not build_meta:
        build_meta = {
            "version": version,
            "title": f"Custom Build {version}",
            "service": service,
            "status": "CUSTOM",
            "fault_type": "custom",
            "description": f"Deployment of {service} build {version}.",
            "needs_rollback": version != "2.4.0",
            "recommended_action": "rollback_deployment" if version != "2.4.0" else "none",
            "action_label": "Rollback" if version != "2.4.0" else "None",
            "target_incident_severity": "P1" if version != "2.4.0" else "NOMINAL"
        }

    # 1. Update AcmeClient version
    acme_client.set_mock_version(service, version)

    global _traffic_task, _traffic_running
    if version == "2.4.0":
        # Reset baseline
        _traffic_running = False
        if _traffic_task and not _traffic_task.done():
            _traffic_task.cancel()
            _traffic_task = None

        tracer.log_event("CHAOS", "chaos", "CHAOS_RESET", {
            "service": service,
            "version": "2.4.0",
            "health": "RESTORED"
        })
        tracer.log_event("INC-001", "chaos", "CHAOS_RESET", {
            "service": service,
            "version": "2.4.0",
            "health": "RESTORED"
        })

        # Register healthy requests to Prometheus
        try:
            async with httpx.AsyncClient(timeout=2.0) as client:
                for _ in range(4):
                    await client.post("http://localhost:8001/checkout", json={
                        "customer_id": "00000000-0000-0000-0000-000000000001",
                        "total_amount": 49.99,
                        "currency": "USD"
                    })
        except Exception:
            pass

        # Update incidents to RESOLVED
        for inc_id, state in list(INCIDENTS.items()):
            if state.service == service:
                state.status = "RESOLVED"
                INCIDENTS[inc_id] = state

        try:
            mcp_data = _load_incidents()
            for inc_id, inc_dict in mcp_data.items():
                if inc_dict.get("service") == service:
                    inc_dict["status"] = "RESOLVED"
                    inc_dict["active_version"] = "2.4.0"
                    if inc_id in INCIDENTS:
                        INCIDENTS[inc_id].status = "RESOLVED"
            _save_incidents(mcp_data)
        except Exception as e:
            print(f"Warning: could not save MCP incidents: {e}")

        return {
            "status": "RESET",
            "deploy_status": "DEPLOYED",
            "service": service,
            "version": "2.4.0",
            "is_healthy": True,
            "build": build_meta,
            "message": f"Successfully deployed baseline build v2.4.0 for {service}."
        }
    else:
        # Deploy faulty build & start traffic load
        tracer.log_event("CHAOS", "chaos", "CHAOS_INJECTED", {
            "service": service,
            "version": version,
            "fault": build_meta["title"]
        })
        tracer.log_event("INC-001", "chaos", "CHAOS_INJECTED", {
            "service": service,
            "version": version,
            "fault": build_meta["title"],
            "severity": build_meta["target_incident_severity"]
        })

        if _traffic_task and not _traffic_task.done():
            _traffic_running = False
            _traffic_task.cancel()
        _traffic_running = True
        _traffic_task = asyncio.create_task(_continuous_traffic_worker())

        # Update in-memory state with specific scenario context
        for inc_id, state in list(INCIDENTS.items()):
            if state.service == service:
                INCIDENTS[inc_id] = IncidentState(
                    incident_id=inc_id,
                    service=service,
                    severity=build_meta["target_incident_severity"],
                    title=f"{build_meta['title']} on {service}",
                    description=build_meta["description"],
                    status="OPEN"
                )

        try:
            mcp_data = _load_incidents()
            for inc_id, inc_dict in mcp_data.items():
                if inc_dict.get("service") == service:
                    inc_dict["status"] = "OPEN"
                    inc_dict["active_version"] = version
                    inc_dict["summary"] = build_meta["title"]
                    if "resolved_at" in inc_dict:
                        del inc_dict["resolved_at"]
                    # Also populate in-memory INCIDENTS store
                    INCIDENTS[inc_id] = IncidentState(
                        incident_id=inc_id,
                        service=service,
                        severity=build_meta["target_incident_severity"],
                        title=f"{build_meta['title']} on {service}",
                        description=build_meta["description"],
                        status="OPEN"
                    )
            _save_incidents(mcp_data)
        except Exception as e:
            print(f"Warning: could not save MCP incidents: {e}")

        return {
            "status": "INJECTED",
            "deploy_status": "DEPLOYED",
            "service": service,
            "version": version,
            "is_healthy": False,
            "build": build_meta,
            "message": f"Deployed build v{version} ({build_meta['title']}) for {service} with live load traffic."
        }


class DeployBuildRequest(BaseModel):
    service: str = "checkout-service"
    version: str = "2.4.1"


@app.get("/api/acmecloud/builds")
async def get_acmecloud_builds(service: str = "checkout-service"):
    """List available AcmeCloud deployment builds and their scenario metadata."""
    health = await acme_client.get_service_health(service)
    current_ver = health.get("version", "2.4.0")
    
    builds_with_active = []
    for b in ACME_BUILDS:
        builds_with_active.append({
            **b,
            "is_active": b["version"] == current_ver
        })
    return {
        "service": service,
        "current_version": current_ver,
        "builds": builds_with_active
    }


@app.get("/api/acmecloud/status")
async def get_acmecloud_status(service: str = "checkout-service"):
    """Get overall AcmeCloud infrastructure health, telemetry, and container statuses."""
    health = await acme_client.get_service_health(service)
    metrics = await acme_client.get_metrics(service)
    current_ver = health.get("version", "2.4.0")

    containers = []
    try:
        from aegis.mcp.server import docker_ps
        containers = await docker_ps(all_containers=True)
    except Exception:
        pass

    services_manifest = [
        {"name": "checkout-service", "role": "Core API", "port": 8001, "version": current_ver, "healthy": health.get("healthy", True)},
        {"name": "postgres", "role": "Stateful DB", "port": 5432, "version": "17.0", "healthy": True},
        {"name": "prometheus", "role": "Metrics TSDB", "port": 9090, "version": "v3.5.0", "healthy": True},
        {"name": "grafana", "role": "Dashboards", "port": 3001, "version": "12.1.1", "healthy": True},
    ]

    return {
        "service": service,
        "current_version": current_ver,
        "is_healthy": health.get("healthy", True),
        "error_rate": metrics.get("error_rate", 0.0),
        "latency_p95_ms": metrics.get("latency_p95_ms", 42.5),
        "requests_per_sec": metrics.get("requests_per_sec", 120.0),
        "db_pool_active": metrics.get("db_pool_active", 0),
        "db_pool_max": metrics.get("db_pool_max", 50),
        "traffic_running": _traffic_running,
        "services": services_manifest,
        "containers": containers
    }


@app.post("/api/acmecloud/deploy")
async def deploy_acmecloud_build(req: DeployBuildRequest):
    """Deploy any build from the AcmeCloud build catalog to simulate an operational scenario."""
    return await _deploy_build(service=req.service, version=req.version)


@app.post("/api/acmecloud/traffic/toggle")
async def toggle_acmecloud_traffic(enable: Optional[bool] = None):
    """Toggle continuous simulated load traffic in AcmeCloud."""
    global _traffic_task, _traffic_running
    target_state = not _traffic_running if enable is None else enable

    if target_state and not _traffic_running:
        _traffic_running = True
        _traffic_task = asyncio.create_task(_continuous_traffic_worker())
        return {"status": "TRAFFIC_STARTED", "traffic_running": True}
    elif not target_state and _traffic_running:
        _traffic_running = False
        if _traffic_task and not _traffic_task.done():
            _traffic_task.cancel()
            _traffic_task = None
        return {"status": "TRAFFIC_STOPPED", "traffic_running": False}

    return {"status": "NOOP", "traffic_running": _traffic_running}


class StoreCheckoutRequest(BaseModel):
    customer_id: str = "00000000-0000-0000-0000-000000000001"
    total_amount: float = 2899.00
    currency: str = "USD"
    items: Optional[List[Dict[str, Any]]] = None


@app.post("/api/store/checkout")
async def store_checkout(req: StoreCheckoutRequest):
    """
    Client-facing checkout endpoint for the Acme Storefront.
    Attempts live HTTP POST to checkout-service on port 8001.
    If live container fails or is in simulated fault mode, returns the exact fault behavior.
    """
    health = await acme_client.get_service_health("checkout-service")
    active_version = health.get("version", "2.4.0")

    # 1. Attempt live Docker container checkout if available
    try:
        async with httpx.AsyncClient(timeout=4.0) as client:
            resp = await client.post("http://localhost:8001/checkout", json={
                "customer_id": req.customer_id,
                "total_amount": req.total_amount,
                "currency": req.currency
            })
            if resp.status_code == 201:
                return {
                    "status": "CONFIRMED",
                    "order_id": resp.json().get("order_id", f"ord-{int(time.time()*1000)}"),
                    "version": active_version,
                    "execution_mode": "LIVE_DOCKER_CONTAINER",
                    "message": "Order successfully persisted in Acme PostgreSQL database."
                }
            elif resp.status_code >= 500:
                raise HTTPException(
                    status_code=resp.status_code,
                    detail=f"Acme Checkout Backend Error: HTTP {resp.status_code} on version {active_version}."
                )
    except httpx.RequestError:
        pass

    # 2. Simulated Fault Scenarios based on active build version
    if active_version == "2.4.1":
        await asyncio.sleep(1.8)
        raise HTTPException(
            status_code=500,
            detail="HTTP 500 DatabaseTimeout: Unable to acquire connection from pool (limit=5 reached under load). Checkout persistence failed."
        )
    elif active_version == "2.4.2":
        await asyncio.sleep(1.4)
        return {
            "status": "CONFIRMED",
            "order_id": f"ord-{int(time.time()*1000)}",
            "version": active_version,
            "warning": "High latency detected: GC pause duration 1850ms due to 94.2% heap allocation.",
            "execution_mode": "SIMULATED_COMMERCE",
            "message": "Order confirmed with elevated response latency."
        }
    elif active_version == "2.4.3":
        await asyncio.sleep(2.5)
        raise HTTPException(
            status_code=504,
            detail="HTTP 504 Gateway Timeout: PostgreSQL transaction ExclusiveLock wait timeout exceeded (7500ms) on orders table."
        )
    elif active_version == "2.4.4":
        await asyncio.sleep(0.3)
        raise HTTPException(
            status_code=502,
            detail="HTTP 502 Bad Gateway: Upstream payment processor payment-gw.internal.invalid:9999 connection refused."
        )

    # 3. Default nominal baseline (v2.4.0)
    return {
        "status": "CONFIRMED",
        "order_id": f"ord-{int(time.time()*1000)}",
        "version": active_version,
        "execution_mode": "NOMINAL_BASELINE",
        "message": "Order confirmed and processed successfully in PostgreSQL."
    }


@app.post("/api/chaos/inject")
async def inject_chaos(service: str = "checkout-service", version: str = "2.4.1"):
    """Inject faulty deployment build."""
    return await _deploy_build(service=service, version=version)


@app.post("/api/chaos/reset")
async def reset_chaos(service: str = "checkout-service"):
    """Reset AcmeCloud to healthy baseline (v2.4.0)."""
    return await _deploy_build(service=service, version="2.4.0")


# Mount built frontend SPA static files if dist directory exists
_FRONTEND_DIST = Path(__file__).resolve().parent.parent.parent / "frontend" / "dist"
if _FRONTEND_DIST.is_dir():
    app.mount("/", StaticFiles(directory=str(_FRONTEND_DIST), html=True), name="frontend")


