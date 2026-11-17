"""Unit tests for the Phase 3.3 Scenario Registry."""

from pathlib import Path

import pytest

from simulator.scenarios.registry import (
    DuplicateScenarioIDError,
    ScenarioNotFoundError,
    ScenarioRegistry,
    ScenarioRegistryError,
)

CANONICAL_SCENARIO = """scenario_id: ITOPS-001
service: checkout-service
initial_version: 2.4.0
fault:
  type: bad_deployment
  version: 2.4.1
traffic:
  requests_per_second: 100
expected_root_cause: bad_deployment
expected_action:
  type: rollback
  target_version: 2.4.0
approval_required: true
expected_final_state:
  service_version: 2.4.0
  service_health: healthy
"""


def write_scenario(directory: Path, filename: str, scenario_id: str) -> None:
    """Write a minimal valid scenario with the requested ID."""
    content = CANONICAL_SCENARIO.replace(
        "scenario_id: ITOPS-001",
        f"scenario_id: {scenario_id}",
    )
    (directory / filename).write_text(content, encoding="utf-8")


def test_registry_discovers_yaml_scenarios(tmp_path: Path) -> None:
    """Valid YAML scenario files are discovered and loaded."""
    write_scenario(tmp_path, "itops-002.yaml", "ITOPS-002")
    write_scenario(tmp_path, "itops-001.yaml", "ITOPS-001")

    scenarios = ScenarioRegistry(tmp_path).list()

    assert [scenario.scenario_id for scenario in scenarios] == [
        "ITOPS-001",
        "ITOPS-002",
    ]


def test_registry_returns_scenarios_in_deterministic_id_order(
    tmp_path: Path,
) -> None:
    """Registry ordering is based on scenario ID, not filesystem order."""
    write_scenario(tmp_path, "z.yaml", "ITOPS-010")
    write_scenario(tmp_path, "a.yaml", "ITOPS-002")
    write_scenario(tmp_path, "m.yaml", "ITOPS-001")

    registry = ScenarioRegistry(tmp_path)

    first = [scenario.scenario_id for scenario in registry.list()]
    second = [scenario.scenario_id for scenario in registry.list()]

    assert first == ["ITOPS-001", "ITOPS-002", "ITOPS-010"]
    assert second == first


def test_registry_get_returns_requested_scenario(tmp_path: Path) -> None:
    """A known scenario ID resolves to its typed definition."""
    write_scenario(tmp_path, "itops-001.yaml", "ITOPS-001")

    scenario = ScenarioRegistry(tmp_path).get("ITOPS-001")

    assert scenario.scenario_id == "ITOPS-001"
    assert scenario.service == "checkout-service"


def test_registry_get_rejects_unknown_scenario(tmp_path: Path) -> None:
    """Unknown scenario IDs fail explicitly."""
    write_scenario(tmp_path, "itops-001.yaml", "ITOPS-001")

    with pytest.raises(ScenarioNotFoundError, match="ITOPS-999"):
        ScenarioRegistry(tmp_path).get("ITOPS-999")


def test_registry_rejects_duplicate_scenario_ids(tmp_path: Path) -> None:
    """Two files cannot register the same scenario ID."""
    write_scenario(tmp_path, "first.yaml", "ITOPS-001")
    write_scenario(tmp_path, "second.yaml", "ITOPS-001")

    with pytest.raises(DuplicateScenarioIDError, match="ITOPS-001"):
        ScenarioRegistry(tmp_path).list()


def test_registry_wraps_invalid_scenario_definition(
    tmp_path: Path,
) -> None:
    """Malformed or invalid scenario files fail during discovery."""
    (tmp_path / "broken.yaml").write_text(
        "scenario_id: ITOPS-001\nservice:\n  - invalid\n",
        encoding="utf-8",
    )

    with pytest.raises(ScenarioRegistryError, match="broken.yaml"):
        ScenarioRegistry(tmp_path).list()


def test_registry_rejects_missing_directory(tmp_path: Path) -> None:
    """A missing scenario directory is an explicit registry error."""
    missing = tmp_path / "scenarios"

    with pytest.raises(ScenarioRegistryError, match="does not exist"):
        ScenarioRegistry(missing).list()


def test_registry_rejects_file_as_directory(tmp_path: Path) -> None:
    """The registry requires a directory, not a single file."""
    scenario_file = tmp_path / "scenario.yaml"
    scenario_file.write_text(CANONICAL_SCENARIO, encoding="utf-8")

    with pytest.raises(ScenarioRegistryError, match="not a directory"):
        ScenarioRegistry(scenario_file).list()


def test_registry_ignores_non_yaml_files(tmp_path: Path) -> None:
    """Unrelated files do not participate in scenario discovery."""
    write_scenario(tmp_path, "itops-001.yaml", "ITOPS-001")
    (tmp_path / "README.md").write_text("not a scenario", encoding="utf-8")
    (tmp_path / "notes.txt").write_text("not a scenario", encoding="utf-8")

    scenarios = ScenarioRegistry(tmp_path).list()

    assert [scenario.scenario_id for scenario in scenarios] == ["ITOPS-001"]
