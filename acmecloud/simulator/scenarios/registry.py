"""Discover and index declarative Scenario Engine definitions.

Phase 3.3 establishes the discovery boundary:

    scenario directory -> ScenarioRegistry -> ScenarioDefinition

The registry is responsible for discovering YAML definitions, validating them
through the existing scenario loader, detecting duplicate scenario IDs, and
providing deterministic lookup.

It intentionally does not execute scenarios, control Docker, generate traffic,
create incidents, or mutate AcmeCloud state.
"""

from pathlib import Path

from .loader import ScenarioDefinitionError, load_scenario
from .models import ScenarioDefinition


class ScenarioRegistryError(ValueError):
    """Base error raised for invalid Scenario Registry state."""


class ScenarioNotFoundError(ScenarioRegistryError):
    """Raised when a requested scenario ID is not registered."""


class DuplicateScenarioIDError(ScenarioRegistryError):
    """Raised when multiple files define the same scenario ID."""


class ScenarioRegistry:
    """Discover and provide deterministic access to scenario definitions."""

    def __init__(self, directory: Path) -> None:
        """Create a registry rooted at one scenario-definition directory."""
        self._directory = directory

    def list(self) -> list[ScenarioDefinition]:
        """Load all YAML scenarios in deterministic scenario-ID order."""
        if not self._directory.exists():
            raise ScenarioRegistryError(
                f"Scenario directory does not exist: {self._directory}"
            )

        if not self._directory.is_dir():
            raise ScenarioRegistryError(
                f"Scenario path is not a directory: {self._directory}"
            )

        scenario_paths = sorted(self._directory.glob("*.yaml"))
        scenarios: list[ScenarioDefinition] = []
        scenario_ids: dict[str, Path] = {}

        for path in scenario_paths:
            try:
                scenario = load_scenario(path)
            except ScenarioDefinitionError as exc:
                raise ScenarioRegistryError(str(exc)) from exc

            previous_path = scenario_ids.get(scenario.scenario_id)
            if previous_path is not None:
                raise DuplicateScenarioIDError(
                    f"Duplicate scenario_id '{scenario.scenario_id}' "
                    f"defined by {previous_path} and {path}"
                )

            scenario_ids[scenario.scenario_id] = path
            scenarios.append(scenario)

        return sorted(scenarios, key=lambda scenario: scenario.scenario_id)

    def get(self, scenario_id: str) -> ScenarioDefinition:
        """Return one scenario by ID or raise ScenarioNotFoundError."""
        for scenario in self.list():
            if scenario.scenario_id == scenario_id:
                return scenario

        raise ScenarioNotFoundError(f"Scenario not found: {scenario_id}")
