"""Typed lifecycle state for deterministic Scenario Engine executions."""

from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum
from typing import Self
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field, model_validator


class ExecutionPhase(StrEnum):
    """Canonical lifecycle phases for one scenario execution."""

    SCENARIO_SELECTED = "scenario_selected"
    INITIAL_STATE_APPLIED = "initial_state_applied"
    FAULT_INTRODUCED = "fault_introduced"
    TRAFFIC_GENERATED = "traffic_generated"
    FAILURE_EMERGED = "failure_emerged"
    INCIDENT_CREATED = "incident_created"
    OPSPILOT_INVESTIGATING = "opspilot_investigating"


class ExecutionStatus(StrEnum):
    """Execution status values."""

    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    RESET = "reset"


class ExecutionStateError(ValueError):
    """Raised when an execution state transition is invalid."""


class ScenarioExecutionState(BaseModel):
    """Operational state for one deterministic scenario execution."""

    model_config = ConfigDict(
        extra="forbid",
        validate_assignment=True,
    )

    execution_id: UUID = Field(default_factory=uuid4)
    scenario_id: str = Field(min_length=1)
    phase: ExecutionPhase = ExecutionPhase.SCENARIO_SELECTED
    status: ExecutionStatus = ExecutionStatus.RUNNING
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    initial_service_version: str | None = None
    active_service_version: str | None = None
    fault_introduced: bool = False
    traffic_generated: bool = False
    incident_id: str | None = None
    error: str | None = None

    @model_validator(mode="after")
    def validate_state(self) -> Self:
        """Validate lifecycle invariants."""
        phase_index = list(ExecutionPhase).index(self.phase)

        if phase_index >= 1 and self.initial_service_version is None:
            raise ValueError(
                "initial_service_version is required after initial_state_applied"
            )

        if phase_index >= 2 and not self.fault_introduced:
            raise ValueError("fault_introduced is required after fault_introduced")

        if phase_index >= 3 and not self.traffic_generated:
            raise ValueError("traffic_generated is required after traffic_generated")

        if phase_index >= 5 and self.incident_id is None:
            raise ValueError("incident_id is required after incident_created")

        if (
            self.status
            in {
                ExecutionStatus.COMPLETED,
                ExecutionStatus.RESET,
            }
            and self.error is not None
        ):
            raise ValueError(f"{self.status.value} execution cannot contain an error")

        return self

    def transition_to(
        self,
        next_phase: ExecutionPhase,
        *,
        initial_service_version: str | None = None,
        active_service_version: str | None = None,
        fault_introduced: bool | None = None,
        traffic_generated: bool | None = None,
        incident_id: str | None = None,
    ) -> Self:
        """Advance one phase and apply any facts supplied for that phase."""
        phases = list(ExecutionPhase)
        current_index = phases.index(self.phase)
        next_index = phases.index(next_phase)

        if next_index != current_index + 1:
            raise ExecutionStateError(
                f"Invalid transition: {self.phase.value} -> {next_phase.value}"
            )

        if self.status is not ExecutionStatus.RUNNING:
            raise ExecutionStateError(
                "Invalid transition: only a running execution can change phase"
            )

        updates: dict[str, object] = {
            "phase": next_phase,
            "updated_at": datetime.now(UTC),
        }

        if initial_service_version is not None:
            updates["initial_service_version"] = initial_service_version
        if active_service_version is not None:
            updates["active_service_version"] = active_service_version
        if fault_introduced is not None:
            updates["fault_introduced"] = fault_introduced
        if traffic_generated is not None:
            updates["traffic_generated"] = traffic_generated
        if incident_id is not None:
            updates["incident_id"] = incident_id

        # Entering these phases establishes the corresponding operational fact.
        # This lets callers provide only the facts that are not implied by the
        # lifecycle transition itself.
        if next_phase is ExecutionPhase.FAULT_INTRODUCED:
            updates["fault_introduced"] = True
        elif next_phase is ExecutionPhase.TRAFFIC_GENERATED:
            updates["traffic_generated"] = True

        candidate = self.__class__.model_validate(
            self.model_dump(mode="python") | updates
        )

        for field, value in candidate.__dict__.items():
            object.__setattr__(self, field, value)

        return self

    def mark_completed(self) -> Self:
        """Mark a running execution as completed."""
        if self.status is not ExecutionStatus.RUNNING:
            raise ExecutionStateError(
                "Invalid transition: only a running execution can be completed"
            )

        self.status = ExecutionStatus.COMPLETED
        self.updated_at = datetime.now(UTC)
        return self

    def mark_failed(self, error: str) -> Self:
        """Mark a running execution as failed."""
        if not error.strip():
            raise ExecutionStateError("Failed execution requires an error")

        if self.status is not ExecutionStatus.RUNNING:
            raise ExecutionStateError(
                "Invalid transition: only a running execution can fail"
            )

        self.status = ExecutionStatus.FAILED
        self.error = error
        self.updated_at = datetime.now(UTC)
        return self

    def mark_reset(self) -> Self:
        """Reset active execution state and clear its active incident ID."""
        if self.status is ExecutionStatus.RESET:
            raise ExecutionStateError("Execution is already reset")

        self.phase = ExecutionPhase.SCENARIO_SELECTED
        self.status = ExecutionStatus.RESET
        self.initial_service_version = None
        self.active_service_version = None
        self.fault_introduced = False
        self.traffic_generated = False
        self.incident_id = None
        self.error = None
        self.updated_at = datetime.now(UTC)
        return self
