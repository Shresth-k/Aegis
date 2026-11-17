"""Unit tests for operational incident creation."""

from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from simulator.scenarios.incident import (
    Incident,
    IncidentCreateRequest,
    IncidentCreationError,
    IncidentCreator,
    InMemoryIncidentStore,
)


def _request(**overrides: object) -> IncidentCreateRequest:
    """Build a valid incident creation request."""
    values = {
        "service": "checkout-service",
        "environment": "simulation",
        "severity": "high",
        "status": "open",
        "summary": "Checkout requests are failing.",
    }
    values.update(overrides)
    return IncidentCreateRequest(**values)


def test_incident_contains_operational_information_only() -> None:
    """Evaluation-only fields are absent from the operational model."""
    assert "expected_root_cause" not in Incident.model_fields
    assert "expected_action" not in Incident.model_fields


def test_incident_create_request_contains_operational_fields_only() -> None:
    """Incident creation requests contain only observed information."""
    assert set(IncidentCreateRequest.model_fields) == {
        "service",
        "environment",
        "severity",
        "status",
        "summary",
    }


def test_incident_creator_creates_deterministic_incident_id() -> None:
    """The first persisted incident receives INC-001."""
    store = InMemoryIncidentStore()
    creator = IncidentCreator(store)

    incident = creator.create(_request())

    assert incident.incident_id == "INC-001"


def test_incident_creator_assigns_incrementing_ids() -> None:
    """Subsequent incidents receive deterministic sequence IDs."""
    store = InMemoryIncidentStore()
    creator = IncidentCreator(store)

    first = creator.create(_request(summary="First failure."))
    second = creator.create(_request(summary="Second failure."))

    assert first.incident_id == "INC-001"
    assert second.incident_id == "INC-002"


def test_incident_creator_preserves_operational_request_fields() -> None:
    """Observed incident information is copied into the incident record."""
    store = InMemoryIncidentStore()
    creator = IncidentCreator(store)

    incident = creator.create(
        _request(
            service="payment-service",
            environment="production",
            severity="critical",
            status="investigating",
            summary="Payment dependency is failing.",
        )
    )

    assert incident.service == "payment-service"
    assert incident.environment == "production"
    assert incident.severity == "critical"
    assert incident.status == "investigating"
    assert incident.summary == "Payment dependency is failing."


def test_incident_creator_assigns_utc_creation_timestamp() -> None:
    """Created incidents receive an aware UTC timestamp."""
    store = InMemoryIncidentStore()
    creator = IncidentCreator(store)

    before = datetime.now(UTC)
    incident = creator.create(_request())
    after = datetime.now(UTC)

    assert incident.created_at.tzinfo == UTC
    assert before <= incident.created_at <= after


def test_in_memory_store_persists_and_retrieves_incident() -> None:
    """Saved incidents can be retrieved by their deterministic ID."""
    store = InMemoryIncidentStore()
    creator = IncidentCreator(store)

    incident = creator.create(_request())

    assert store.get("INC-001") == incident


def test_in_memory_store_lists_incidents_in_deterministic_order() -> None:
    """Incident listing is ordered by incident sequence ID."""
    store = InMemoryIncidentStore()
    creator = IncidentCreator(store)

    first = creator.create(_request(summary="First failure."))
    second = creator.create(_request(summary="Second failure."))

    assert store.list() == [first, second]


def test_in_memory_store_rejects_duplicate_incident_ids() -> None:
    """The store rejects attempts to persist an existing incident ID."""
    store = InMemoryIncidentStore()
    incident = Incident(
        incident_id="INC-001",
        service="checkout-service",
        environment="simulation",
        severity="high",
        status="open",
        summary="Checkout requests are failing.",
        created_at=datetime.now(UTC),
    )

    store.save(incident)

    with pytest.raises(
        IncidentCreationError,
        match="Incident already exists: INC-001",
    ):
        store.save(incident)


def test_in_memory_store_raises_for_missing_incident() -> None:
    """Retrieving an unknown incident raises an operational error."""
    store = InMemoryIncidentStore()

    with pytest.raises(
        IncidentCreationError,
        match="Incident not found: INC-999",
    ):
        store.get("INC-999")


def test_incident_models_reject_extra_fields() -> None:
    """Operational models reject evaluation-only or arbitrary extra fields."""
    with pytest.raises(ValidationError):
        IncidentCreateRequest(
            service="checkout-service",
            environment="simulation",
            severity="high",
            status="open",
            summary="Checkout requests are failing.",
            expected_root_cause="bad_deployment",
        )

    with pytest.raises(ValidationError):
        Incident(
            incident_id="INC-001",
            service="checkout-service",
            environment="simulation",
            severity="high",
            status="open",
            summary="Checkout requests are failing.",
            created_at=datetime.now(UTC),
            expected_action="rollback",
        )
