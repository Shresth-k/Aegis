"""Phase 3.10 integration test for the real Scenario Engine lifecycle.

This test requires the AcmeCloud Docker Compose environment to be running.
It uses the concrete deployment, traffic, incident, and reset boundaries.
"""

from __future__ import annotations

import json
import time
import urllib.error
import urllib.request
from pathlib import Path

import pytest

from simulator.scenarios.deployment import DockerComposeDeploymentController
from simulator.scenarios.execution_state import ExecutionPhase, ExecutionStatus
from simulator.scenarios.incident import IncidentCreator, InMemoryIncidentStore
from simulator.scenarios.registry import ScenarioRegistry
from simulator.scenarios.reset import ScenarioResetter
from simulator.scenarios.runner import ScenarioRunner
from simulator.scenarios.traffic import TrafficGenerator

PROJECT_ROOT = Path(__file__).resolve().parents[2]
COMPOSE_FILE = PROJECT_ROOT / "docker-compose.yml"
DEPLOYMENTS_ROOT = PROJECT_ROOT / "simulator" / "deployments"
SCENARIOS_ROOT = PROJECT_ROOT / "evaluation" / "scenarios"
BASE_URL = "http://localhost:8000"


def _health() -> tuple[int, dict[str, object] | None]:
    """Return the checkout health status and JSON body when available."""
    request = urllib.request.Request(f"{BASE_URL}/health", method="GET")
    try:
        with urllib.request.urlopen(request, timeout=5) as response:
            body = response.read().decode("utf-8")
            return response.status, json.loads(body)
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8")
        try:
            payload = json.loads(body)
        except json.JSONDecodeError:
            payload = None
        return exc.code, payload
    except (OSError, urllib.error.URLError):
        raise


def _wait_for_http(timeout_seconds: float = 30.0) -> None:
    """Wait until the checkout HTTP endpoint responds."""
    deadline = time.monotonic() + timeout_seconds

    while time.monotonic() < deadline:
        try:
            _health()
        except (OSError, urllib.error.URLError):
            time.sleep(1)
            continue
        return

    pytest.fail("checkout-service did not become reachable")


def _wait_for_healthy_version(
    expected_version: str,
    *,
    timeout_seconds: float = 30.0,
) -> None:
    """Wait until checkout reports the requested healthy version."""
    deadline = time.monotonic() + timeout_seconds
    last_status: int | None = None
    last_payload: dict[str, object] | None = None

    while time.monotonic() < deadline:
        try:
            last_status, last_payload = _health()
        except (OSError, urllib.error.URLError):
            time.sleep(1)
            continue

        if (
            last_status == 200
            and last_payload is not None
            and last_payload.get("status") == "healthy"
            and last_payload.get("version") == expected_version
        ):
            return

        time.sleep(1)

    pytest.fail(
        f"checkout-service did not become healthy on {expected_version}; "
        f"last_status={last_status!r}, last_payload={last_payload!r}"
    )


def test_itops_001_executes_and_resets_real_environment() -> None:
    """Execute ITOPS-001 with real Docker Compose and restore its initial state."""
    try:
        status, payload = _health()
    except (OSError, urllib.error.URLError) as exc:
        pytest.skip(f"AcmeCloud checkout-service is unavailable: {exc}")

    if status != 200 or payload is None:
        pytest.fail(
            "AcmeCloud checkout-service is reachable but not healthy: "
            f"status={status}, payload={payload!r}"
        )

    registry = ScenarioRegistry(SCENARIOS_ROOT)
    scenario = registry.get("ITOPS-001")

    deployment = DockerComposeDeploymentController(
        compose_file=COMPOSE_FILE,
        deployments_root=DEPLOYMENTS_ROOT,
        project_root=PROJECT_ROOT,
    )
    incident_store = InMemoryIncidentStore()
    incident_creator = IncidentCreator(incident_store)
    resetter = ScenarioResetter(deployment)
    traffic_generator = TrafficGenerator()

    deployment.deploy(scenario.service, scenario.initial_version)
    _wait_for_healthy_version(scenario.initial_version)

    runner = ScenarioRunner(
        deployment_controller=deployment,
        traffic_generator=traffic_generator,
        incident_creator=incident_creator,
        resetter=resetter,
        base_url=BASE_URL,
    )

    try:
        result = runner.execute(scenario, traffic_duration_seconds=1.0)

        assert result.state.phase is ExecutionPhase.OPSPILOT_INVESTIGATING
        assert result.state.active_service_version == "2.4.1"
        assert result.traffic.requested == 100
        assert result.traffic.failed > 0
        assert result.incident.incident_id == "INC-001"
        assert incident_store.get(result.incident.incident_id) == result.incident
        assert "expected_root_cause" not in type(result.incident).model_fields
        assert "expected_action" not in type(result.incident).model_fields

        reset_state = runner.reset(scenario, result.state)

        assert reset_state.status is ExecutionStatus.RESET
        assert reset_state.active_service_version is None
        assert reset_state.incident_id == result.incident.incident_id
        _wait_for_healthy_version(scenario.initial_version)
    finally:
        # Never leave the local AcmeCloud environment on the faulty version.
        deployment.deploy(scenario.service, scenario.initial_version)
        _wait_for_healthy_version(scenario.initial_version)
