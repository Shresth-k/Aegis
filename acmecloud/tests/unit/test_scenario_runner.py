"""Unit tests for the Phase 3.9 ScenarioRunner lifecycle."""

from datetime import UTC, datetime

from simulator.scenarios.execution_state import ExecutionPhase
from simulator.scenarios.incident import Incident
from simulator.scenarios.models import (
    ExpectedAction,
    ExpectedFinalState,
    FaultDefinition,
    ScenarioDefinition,
    TrafficDefinition,
)
from simulator.scenarios.runner import ScenarioRunner
from simulator.scenarios.traffic import TrafficResult


class FakeDeploymentController:
    """Record deployments without touching Docker."""

    def __init__(self) -> None:
        self.deployments: list[tuple[str, str]] = []

    def deploy(self, service: str, version: str) -> None:
        self.deployments.append((service, version))


class FakeTrafficGenerator:
    """Return deterministic failed traffic without HTTP calls."""

    def __init__(self) -> None:
        self.configs = []

    def generate(self, config):
        self.configs.append(config)
        return TrafficResult(
            requested=100,
            completed=100,
            successful=0,
            failed=100,
            status_codes={500: 100},
            errors=(),
        )


class FakeIncidentCreator:
    """Create an operational incident without evaluation fields."""

    def create(self, request):
        return Incident(
            incident_id="INC-001",
            service=request.service,
            environment=request.environment,
            severity=request.severity,
            status=request.status,
            summary=request.summary,
            created_at=datetime.now(UTC),
        )


class FakeResetter:
    """Record reset requests without changing the environment."""

    def reset(self, scenario, state):
        return state


def make_scenario() -> ScenarioDefinition:
    """Build the canonical ITOPS-001 contract for runner testing."""
    return ScenarioDefinition(
        scenario_id="ITOPS-001",
        service="checkout-service",
        initial_version="2.4.0",
        fault=FaultDefinition(type="bad_deployment", version="2.4.1"),
        traffic=TrafficDefinition(requests_per_second=100),
        expected_root_cause="bad_deployment",
        expected_action=ExpectedAction(
            type="rollback",
            target_version="2.4.0",
        ),
        approval_required=True,
        expected_final_state=ExpectedFinalState(
            service_version="2.4.0",
            service_health="healthy",
        ),
    )


def test_runner_executes_environment_lifecycle_without_using_evaluation_data() -> None:
    """Runner reaches investigation using observed traffic failure only."""
    deployment = FakeDeploymentController()
    traffic = FakeTrafficGenerator()
    incident_creator = FakeIncidentCreator()
    resetter = FakeResetter()

    runner = ScenarioRunner(
        deployment_controller=deployment,
        traffic_generator=traffic,
        incident_creator=incident_creator,
        resetter=resetter,
        base_url="http://checkout-service:8000",
    )

    result = runner.execute(make_scenario())

    assert deployment.deployments == [
        ("checkout-service", "2.4.0"),
        ("checkout-service", "2.4.1"),
    ]
    assert traffic.configs[0].requests_per_second == 100
    assert result.state.phase == ExecutionPhase.OPSPILOT_INVESTIGATING
    assert result.incident.incident_id == "INC-001"
    assert "expected_root_cause" not in Incident.model_fields
    assert "expected_action" not in Incident.model_fields
