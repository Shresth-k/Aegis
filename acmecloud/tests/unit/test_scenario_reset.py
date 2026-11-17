"""Unit tests for Phase 3.8 scenario reset."""

from pathlib import Path

import pytest

from simulator.scenarios.execution_state import (
    ExecutionPhase,
    ExecutionStatus,
    ScenarioExecutionState,
)
from simulator.scenarios.loader import load_scenario
from simulator.scenarios.reset import ScenarioResetError, ScenarioResetter


class FakeDeploymentController:
    """Record deployment operations for reset tests."""

    def __init__(self) -> None:
        self.calls: list[tuple[str, str]] = []
        self.should_fail = False

    def deploy(self, service: str, version: str) -> None:
        """Record a deployment request or simulate a failure."""
        if self.should_fail:
            raise RuntimeError("deployment failed")

        self.calls.append((service, version))


def _scenario():
    """Load the canonical ITOPS-001 scenario."""
    return load_scenario(Path("evaluation/scenarios/ITOPS-001.yaml"))


def _execution_state() -> ScenarioExecutionState:
    """Build an execution state belonging to ITOPS-001."""
    return ScenarioExecutionState(
        scenario_id="ITOPS-001",
        initial_service_version="2.4.0",
        active_service_version="2.4.1",
        fault_introduced=True,
        traffic_generated=True,
        phase=ExecutionPhase.INCIDENT_CREATED,
        status=ExecutionStatus.RUNNING,
        incident_id="INC-001",
    )


def test_reset_deploys_initial_version() -> None:
    """Reset restores the scenario's declared initial version."""
    controller = FakeDeploymentController()
    resetter = ScenarioResetter(controller)

    state = resetter.reset(_scenario(), _execution_state())

    assert controller.calls == [("checkout-service", "2.4.0")]
    assert state.status is ExecutionStatus.RESET


def test_reset_marks_execution_state_reset() -> None:
    """Reset records the terminal reset status."""
    controller = FakeDeploymentController()
    resetter = ScenarioResetter(controller)

    state = resetter.reset(_scenario(), _execution_state())

    assert state.status is ExecutionStatus.RESET
    assert state.error is None
    assert state.updated_at >= state.created_at


def test_reset_rejects_mismatched_scenario_state() -> None:
    """A reset cannot mutate an execution belonging to another scenario."""
    controller = FakeDeploymentController()
    resetter = ScenarioResetter(controller)
    state = _execution_state()
    state.scenario_id = "ITOPS-999"

    with pytest.raises(
        ScenarioResetError,
        match="does not belong to the scenario",
    ):
        resetter.reset(_scenario(), state)

    assert controller.calls == []


def test_reset_does_not_delete_incident_reference() -> None:
    """Reset preserves the incident reference for operational history."""
    controller = FakeDeploymentController()
    resetter = ScenarioResetter(controller)

    state = resetter.reset(_scenario(), _execution_state())

    assert state.incident_id == "INC-001"


def test_reset_propagates_deployment_failure_as_domain_error() -> None:
    """Deployment failures are translated into ScenarioResetError."""
    controller = FakeDeploymentController()
    controller.should_fail = True
    resetter = ScenarioResetter(controller)

    with pytest.raises(
        ScenarioResetError,
        match="Unable to reset checkout-service to 2.4.0",
    ):
        resetter.reset(_scenario(), _execution_state())
