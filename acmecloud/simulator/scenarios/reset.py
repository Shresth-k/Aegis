"""Reset the simulated environment for a Scenario Engine execution."""

from __future__ import annotations

from typing import Protocol

from .execution_state import ScenarioExecutionState
from .models import ScenarioDefinition


class ScenarioResetError(RuntimeError):
    """Raised when a scenario environment cannot be reset."""


class DeploymentResetter(Protocol):
    """Minimal deployment boundary required by the reset operation."""

    def deploy(self, service: str, version: str):
        """Deploy one service version."""


class ScenarioResetter:
    """Restore the initial deployment and preserve incident history."""

    def __init__(self, deployment_controller: DeploymentResetter) -> None:
        """Create a resetter backed by a deployment controller."""
        self._deployment_controller = deployment_controller

    def reset(
        self,
        scenario: ScenarioDefinition,
        execution_state: ScenarioExecutionState,
    ) -> ScenarioExecutionState:
        """Restore the initial version and preserve the historical incident."""
        if execution_state.scenario_id != scenario.scenario_id:
            raise ScenarioResetError("execution state does not belong to the scenario")

        historical_incident_id = execution_state.incident_id

        try:
            self._deployment_controller.deploy(
                scenario.service,
                scenario.initial_version,
            )
        except Exception as exc:
            raise ScenarioResetError(
                f"Unable to reset {scenario.service} to {scenario.initial_version}"
            ) from exc

        reset_state = execution_state.mark_reset()

        # The state machine clears the active incident association. The
        # orchestrator restores it as historical correlation metadata.
        reset_state.incident_id = historical_incident_id
        return reset_state
