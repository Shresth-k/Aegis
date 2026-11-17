# OpsPilot Development Plan: NEXT

> Last updated: 2026-09-22
>
> Starting point: Phase 4
>
> Phases 0 through 3 are complete.
>
> This document describes the remaining implementation required to reach the full OpsPilot system.

---

# 1. Purpose

This document is the forward implementation plan for OpsPilot.

The completed foundation currently provides a deterministic AcmeCloud simulation and a working scenario engine.

The remaining work is to build the actual OpsPilot operational intelligence layer around that simulation.

The target system must evolve from:

```text
Scenario execution infrastructure
```

into:

```text
Agentic IT operations and incident resolution platform
```

The implementation should preserve the project's central principle:

> OpsPilot must infer operational causes from evidence and operate through explicit policy, authorization, approval, action, and verification boundaries.

---

# 2. Target Operational Loop

The final system must implement:

```text
INCIDENT
    ↓
OBSERVE
    ↓
INVESTIGATE
    ↓
REASON
    ↓
CHECK POLICY
    ↓
REQUEST APPROVAL
    ↓
ACT
    ↓
VERIFY
    ↓
RESOLVE
    ↘
   INVESTIGATE AGAIN
    ↓
ESCALATE
```

The loop must be represented as executable system behavior, not merely documentation.

---

# 3. Phase 4: MCP Operational Tools

## Objective

Expose AcmeCloud operational capabilities to OpsPilot through well-defined MCP tools.

MCP is the boundary between the agentic system and operational systems.

The first tool families are:

```text
Metrics MCP
Logs MCP
Deployment MCP
Incident MCP
```

The repository already has corresponding directories:

```text
mcp/
├── common/
├── metrics/
├── logs/
├── deployments/
└── incidents/
```

---

## 3.1 Metrics MCP

Build a read-only operational metrics interface.

It should support controlled access to metrics such as:

```text
checkout_requests_total
checkout_errors_total
checkout_error_rate
checkout_latency
db_connections_active
db_connection_wait_time
payment_request_latency
payment_errors_total
inventory_request_latency
```

The MCP layer should expose structured responses rather than raw unbounded Prometheus responses where practical.

Required concerns:

- strict input schemas
- strict output schemas
- service validation
- metric validation
- bounded time ranges
- bounded result sizes
- deterministic error behavior
- tests against the real Prometheus instance

The agent should be able to answer operational questions such as:

```text
What is the checkout error rate?
Is latency increasing?
Are database connections saturated?
Did failures begin after the deployment?
```

---

# 4. Logs MCP

Build a controlled log retrieval interface.

The tool should support operational investigation by allowing OpsPilot to retrieve relevant checkout-service logs.

Required capabilities should include:

- service filtering
- time-window filtering
- severity filtering
- bounded result count
- structured results
- deterministic ordering
- safe handling of malformed or unavailable logs

The tool must not become an unrestricted arbitrary host command interface.

The purpose is evidence retrieval.

---

# 5. Deployment MCP

Expose deployment state and deployment history.

The deployment interface should support read operations such as:

```text
Get current version
Get previous version
Get deployment status
Get deployment history
Get deployment timestamp
Get deployment actor
```

Later it will also expose controlled remediation operations such as:

```text
Rollback service
Deploy specific approved version
```

However, deployment actions must not bypass policy or human approval.

The MCP action boundary should remain explicit.

---

# 6. Incident MCP

Expose operational incident state.

Required capabilities include:

```text
Create incident
Get incident
Update incident status
List incidents
Record investigation information
Record remediation information
```

Incident state should remain separate from scenario evaluation metadata.

The system must never expose:

```text
expected_root_cause
expected_action
```

to the agent through operational incident APIs.

---

# 7. MCP Safety and Contracts

Every MCP tool should have:

- explicit input schema
- explicit output schema
- validation
- bounded access
- deterministic errors
- unit tests
- integration tests
- documentation

Consequential actions must have explicit authorization boundaries.

The LLM itself is not an authorization system.

The architecture must prevent an agent from bypassing:

```text
policy
risk checks
approval requirements
audit logging
```

---

# 8. Phase 5: Knowledge and RAG

## Objective

Give OpsPilot access to organizational knowledge needed for investigation and remediation reasoning.

Knowledge sources include:

```text
architecture documents
policies
runbooks
postmortems
templates
```

The repository already has:

```text
knowledge/
rag/
```

The implementation should establish:

```text
Knowledge documents
        ↓
Ingestion
        ↓
Chunking
        ↓
Embeddings
        ↓
Vector database
        ↓
Retrieval
        ↓
Investigation context
```

PostgreSQL remains the authoritative operational state store.

The vector store is for organizational knowledge retrieval.

---

# 9. RAG Context Construction

Build a context layer that combines:

```text
Incident
+
Metrics
+
Logs
+
Deployment history
+
Dependency information
+
Incident history
+
Runbooks
+
Postmortems
+
Policies
```

The system should distinguish:

```text
Observed operational facts
Retrieved organizational knowledge
Model-generated hypotheses
```

These categories must not be silently mixed.

Evidence should remain traceable.

---

# 10. Phase 6: LangGraph Investigation System

## Objective

Implement the executable agent workflow.

The repository already reserves:

```text
agents/
graph/
```

The system should use LangGraph for stateful orchestration.

The intended graph should resemble:

```text
Incident
   ↓
Supervisor
   ↓
Investigation
   ↓
Evidence Collection
   ↓
Diagnosis
   ↓
Policy Check
   ↓
Approval
   ↓
Remediation
   ↓
Verification
   ↓
Resolve / Investigate Again / Escalate
```

---

# 11. Supervisor

Implement the supervisor as the graph-level coordinator.

The supervisor should:

- determine the current investigation stage
- select the appropriate agent/tool
- enforce graph transitions
- maintain structured state
- stop unsafe execution
- route back to investigation when verification fails
- route to escalation when the system cannot safely proceed

The supervisor should coordinate.

It should not become a dumping ground for business logic.

---

# 12. Investigation Agent

The investigation agent should collect evidence through MCP tools.

For ITOPS-001, it should be able to discover evidence such as:

```text
checkout error rate increased
        ↓
database connection behavior degraded
        ↓
deployment occurred
        ↓
current version is 2.4.1
        ↓
previous version is 2.4.0
        ↓
2.4.1 changed database connection pool configuration
        ↓
failures correlate with the deployment
```

The agent must derive this from available evidence rather than receiving the expected root cause.

---

# 13. Diagnosis Agent

The diagnosis layer should produce structured hypotheses.

A diagnosis should contain concepts such as:

```text
root cause hypothesis
confidence
supporting evidence
contradicting evidence
affected service
affected dependency
recommended remediation
```

The diagnosis should remain explicitly separate from observed facts.

A model hypothesis must never be treated as authorization.

---

# 14. Phase 7: Policy and Risk Engine

## Objective

Create deterministic controls around consequential operations.

The repository already contains:

```text
policy/
policy/rules
```

The policy system should evaluate:

```text
What action is proposed?
Why is it proposed?
Which service is affected?
What is the risk?
Does the action require approval?
Is the target version allowed?
Is the environment eligible?
```

Example:

```text
Rollback checkout-service
        ↓
Policy evaluation
        ↓
Approval required
        ↓
Human approval
        ↓
Action allowed
```

Policy must be deterministic and testable.

The LLM should not decide whether it is authorized to perform an action.

---

# 15. Risk Classification

Introduce explicit remediation risk levels.

The exact taxonomy should be defined during implementation, but it should distinguish at least:

```text
read-only investigation
low-risk operational action
consequential remediation
high-risk or restricted action
```

Risk evaluation should be deterministic.

Risk should influence whether human approval is required.

---

# 16. Phase 8: Human Approval and HITL

## Objective

Implement the approval boundary.

For ITOPS-001:

```text
Diagnosis
    ↓
Rollback proposed
    ↓
Policy says approval required
    ↓
Human approval requested
    ↓
Approval granted
    ↓
Rollback executed
```

The approval system must capture:

```text
incident
proposed action
target
reason
risk
request timestamp
approver
approval decision
decision timestamp
```

No approval means no consequential action.

Approval must not be inferred from an LLM response.

---

# 17. Phase 9: Remediation

Implement controlled remediation operations.

The first canonical remediation is:

```text
Rollback checkout-service 2.4.1 → 2.4.0
```

The remediation layer should:

- validate the proposed action
- verify policy authorization
- verify approval
- execute through Deployment MCP
- record an audit event
- return structured action results

The agent should not directly execute arbitrary shell commands.

---

# 18. Phase 10: Verification

After remediation, OpsPilot must verify the actual environment.

Verification should inspect operational evidence such as:

```text
service health
error rate
latency
database behavior
request success rate
deployment version
```

For ITOPS-001 the expected outcome is:

```text
service version = 2.4.0
service health = healthy
errors return to normal
```

Verification must use actual observed state.

The agent must not declare success simply because a deployment command returned successfully.

---

# 19. Remediation Failure Loop

If verification fails:

```text
Remediation
    ↓
Verification
    ↓
FAILED
    ↓
Investigation Again
```

The system should investigate the new evidence rather than blindly retrying.

If the system cannot safely determine a next action:

```text
Escalate
```

---

# 20. Auditability

Every consequential operation must generate an audit record.

At minimum capture:

```text
incident
actor
agent / component
action
target
reason
policy decision
approval
timestamp
result
verification result
```

Audit records should be immutable from the agent's perspective.

The system must support later reconstruction of:

```text
What happened?
Why did OpsPilot act?
What evidence did it use?
Which policy allowed it?
Who approved it?
What changed?
Did verification succeed?
```

---

# 21. Phase 11: MLflow

Use MLflow for AI-specific observability.

This layer should cover:

```text
agent traces
LLM calls
tool calls
latency
token usage where available
evaluation results
experiment runs
```

MLflow should complement infrastructure observability.

It should not replace:

```text
Prometheus
logs
OpenTelemetry
```

---

# 22. Phase 12: Evaluation Framework

Build deterministic and LLM-assisted evaluation.

The repository already contains:

```text
evaluation/
```

The evaluation framework should measure:

### Investigation quality

Did OpsPilot collect the relevant evidence?

### Diagnosis quality

Did the diagnosis match the operational evidence?

### Policy correctness

Was the proposed action permitted?

### Approval correctness

Was approval requested when required?

### Action correctness

Was the correct remediation executed?

### Verification correctness

Did OpsPilot verify the actual environment?

### Safety

Did the agent avoid unauthorized consequential actions?

### Efficiency

How many unnecessary tool calls or investigation loops occurred?

---

# 23. Evaluation Scenarios

Expand beyond ITOPS-001.

The initial scenario catalogue contains:

```text
bad deployment
DB saturation
certificate expiration
queue backlog
payment dependency failure
memory leak
network failure
configuration error
high latency
Redis failure
```

Each scenario should eventually have:

```text
scenario definition
initial state
fault
observable evidence
expected diagnosis
policy expectations
expected remediation
approval requirements
expected final state
```

Evaluation must not leak expected answers into operational agent context.

---

# 24. Phase 13: Dashboard

Build the OpsPilot human-facing dashboard.

The dashboard should expose:

```text
Active incidents
Investigation state
Current diagnosis
Evidence
Policy decision
Approval requests
Remediation status
Verification result
Audit history
```

The dashboard is not the reasoning engine.

It is the human visibility and control surface.

---

# 25. Phase 14: API Layer

Expand the FastAPI application to expose OpsPilot operations.

Potential API boundaries include:

```text
/scenarios
/incidents
/investigations
/diagnoses
/policies
/approvals
/remediations
/verifications
/audit
```

API schemas should remain strict and versionable.

The API must not bypass policy or approval boundaries.

---

# 26. Phase 15: PostgreSQL Operational State

Expand PostgreSQL beyond the current foundation.

Authoritative operational state should eventually include entities such as:

```text
services
service_versions
deployments
incidents
incident_events
investigations
diagnoses
policy_decisions
approval_requests
remediation_actions
verification_runs
audit_events
```

Database migrations must be explicit and version controlled.

---

# 27. Phase 16: OpenTelemetry

Expand OpenTelemetry coverage across the simulated environment.

Capture:

```text
service requests
dependency calls
database operations
errors
latency
trace context
```

The goal is to allow OpsPilot to correlate:

```text
incident
→ request
→ dependency
→ database
→ deployment
```

rather than relying only on isolated metrics.

---

# 28. Phase 17: Additional AcmeCloud Services

After checkout-service is stable, progressively implement:

```text
auth-service
inventory-service
payment-service
notification-service
api-gateway
frontend
redis
```

Each service should have:

- health endpoint
- operational metrics
- structured logs
- version information
- deployment history
- scenario-specific failure modes

The environment should remain deterministic enough for evaluation.

---

# 29. Phase 18: Kubernetes and GCP

The project eventually targets:

```text
Kubernetes
GCP
```

The existing infrastructure directories are:

```text
infrastructure/
├── compose/
├── docker/
├── gcp/
└── kubernetes/
```

Docker Compose remains the local development environment.

Kubernetes and GCP should be added only after the local operational loop is reliable.

The deployment abstraction should allow the agent layer to remain independent from the underlying deployment platform.

---

# 30. Phase 19: Production-Grade Safety

Before treating OpsPilot as a serious autonomous operations platform, establish:

- authentication
- authorization
- least privilege
- secrets management
- action allowlists
- approval enforcement
- audit integrity
- rate limits
- tool timeouts
- retry limits
- blast-radius controls
- rollback safeguards
- environment separation
- failure containment

No autonomous action should be able to bypass these controls.

---

# 31. Phase 20: Testing Strategy

Maintain multiple test layers.

## Unit tests

Validate:

```text
models
state transitions
policy rules
tool contracts
risk evaluation
agent routing
```

## Integration tests

Validate:

```text
MCP ↔ Prometheus
MCP ↔ logs
MCP ↔ deployment system
MCP ↔ incident system
PostgreSQL
RAG
LangGraph
```

## End-to-end tests

Validate the complete loop:

```text
Scenario
→ Incident
→ Observe
→ Investigate
→ Diagnose
→ Policy
→ Approval
→ Remediate
→ Verify
→ Resolve
```

## Safety tests

Explicitly verify that:

```text
No approval
    ≠
execute action
```

and:

```text
Policy denial
    ≠
execute action
```

and:

```text
Verification failure
    ≠
declare success
```

---

# 32. Final Target Architecture

The intended architecture is:

```text
                         ┌─────────────────────┐
                         │     Dashboard       │
                         └──────────┬──────────┘
                                    │
                                    ▼
                         ┌─────────────────────┐
                         │      FastAPI        │
                         └──────────┬──────────┘
                                    │
                                    ▼
                         ┌─────────────────────┐
                         │    LangGraph        │
                         │    Supervisor       │
                         └──────────┬──────────┘
                                    │
                ┌───────────────────┼───────────────────┐
                │                   │                   │
                ▼                   ▼                   ▼
        Investigation          Diagnosis            Policy
                │                   │                   │
                └──────────────┬────┴──────────────────┘
                               │
                               ▼
                         Human Approval
                               │
                               ▼
                         Remediation
                               │
                               ▼
                          Verification
                               │
                ┌──────────────┴──────────────┐
                │                             │
              Resolve                     Investigate
                                            Again
                │
                ▼
            Escalation
```

Operational access:

```text
                    OpsPilot
                       │
                       ▼
                      MCP
                       │
       ┌───────────────┼────────────────┐
       │               │                │
       ▼               ▼                ▼
    Metrics           Logs          Deployment
       │               │                │
       └───────────────┼────────────────┘
                       │
                       ▼
                    Incident
```

Knowledge:

```text
Architecture
Policies
Runbooks
Postmortems
Templates
      ↓
RAG ingestion
      ↓
Vector store
      ↓
Investigation context
```

Operational state:

```text
PostgreSQL
```

Infrastructure observability:

```text
OpenTelemetry
Prometheus
Logs
Grafana
```

AI observability:

```text
MLflow
```

---

# 33. Implementation Order

The recommended implementation order is:

```text
PHASE 4
MCP operational tools
        ↓
PHASE 5
Knowledge + RAG
        ↓
PHASE 6
LangGraph + Supervisor + Investigation
        ↓
PHASE 7
Diagnosis + Policy + Risk
        ↓
PHASE 8
Human Approval / HITL
        ↓
PHASE 9
Controlled Remediation
        ↓
PHASE 10
Verification + Resolve / Retry / Escalate
        ↓
PHASE 11
MLflow tracing
        ↓
PHASE 12
Evaluation framework
        ↓
PHASE 13
Dashboard
        ↓
PHASE 14
Expanded API
        ↓
PHASE 15
Operational PostgreSQL expansion
        ↓
PHASE 16
OpenTelemetry expansion
        ↓
PHASE 17
Additional AcmeCloud services
        ↓
PHASE 18
Kubernetes + GCP
        ↓
PHASE 19
Production safety hardening
        ↓
PHASE 20
Full test/evaluation maturity
```

---

# 34. Immediate Next Milestone

Do not start with LangGraph yet.

The immediate next implementation target is:

## Phase 4: MCP Operational Tools

Start with:

```text
1. MCP common contracts
2. Metrics MCP
3. Logs MCP
4. Deployment MCP
5. Incident MCP
6. Unit tests
7. Real integration tests
8. MCP documentation
```

The first useful agent capability should therefore be:

```text
Incident
   ↓
OpsPilot
   ↓
Metrics MCP
   ↓
Logs MCP
   ↓
Deployment MCP
   ↓
Incident MCP
```

Only after these operational interfaces are stable should the agent graph be allowed to depend on them.

---

# 35. Definition of Done for the Entire Project

OpsPilot is complete only when the system can demonstrate the full controlled loop against a real simulated incident:

```text
1. Fault is introduced
2. Failure emerges
3. Incident exists
4. OpsPilot observes evidence
5. OpsPilot investigates
6. OpsPilot retrieves organizational knowledge
7. OpsPilot produces an evidence-backed diagnosis
8. Policy evaluates the proposed action
9. Approval is requested when required
10. Human approval is captured
11. Approved remediation executes
12. Action is audited
13. Environment is verified
14. Incident resolves if healthy
15. Investigation resumes if verification fails
16. Incident escalates when safe remediation is unavailable
```

For ITOPS-001 specifically:

```text
2.4.0
  ↓
deploy 2.4.1
  ↓
traffic increases
  ↓
checkout failures
  ↓
incident
  ↓
OpsPilot investigates
  ↓
evidence points to 2.4.1 deployment
  ↓
diagnosis: bad deployment
  ↓
policy: rollback requires approval
  ↓
human approval
  ↓
rollback to 2.4.0
  ↓
verification
  ↓
healthy
  ↓
resolved
```

The system must reach that outcome through evidence, policy, authorization, action, and verification rather than hardcoded scenario answers.

---

# 36. Current Status

```text
Phase 0  ████████████████████ COMPLETE
Phase 1  ████████████████████ COMPLETE
Phase 2  ████████████████████ COMPLETE
Phase 3  ████████████████████ COMPLETE

Phase 4  ░░░░░░░░░░░░░░░░░░░░ NEXT
Phase 5  ░░░░░░░░░░░░░░░░░░░░ PLANNED
Phase 6  ░░░░░░░░░░░░░░░░░░░░ PLANNED
Phase 7  ░░░░░░░░░░░░░░░░░░░░ PLANNED
Phase 8  ░░░░░░░░░░░░░░░░░░░░ PLANNED
Phase 9  ░░░░░░░░░░░░░░░░░░░░ PLANNED
Phase 10 ░░░░░░░░░░░░░░░░░░░░ PLANNED
Phase 11 ░░░░░░░░░░░░░░░░░░░░ PLANNED
Phase 12 ░░░░░░░░░░░░░░░░░░░░ PLANNED
Phase 13 ░░░░░░░░░░░░░░░░░░░░ PLANNED
Phase 14 ░░░░░░░░░░░░░░░░░░░░ PLANNED
Phase 15 ░░░░░░░░░░░░░░░░░░░░ PLANNED
Phase 16 ░░░░░░░░░░░░░░░░░░░░ PLANNED
Phase 17 ░░░░░░░░░░░░░░░░░░░░ PLANNED
Phase 18 ░░░░░░░░░░░░░░░░░░░░ PLANNED
Phase 19 ░░░░░░░░░░░░░░░░░░░░ PLANNED
Phase 20 ░░░░░░░░░░░░░░░░░░░░ PLANNED
```

**Immediate next step: implement Phase 4 MCP operational tools.**
