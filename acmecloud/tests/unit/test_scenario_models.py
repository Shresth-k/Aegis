"""Unit tests for the Phase 3.1 Scenario Engine models."""

import pytest
from pydantic import ValidationError

from simulator.scenarios.models import ScenarioDefinition


@pytest.fixture
def itops_001() -> dict:
    """Return the canonical ITOPS-001 scenario definition."""
    return {
        "scenario_id": "ITOPS-001",
        "service": "checkout-service",
        "initial_version": "2.4.0",
        "fault": {
            "type": "bad_deployment",
            "version": "2.4.1",
        },
        "traffic": {
            "requests_per_second": 100,
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


def test_itops_001_matches_scenario_contract(itops_001: dict) -> None:
    """Verify the canonical scenario can be represented by the model."""
    scenario = ScenarioDefinition.model_validate(itops_001)

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


def test_unknown_fields_are_rejected(itops_001: dict) -> None:
    """Prevent misspelled or unsupported scenario fields from being ignored."""
    itops_001["unexpected"] = "value"

    with pytest.raises(ValidationError):
        ScenarioDefinition.model_validate(itops_001)


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("scenario_id", ""),
        ("service", ""),
        ("initial_version", ""),
        ("expected_root_cause", ""),
    ],
)
def test_required_string_fields_cannot_be_empty(
    itops_001: dict,
    field: str,
    value: str,
) -> None:
    """Reject empty required string values."""
    itops_001[field] = value

    with pytest.raises(ValidationError):
        ScenarioDefinition.model_validate(itops_001)


def test_traffic_rate_must_be_positive(itops_001: dict) -> None:
    """Reject a scenario that cannot generate positive traffic."""
    itops_001["traffic"]["requests_per_second"] = 0

    with pytest.raises(ValidationError):
        ScenarioDefinition.model_validate(itops_001)


def test_bad_deployment_must_change_version(itops_001: dict) -> None:
    """Reject a bad-deployment fault that does not change the version."""
    itops_001["fault"]["version"] = "2.4.0"

    with pytest.raises(ValidationError, match="must differ"):
        ScenarioDefinition.model_validate(itops_001)


def test_optional_fault_version_is_supported(itops_001: dict) -> None:
    """Allow fault types that do not require a deployment version."""
    itops_001["fault"] = {"type": "database_saturation"}

    scenario = ScenarioDefinition.model_validate(itops_001)

    assert scenario.fault.type == "database_saturation"
    assert scenario.fault.version is None
