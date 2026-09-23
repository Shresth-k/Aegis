# OpsPilot Development Status: DONE

> Last updated: 2026-09-22
>
> Scope: Phases 0 through 3
>
> Status: **COMPLETE**

## 1. Purpose

This document records the work completed in the OpsPilot repository through the end of Phase 3.

It is the historical implementation record for the project. It describes what exists, what contracts were established, what was tested, and what was deliberately left for later phases.

The project is now ready to move from scenario-execution infrastructure into the operational MCP and agent layers.

---

# 2. Project Definition

OpsPilot is an **Agentic IT Operations and Incident Resolution Platform**.

The system is intentionally designed around an operational incident-resolution loop rather than a generic chatbot or generic multi-agent framework.

The core loop is:

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

The project contains two conceptual worlds:

### World A: AcmeCloud

A simulated enterprise environment containing services and infrastructure that can experience controlled operational failures.

### World B: OpsPilot

The AI operations platform that will eventually observe AcmeCloud, investigate incidents, reason over evidence, check policy, request approval where required, execute remediation, verify the result, and resolve or escalate the incident.

---

# 3. AcmeCloud Simulation

The simulated enterprise contains:

```text
frontend
api-gateway
auth-service
checkout-service
payment-service
inventory-service
notification-service
postgres
redis
```

The checkout service is the first fully exercised service.

Its important dependencies are:

```text
checkout-service
├── inventory-service
├── payment-service
├── postgres
└── redis
```

Services expose basic APIs and health endpoints.

The simulation also supports versioned service deployments and controlled faults.

---

# 4. Canonical Fault Model

The canonical controlled deployment fault is:

```text
Version 2.4.0
DB_CONNECTION_POOL=50

Version 2.4.1
DB_CONNECTION_POOL=5
```

Under sufficiently high traffic, the faulty version is intended to cause database connection pool exhaustion, producing request failures and HTTP 500 responses.

The important architectural requirement is that OpsPilot must eventually infer the root cause from operational evidence.

The root cause must not simply be supplied to the agent.

Relevant evidence includes:

- metrics
- logs
- deployment history
- service dependencies
- incident history
- runbooks
- postmortems
- policies

---

# 5. Canonical Scenario: ITOPS-001

The canonical Phase 3 scenario is:

```text
Scenario: ITOPS-001
Service: checkout-service
Initial version: 2.4.0
Fault: bad deployment
Fault version: 2.4.1
Traffic: 100 requests/second
Expected root cause: bad_deployment
Expected action: rollback to 2.4.0
Approval required: true
Expected final version: 2.4.0
Expected final health: healthy
```

The scenario lifecycle is:

```text
Scenario Selected
        ↓
Initial State Applied
        ↓
Fault Introduced
        ↓
Traffic Generated
        ↓
Failure Emerges
        ↓
Incident Created
        ↓
OpsPilot Investigates
```

Reset then restores the initial deployment state.

---

# 6. Phase 0: Foundation

## Completed

The repository foundation was established with a structure separating:

```text
agents/
apps/
database/
docs/
evaluation/
graph/
infrastructure/
knowledge/
mcp/
mlflow/
observability/
policy/
rag/
scripts/
simulator/
tests/
```

The project uses:

- Python 3.12
- `uv` for environment and dependency management
- FastAPI
- Pydantic
- SQLAlchemy
- PostgreSQL
- Docker Compose
- pytest
- Ruff

The project is configured for Python 3.12 and Ruff with:

```text
line length: 88
target: py312
rules: E F I UP B
```

The test configuration uses:

```text
testpaths = tests
```

## Local infrastructure established

Docker Compose provides:

```text
postgres
checkout-service
prometheus
grafana
```

PostgreSQL is available as the operational database.

Prometheus scrapes the checkout service.

Grafana is available as the human-facing metrics visualization layer.

The checkout service exposes a health endpoint.

---

# 7. Phase 1: Versioning and Controlled Faults

## Completed

Versioned checkout deployments were established.

### Version 2.4.0

```text
SERVICE_VERSION=2.4.0
DB_CONNECTION_POOL=50
DB_POOL_TIMEOUT=5
DB_OPERATION_DELAY_MS=0
```

### Version 2.4.1

```text
SERVICE_VERSION=2.4.1
DB_CONNECTION_POOL=5
DB_POOL_TIMEOUT=0.5
DB_OPERATION_DELAY_MS=2000
```

Version 2.4.1 is deliberately faulty and exists specifically for controlled scenario execution.

The deployment model supports:

- current version
- previous version
- deployment timestamp
- deployment status
- environment
- deployment actor
- deployment history

The deployment mechanism was implemented so that service versions can be recreated through Docker Compose.

---

# 8. Phase 2: Observability Foundation

## Completed

The first operational observability layer was established around the checkout service.

Prometheus is configured as the metrics backend.

The checkout service exposes metrics including:

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

An important implementation detail was established:

> Checkout request metrics are incremented by the checkout operation itself, not by health checks or unrelated endpoints.

This keeps the operational measurements meaningful.

Grafana is the human-facing observability layer.

The architectural direction is:

```text
AcmeCloud
    ↓
OpenTelemetry / Prometheus / Logs
    ↓
Operational evidence
    ↓
OpsPilot MCP tools
```

MLflow is reserved for AI tracing and evaluation rather than replacing infrastructure observability.

---

# 9. Phase 3: Scenario Engine

Phase 3 established the controlled scenario execution infrastructure.

This is the first complete executable vertical slice of the AcmeCloud simulation.

---

## 9.1 Scenario Models

Implemented strict Pydantic models for scenario definitions.

The models include:

### FaultDefinition

```text
type
version
```

### TrafficDefinition

```text
requests_per_second
```

### ExpectedAction

```text
type
target_version
```

### ExpectedFinalState

```text
service_version
service_health
```

### ScenarioDefinition

```text
scenario_id
service
initial_version
fault
traffic
expected_root_cause
expected_action
approval_required
expected_final_state
```

Models use strict configuration such as:

```text
extra = forbid
str_strip_whitespace = true
```

Invalid scenario definitions are rejected early.

The model validation also prevents a `bad_deployment` fault from using the same version as the initial deployment.

---

# 10. Scenario YAML Loader

Scenario definitions are stored outside Python code.

The canonical scenario is:

```text
evaluation/scenarios/ITOPS-001.yaml
```

The loader:

1. reads YAML
2. parses the YAML safely
3. validates it against the Pydantic scenario model
4. converts failures into a scenario-specific loading error

This establishes a clean separation between:

```text
Scenario data
```

and:

```text
Scenario execution code
```

---

# 11. Scenario Registry

The scenario registry:

- discovers YAML scenario definitions
- validates every discovered scenario
- detects duplicate scenario IDs
- provides lookup by scenario ID
- returns deterministic scenario ordering

The registry does not execute scenarios.

This separation is intentional.

---

# 12. Scenario Execution State Machine

A dedicated execution state model was implemented.

The supported phases are:

```text
SCENARIO_SELECTED
INITIAL_STATE_APPLIED
FAULT_INTRODUCED
TRAFFIC_GENERATED
FAILURE_EMERGED
INCIDENT_CREATED
OPSPILOT_INVESTIGATING
```

Execution status includes:

```text
RUNNING
COMPLETED
FAILED
RESET
```

The state machine validates transitions.

Invalid transitions fail explicitly.

State facts are also validated against the current phase.

For example, later phases cannot be entered without the facts required by earlier phases.

The state transition operation validates the candidate state before mutating the current state.

This prevents partially applied invalid state.

---

# 13. Deployment Controller

A Docker Compose deployment controller was implemented.

Its responsibility is narrow:

```text
service + version
        ↓
versioned deployment definition
        ↓
Docker Compose service recreation
```

The controller:

- resolves version-specific deployment files
- validates deployment paths
- rejects missing versions
- validates the Compose file
- invokes Docker Compose
- preserves the existing project environment
- sets the requested `CHECKOUT_VERSION`
- reports deployment failures through explicit exceptions

### Important design correction

The deployment version file is a service-level environment file.

It must **not** be supplied as the Compose project's global `--env-file`.

Doing that caused the project-level PostgreSQL variables to disappear during Compose interpolation.

The corrected design is:

```text
Project environment
    ↓
Docker Compose interpolation
    ↓
DATABASE_URL with PostgreSQL credentials

Version deployment environment
    ↓
checkout-service env_file
    ↓
SERVICE_VERSION / DB settings
```

This preserves the separation between project-level infrastructure configuration and service-version configuration.

The real deployment controller was verified against Docker.

---

# 14. Traffic Generator

A deterministic traffic generator was implemented.

Public contract:

```text
TrafficGenerator.generate(...)
```

It supports:

- base URL
- requests per second
- duration
- request timeout

Traffic results include:

```text
requested
completed
successful
failed
status_codes
errors
success_rate
```

Transport errors are represented deterministically.

The generated checkout payload is deterministic:

```json
{
  "customer_id": "scenario-customer-N",
  "total_amount": "149.99",
  "currency": "usd"
}
```

Real HTTP traffic converts the scenario customer identifier into a deterministic UUID5 value.

The generator uses bounded concurrency and deterministic ordering.

---

# 15. Incident Creation

Operational incident creation was separated from evaluation metadata.

The operational incident contains:

```text
incident_id
service
environment
severity
status
summary
created_at
```

The incident creation request intentionally does not contain:

```text
expected_root_cause
expected_action
```

Those fields belong to scenario evaluation, not operational incident state.

This prevents the simulated incident from leaking the expected answer to the future OpsPilot agent.

Incident IDs are deterministic within the in-memory implementation:

```text
INC-001
INC-002
...
```

Incident timestamps are generated using UTC.

An in-memory incident store was implemented for scenario tests.

---

# 16. Scenario Reset

A reset mechanism was implemented.

Reset behavior:

1. verify the execution state belongs to the scenario
2. capture the historical incident ID
3. deploy the scenario's initial version
4. mark execution state as reset
5. preserve the historical incident correlation

Reset does not delete the incident.

This allows historical incident correlation to remain available after the simulated environment has been restored.

Deployment failures during reset are surfaced as scenario reset errors.

---

# 17. Scenario Runner

The ScenarioRunner orchestrates the Phase 3 lifecycle.

Execution sequence:

```text
Create execution state
        ↓
Deploy initial version
        ↓
Mark initial state applied
        ↓
Deploy fault version
        ↓
Mark fault introduced
        ↓
Generate traffic
        ↓
Mark traffic generated
        ↓
Verify failure occurred
        ↓
Mark failure emerged
        ↓
Create operational incident
        ↓
Mark incident created
        ↓
Mark OpsPilot investigating
```

The runner intentionally stops at:

```text
OPSPILOT_INVESTIGATING
```

Actual AI investigation and remediation are later-phase responsibilities.

The runner also exposes reset behavior through the scenario resetter.

---

# 18. End-to-End Validation

The Phase 3 integration test executes the canonical ITOPS-001 scenario against the real Docker environment.

The integration path verifies:

- deployment of 2.4.0
- health verification
- deployment of faulty 2.4.1
- real traffic generation
- request failures
- failure emergence
- incident creation
- transition to `OPSPILOT_INVESTIGATING`
- incident correlation
- reset
- restoration to 2.4.0
- final service health

The full test suite currently reports:

```text
86 passed
1 skipped
0 failures
0 warnings
```

Ruff also reports:

```text
All checks passed!
```

Therefore Phase 3 is considered complete.

---

# 19. Current Completion Boundary

At the end of Phase 3, OpsPilot can:

```text
Define scenario
    ↓
Load scenario
    ↓
Register scenario
    ↓
Create execution state
    ↓
Deploy service version
    ↓
Introduce controlled fault
    ↓
Generate traffic
    ↓
Detect simulated failure
    ↓
Create operational incident
    ↓
Enter OpsPilot investigation state
    ↓
Reset environment
```

What it cannot yet do is the actual intelligent operational loop:

```text
Observe
Investigate
Reason
Retrieve knowledge
Check policy
Request human approval
Execute remediation
Verify
Resolve
Escalate
```

Those responsibilities are intentionally deferred to later phases.

---

# 20. Phase 3 Exit Criteria

Phase 3 exit criteria are satisfied:

- [x] Scenario model exists
- [x] Scenario YAML exists
- [x] Scenario loader exists
- [x] Scenario registry exists
- [x] Execution state machine exists
- [x] Deployment controller exists
- [x] Traffic generator exists
- [x] Incident creation exists
- [x] Scenario reset exists
- [x] Scenario runner exists
- [x] Canonical ITOPS-001 scenario exists
- [x] Real Docker integration works
- [x] Faulted deployment produces failures
- [x] Incident is created
- [x] Execution reaches OpsPilot investigation state
- [x] Reset restores the initial deployment
- [x] Full test suite passes
- [x] Ruff passes
- [x] No current test warnings

## Final status

**PHASE 0: COMPLETE**

**PHASE 1: COMPLETE**

**PHASE 2: COMPLETE**

**PHASE 3: COMPLETE**

**Next implementation target: Phase 4, MCP operational tools.**
