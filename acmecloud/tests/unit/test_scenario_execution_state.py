"""Unit tests for the Phase 3.4 Scenario Execution State."""

from uuid import UUID

import pytest
from pydantic import ValidationError

from simulator.scenarios.execution_state import (
    ExecutionPhase,
    ExecutionStateError,
    ExecutionStatus,
    ScenarioExecutionState,
)


def test_execution_state_starts_at_scenario_selected() -> None:
    """A new execution begins in the selected phase and is running."""
    state = ScenarioExecutionState(scenario_id="ITOPS-001")

    assert isinstance(state.execution_id, UUID)
    assert state.phase == ExecutionPhase.SCENARIO_SELECTED
    assert state.status == ExecutionStatus.RUNNING
    assert state.initial_service_version is None
    assert state.active_service_version is None
    assert state.fault_introduced is False
    assert state.traffic_generated is False
    assert state.incident_id is None
    assert state.error is None


def test_execution_state_advances_through_canonical_lifecycle() -> None:
    """Each lifecycle transition advances exactly one phase."""
    state = ScenarioExecutionState(scenario_id="ITOPS-001")

    state = state.transition_to(
        ExecutionPhase.INITIAL_STATE_APPLIED,
        initial_service_version="2.4.0",
        active_service_version="2.4.0",
    )
    state = state.transition_to(
        ExecutionPhase.FAULT_INTRODUCED,
        active_service_version="2.4.1",
    )
    state = state.transition_to(ExecutionPhase.TRAFFIC_GENERATED)
    state = state.transition_to(ExecutionPhase.FAILURE_EMERGED)
    state = state.transition_to(
        ExecutionPhase.INCIDENT_CREATED,
        incident_id="INC-001",
    )
    state = state.transition_to(ExecutionPhase.OPSPILOT_INVESTIGATING)

    assert state.phase == ExecutionPhase.OPSPILOT_INVESTIGATING
    assert state.initial_service_version == "2.4.0"
    assert state.active_service_version == "2.4.1"
    assert state.fault_introduced is True
    assert state.traffic_generated is True
    assert state.incident_id == "INC-001"


def test_execution_state_rejects_skipping_a_phase() -> None:
    """The state machine does not permit arbitrary phase jumps."""
    state = ScenarioExecutionState(scenario_id="ITOPS-001")

    with pytest.raises(ExecutionStateError, match="Invalid transition"):
        state.transition_to(ExecutionPhase.FAULT_INTRODUCED)


def test_execution_state_requires_initial_version_after_selection() -> None:
    """Later phases cannot exist without the initial service version."""
    with pytest.raises(ValidationError, match="initial_service_version"):
        ScenarioExecutionState(
            scenario_id="ITOPS-001",
            phase=ExecutionPhase.INITIAL_STATE_APPLIED,
        )


def test_execution_state_requires_fault_before_traffic() -> None:
    """Traffic cannot be recorded before the fault is introduced."""
    state = ScenarioExecutionState(
        scenario_id="ITOPS-001",
        phase=ExecutionPhase.FAULT_INTRODUCED,
        initial_service_version="2.4.0",
        fault_introduced=True,
    )

    with pytest.raises(ExecutionStateError, match="Invalid transition"):
        state.transition_to(ExecutionPhase.FAILURE_EMERGED)


def test_execution_state_requires_incident_id_for_investigation() -> None:
    """OpsPilot investigation requires a created incident reference."""
    state = ScenarioExecutionState(
        scenario_id="ITOPS-001",
        phase=ExecutionPhase.INCIDENT_CREATED,
        initial_service_version="2.4.0",
        active_service_version="2.4.1",
        fault_introduced=True,
        traffic_generated=True,
        incident_id="INC-001",
    )

    investigated = state.transition_to(
        ExecutionPhase.OPSPILOT_INVESTIGATING,
    )

    assert investigated.incident_id == "INC-001"


def test_execution_state_can_be_marked_completed() -> None:
    """Completion is only valid once OpsPilot is investigating."""
    state = ScenarioExecutionState(
        scenario_id="ITOPS-001",
        phase=ExecutionPhase.OPSPILOT_INVESTIGATING,
        initial_service_version="2.4.0",
        active_service_version="2.4.1",
        fault_introduced=True,
        traffic_generated=True,
        incident_id="INC-001",
    )

    completed = state.mark_completed()

    assert completed.status == ExecutionStatus.COMPLETED
    assert completed.phase == ExecutionPhase.OPSPILOT_INVESTIGATING


def test_execution_state_can_be_marked_failed() -> None:
    """A running execution can enter failed status with an explicit error."""
    state = ScenarioExecutionState(scenario_id="ITOPS-001")

    failed = state.mark_failed("Fault controller unavailable")

    assert failed.status == ExecutionStatus.FAILED
    assert failed.error == "Fault controller unavailable"


def test_execution_state_rejects_empty_failure_reason() -> None:
    """A failed execution must contain a meaningful error."""
    state = ScenarioExecutionState(scenario_id="ITOPS-001")

    with pytest.raises(ExecutionStateError, match="requires an error"):
        state.mark_failed("   ")


def test_execution_state_can_be_reset() -> None:
    """Reset clears execution facts and returns to the selected phase."""
    state = ScenarioExecutionState(
        scenario_id="ITOPS-001",
        phase=ExecutionPhase.INCIDENT_CREATED,
        initial_service_version="2.4.0",
        active_service_version="2.4.1",
        fault_introduced=True,
        traffic_generated=True,
        incident_id="INC-001",
    )

    reset = state.mark_reset()

    assert reset.status == ExecutionStatus.RESET
    assert reset.phase == ExecutionPhase.SCENARIO_SELECTED
    assert reset.initial_service_version is None
    assert reset.active_service_version is None
    assert reset.fault_introduced is False
    assert reset.traffic_generated is False
    assert reset.incident_id is None
    assert reset.error is None


def test_execution_state_rejects_mutating_unknown_fields() -> None:
    """Runtime state remains a strict typed contract."""
    with pytest.raises(ValidationError):
        ScenarioExecutionState(
            scenario_id="ITOPS-001",
            unexpected_field="should-not-exist",
        )


def test_execution_state_does_not_contain_evaluation_expectations() -> None:
    """Evaluation-only expectations are not part of operational state."""
    fields = ScenarioExecutionState.model_fields

    assert "expected_root_cause" not in fields
    assert "expected_action" not in fields
    assert "expected_final_state" not in fields
