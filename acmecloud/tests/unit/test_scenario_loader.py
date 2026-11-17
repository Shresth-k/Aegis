"""Unit tests for Phase 3.2 YAML scenario loading."""

from pathlib import Path

import pytest
import yaml

from simulator.scenarios.loader import (
    ScenarioDefinitionError,
    load_scenario,
)

SCENARIO_PATH = Path("evaluation/scenarios/ITOPS-001.yaml")


def test_itops_001_loads_from_yaml() -> None:
    """Verify the canonical scenario loads into the typed model."""
    scenario = load_scenario(SCENARIO_PATH)

    assert scenario.scenario_id == "ITOPS-001"
    assert scenario.service == "checkout-service"
    assert scenario.initial_version == "2.4.0"
    assert scenario.fault.type == "bad_deployment"
    assert scenario.fault.version == "2.4.1"
    assert scenario.traffic.requests_per_second == 100
    assert scenario.expected_root_cause == "bad_deployment"
    assert scenario.expected_action.type == "rollback"
    assert scenario.expected_action.target_version == "2.4.0"
    assert scenario.approval_required is True
    assert scenario.expected_final_state.service_version == "2.4.0"
    assert scenario.expected_final_state.service_health == "healthy"


def test_missing_scenario_file_is_rejected(tmp_path: Path) -> None:
    """Verify missing scenario files fail with a domain-specific error."""
    with pytest.raises(ScenarioDefinitionError, match="does not exist"):
        load_scenario(tmp_path / "missing.yaml")


def test_invalid_yaml_is_rejected(tmp_path: Path) -> None:
    """Verify malformed YAML fails before model validation."""
    path = tmp_path / "invalid.yaml"
    path.write_text("scenario_id: [", encoding="utf-8")

    with pytest.raises(ScenarioDefinitionError, match="Invalid YAML"):
        load_scenario(path)


def test_non_mapping_yaml_is_rejected(tmp_path: Path) -> None:
    """Verify a scalar or sequence cannot be a scenario root."""
    path = tmp_path / "list.yaml"
    path.write_text("- ITOPS-001\n", encoding="utf-8")

    with pytest.raises(ScenarioDefinitionError, match="YAML mapping"):
        load_scenario(path)


def test_invalid_scenario_fields_are_rejected(tmp_path: Path) -> None:
    """Verify YAML fields still pass through ScenarioDefinition validation."""
    path = tmp_path / "invalid-scenario.yaml"
    path.write_text(
        yaml.safe_dump(
            {
                "scenario_id": "ITOPS-001",
                "service": "checkout-service",
                "initial_version": "2.4.0",
                "fault": {
                    "type": "bad_deployment",
                    "version": "2.4.1",
                },
                "traffic": {
                    "requests_per_second": 0,
                },
                "expected_root_cause": "bad_deployment",
                "expected_action": {
                    "type": "rollback",
                    "target_version": "2.4.0",
                },
                "approval_required": True,
                "expected_final_state": {
                    "service_version": "2.4.0",
                    "service_health": "healthy",
                },
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(ScenarioDefinitionError, match="Invalid scenario definition"):
        load_scenario(path)


def test_unknown_fields_are_rejected(tmp_path: Path) -> None:
    """Verify the strict Phase 3.1 model applies to YAML input."""
    path = tmp_path / "unknown-field.yaml"
    path.write_text(
        """
scenario_id: ITOPS-001
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
unexpected: true
""",
        encoding="utf-8",
    )

    with pytest.raises(ScenarioDefinitionError, match="Invalid scenario definition"):
        load_scenario(path)
