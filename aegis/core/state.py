from typing import List, Dict, Any, Optional, Literal
from pydantic import BaseModel, Field
from datetime import datetime, timezone

def utc_now():
    return datetime.now(timezone.utc)

class IncidentAlert(BaseModel):
    incident_id: str
    service: str
    severity: Literal["P1", "P2", "P3", "P4"] = "P2"
    title: str
    description: str
    created_at: datetime = Field(default_factory=utc_now)
    metadata: Dict[str, Any] = Field(default_factory=dict)

class TelemetryEvidence(BaseModel):
    service: str
    current_version: str
    previous_version: Optional[str] = None
    recent_deployment: bool = False
    metrics: Dict[str, Any] = Field(default_factory=dict)
    error_logs: List[str] = Field(default_factory=list)
    dependencies: List[str] = Field(default_factory=list)
    dependency_health: Dict[str, bool] = Field(default_factory=dict)

class RetrievedRunbook(BaseModel):
    doc_id: str
    title: str
    content: str
    score: float = 0.0
    source_type: Literal["runbook", "postmortem", "policy", "architecture"] = "runbook"

class DiagnosisResult(BaseModel):
    root_cause: str
    confidence: float = Field(ge=0.0, le=1.0)
    evidence_summary: List[str]
    recommended_action: str
    action_parameters: Dict[str, Any]
    reasoning: str

class PolicyEvaluation(BaseModel):
    action: str
    risk_level: Literal["READ_ONLY", "LOW", "MEDIUM", "HIGH", "FORBIDDEN"]
    decision: Literal["ALLOW", "REQUIRE_APPROVAL", "DENY"]
    requires_approval: bool
    reason: str

class RemediationResult(BaseModel):
    action: str
    target_service: str
    parameters: Dict[str, Any]
    status: Literal["SUCCESS", "FAILED", "SKIPPED"]
    executed_at: datetime = Field(default_factory=utc_now)
    message: str

class VerificationResult(BaseModel):
    is_healthy: bool
    error_rate: Optional[float] = None
    latency_ms: Optional[float] = None
    service_version: str
    status: Literal["SUCCESS", "FAILED"]
    details: str

class IncidentState(BaseModel):
    # Incident Identifiers
    incident_id: str
    service: str
    severity: Literal["P1", "P2", "P3", "P4"]
    title: str
    description: str
    
    # State flags
    status: Literal["OPEN", "INVESTIGATING", "DIAGNOSED", "PENDING_APPROVAL", "REMEDIATING", "VERIFYING", "RESOLVED", "ESCALATED"] = "OPEN"
    
    # Evidence & Analysis
    evidence: Optional[TelemetryEvidence] = None
    retrieved_runbooks: List[RetrievedRunbook] = Field(default_factory=list)
    diagnosis: Optional[DiagnosisResult] = None
    
    # Policy & Governance
    policy_evaluation: Optional[PolicyEvaluation] = None
    approval_granted: Optional[bool] = None
    approved_by: Optional[str] = None
    approval_reason: Optional[str] = None
    
    # Action & Verification
    remediation: Optional[RemediationResult] = None
    verification: Optional[VerificationResult] = None
    
    # History & Trajectory
    trajectory_log: List[Dict[str, Any]] = Field(default_factory=list)
    updated_at: datetime = Field(default_factory=utc_now)
