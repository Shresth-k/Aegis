"""Load and validate declarative Scenario Engine definitions.

Phase 3.2 establishes the boundary:

    YAML scenario definition -> ScenarioDefinition

The loader validates data but does not execute scenarios, control Docker,
introduce faults, generate traffic, or create incidents.
"""

from pathlib import Path

import yaml

from .models import ScenarioDefinition


class ScenarioDefinitionError(ValueError):
    """Raised when a scenario definition cannot be loaded or validated."""


def load_scenario(path: Path) -> ScenarioDefinition:
    """Load one YAML scenario file and validate it against the model."""
    try:
        raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ScenarioDefinitionError(f"Scenario file does not exist: {path}") from exc
    except OSError as exc:
        raise ScenarioDefinitionError(f"Unable to read scenario file: {path}") from exc
    except yaml.YAMLError as exc:
        raise ScenarioDefinitionError(f"Invalid YAML in scenario file: {path}") from exc

    if not isinstance(raw, dict):
        raise ScenarioDefinitionError(f"Scenario root must be a YAML mapping: {path}")

    try:
        return ScenarioDefinition.model_validate(raw)
    except ValueError as exc:
        raise ScenarioDefinitionError(
            f"Invalid scenario definition in {path}: {exc}"
        ) from exc
