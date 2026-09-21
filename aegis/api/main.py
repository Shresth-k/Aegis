from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Dict, Any, Optional
from aegis.core.state import IncidentState, IncidentAlert
from aegis.graph.workflow import aegis_graph, remediate_node, verify_node
from aegis.core.tracer import tracer

app = FastAPI(
    title="Aegis Incident Resolution Platform",
    description="Agentic IT Operations & Autonomous Incident Resolution API",
    version="0.1.0"
)

# In-memory incident store for active sessions
INCIDENTS: Dict[str, IncidentState] = {}

class ApprovalRequest(BaseModel):
    approved: bool
    approved_by: str
    reason: Optional[str] = "Operator verified diagnosis and approved remediation."

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

    # Execute workflow up to approval boundary or resolution
    final_output = await aegis_graph.ainvoke(state)
    state = IncidentState(**{**state.model_dump(), **final_output})
    INCIDENTS[alert.incident_id] = state
    return state

@app.get("/api/incidents/{incident_id}", response_model=IncidentState)
async def get_incident(incident_id: str):
    """Get current state of an incident."""
    if incident_id not in INCIDENTS:
        raise HTTPException(status_code=404, detail="Incident not found")
    return INCIDENTS[incident_id]

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

@app.get("/api/traces/{incident_id}")
async def get_trace(incident_id: str):
    """Retrieve full JSONL event trace for an incident."""
    events = tracer.get_incident_trace(incident_id)
    return {"incident_id": incident_id, "events": events}

@app.get("/health")
async def health():
    return {"status": "healthy", "service": "aegis-api"}
