"""Orchestrate the executable lifecycle of one Scenario Engine run.

Phase 3.9 is intentionally limited to Scenario Engine behavior. It creates
the simulated failure and incident, then resets the environment. It does not
diagnose the incident, choose remediation, apply policy, or invoke OpsPilot.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from .execution_state import ExecutionPhase, ScenarioExecutionState
from .incident import Incident, IncidentCreateRequest, IncidentCreator
from .models import ScenarioDefinition
from .reset import ScenarioResetter
from .traffic import TrafficConfig, TrafficGenerator, TrafficResult


class ScenarioExecutionError(RuntimeError):
    """Raised when a scenario execution cannot complete its lifecycle."""


class DeploymentController(Protocol):
    """Minimal deployment boundary required by the scenario runner."""

    def deploy(self, service: str, version: str):
        """Deploy one service version."""


@dataclass(frozen=True)
class ScenarioExecutionResult:
    """Result of executing the Scenario Engine lifecycle."""

    state: ScenarioExecutionState
    traffic: TrafficResult
    incident: Incident


class ScenarioRunner:
    """Execute the deterministic Scenario Engine lifecycle."""

    def __init__(
        self,
        *,
        deployment_controller: DeploymentController,
        traffic_generator: TrafficGenerator,
        incident_creator: IncidentCreator,
        resetter: ScenarioResetter,
        base_url: str,
    ) -> None:
        """Create a runner from explicit Scenario Engine boundaries."""
        self._deployment_controller = deployment_controller
        self._traffic_generator = traffic_generator
        self._incident_creator = incident_creator
        self._resetter = resetter
        self._base_url = base_url

    def execute(
        self,
        scenario: ScenarioDefinition,
        *,
        traffic_duration_seconds: float = 1.0,
    ) -> ScenarioExecutionResult:
        """Execute one scenario through incident creation."""
        state = ScenarioExecutionState(scenario_id=scenario.scenario_id)

        self._deploy(scenario.service, scenario.initial_version)
        state = state.transition_to(
            ExecutionPhase.INITIAL_STATE_APPLIED,
            initial_service_version=scenario.initial_version,
            active_service_version=scenario.initial_version,
        )

        fault_version = scenario.fault.version
        if fault_version is None:
            raise ScenarioExecutionError(
                "Scenario fault does not define a deployment version"
            )

        self._deploy(scenario.service, fault_version)
        state = state.transition_to(
            ExecutionPhase.FAULT_INTRODUCED,
            active_service_version=fault_version,
        )

        traffic = self._traffic_generator.generate(
            TrafficConfig(
                base_url=self._base_url,
                requests_per_second=scenario.traffic.requests_per_second,
                duration_seconds=traffic_duration_seconds,
            )
        )
        state = state.transition_to(ExecutionPhase.TRAFFIC_GENERATED)

        if traffic.failed == 0:
            raise ScenarioExecutionError(
                "Scenario traffic did not produce a failed request"
            )

        state = state.transition_to(ExecutionPhase.FAILURE_EMERGED)

        incident = self._incident_creator.create(
            IncidentCreateRequest(
                service=scenario.service,
                environment="production",
                severity="P1",
                status="OPEN",
                summary=(f"Checkout traffic produced {traffic.failed} failed requests"),
            )
        )
        state = state.transition_to(
            ExecutionPhase.INCIDENT_CREATED,
            incident_id=incident.incident_id,
        )
        state = state.transition_to(ExecutionPhase.OPSPILOT_INVESTIGATING)

        return ScenarioExecutionResult(
            state=state,
            traffic=traffic,
            incident=incident,
        )

    def reset(
        self,
        scenario: ScenarioDefinition,
        state: ScenarioExecutionState,
    ) -> ScenarioExecutionState:
        """Restore the scenario initial state after execution."""
        return self._resetter.reset(scenario, state)

    def _deploy(self, service: str, version: str) -> None:
        """Apply one deployment and normalize controller failures."""
        try:
            self._deployment_controller.deploy(service, version)
        except Exception as exc:
            raise ScenarioExecutionError(
                f"Unable to deploy {service}:{version}"
            ) from exc
