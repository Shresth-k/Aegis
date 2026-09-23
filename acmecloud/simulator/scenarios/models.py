"""Pydantic models for Scenario Engine definitions.

Phase 3.1 defines the typed contract for a scenario definition. It mirrors
the Scenario Engine schema in the OpsPilot master specification.

This module intentionally contains validation only. YAML loading, scenario
execution, deployment control, traffic generation, incident creation, and
reset belong to later Phase 3 components.
"""

from typing import Self

from pydantic import BaseModel, ConfigDict, Field, model_validator


class ScenarioModel(BaseModel):
    """Base model with strict field validation for scenario definitions."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class FaultDefinition(ScenarioModel):
    """Describe the controlled fault introduced by a scenario."""

    type: str = Field(min_length=1)
    version: str | None = Field(default=None, min_length=1)


class TrafficDefinition(ScenarioModel):
    """Describe the traffic used to exercise the scenario."""

    requests_per_second: int = Field(gt=0)


class ExpectedAction(ScenarioModel):
    """Describe the remediation expected by the scenario evaluator."""

    type: str = Field(min_length=1)
    target_version: str | None = Field(default=None, min_length=1)


class ExpectedFinalState(ScenarioModel):
    """Describe the service state expected after remediation."""

    service_version: str = Field(min_length=1)
    service_health: str = Field(min_length=1)


class ScenarioDefinition(ScenarioModel):
    """Typed contract for a deterministic Scenario Engine scenario."""

    scenario_id: str = Field(min_length=1)
    service: str = Field(min_length=1)
    initial_version: str = Field(min_length=1)

    fault: FaultDefinition
    traffic: TrafficDefinition

    expected_root_cause: str = Field(min_length=1)
    expected_action: ExpectedAction
    approval_required: bool
    expected_final_state: ExpectedFinalState

    @model_validator(mode="after")
    def validate_versions(self) -> Self:
        """Prevent a bad-deployment fault from using the initial version."""
        if (
            self.fault.version is not None
            and self.fault.version == self.initial_version
            and self.fault.type == "bad_deployment"
        ):
            raise ValueError(
                "bad_deployment fault version must differ from initial_version"
            )

        return self
