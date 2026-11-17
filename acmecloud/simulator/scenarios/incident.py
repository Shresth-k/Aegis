"""Operational incident creation for the Scenario Engine.

Phase 3.7 establishes the incident boundary described by the OpsPilot
specification.

The creator turns observed operational information into an incident record.
It intentionally does not receive or store evaluation-only ground truth such
as expected_root_cause or expected_action.

Persistence is represented by an explicit store protocol. PostgreSQL will be
the authoritative implementation when the operational database layer and
Incident MCP are introduced. The in-memory store here keeps Phase 3.7
independently testable without creating a second operational state system.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Protocol

from pydantic import BaseModel, ConfigDict, Field


class IncidentCreationError(ValueError):
    """Raised when an incident cannot be created."""


class Incident(BaseModel):
    """Operational incident record visible to OpsPilot."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    incident_id: str = Field(min_length=1)
    service: str = Field(min_length=1)
    environment: str = Field(min_length=1)
    severity: str = Field(min_length=1)
    status: str = Field(min_length=1)
    summary: str = Field(min_length=1)
    created_at: datetime


class IncidentCreateRequest(BaseModel):
    """Observed information required to create an operational incident."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    service: str = Field(min_length=1)
    environment: str = Field(min_length=1)
    severity: str = Field(min_length=1)
    status: str = Field(min_length=1)
    summary: str = Field(min_length=1)


class IncidentStore(Protocol):
    """Persistence boundary for operational incidents."""

    def save(self, incident: Incident) -> Incident:
        """Persist and return an incident."""

    def get(self, incident_id: str) -> Incident:
        """Return an incident by ID."""

    def list(self) -> list[Incident]:
        """Return incidents in deterministic creation order."""


class IncidentCreator:
    """Create operational incidents without evaluation-only information."""

    def __init__(self, store: IncidentStore) -> None:
        """Create an incident creator backed by an explicit store."""
        self._store = store

    def create(self, request: IncidentCreateRequest) -> Incident:
        """Create one operational incident from observed information."""
        incident_id = self._next_incident_id()

        incident = Incident(
            incident_id=incident_id,
            service=request.service,
            environment=request.environment,
            severity=request.severity,
            status=request.status,
            summary=request.summary,
            created_at=datetime.now(UTC),
        )

        return self._store.save(incident)

    def _next_incident_id(self) -> str:
        """Generate the next deterministic ID from persisted incidents."""
        existing_ids = {incident.incident_id for incident in self._store.list()}
        sequence = 1

        while f"INC-{sequence:03d}" in existing_ids:
            sequence += 1

        return f"INC-{sequence:03d}"


class InMemoryIncidentStore:
    """Test-only incident store implementing the persistence boundary."""

    def __init__(self) -> None:
        """Create an empty incident store."""
        self._incidents: dict[str, Incident] = {}

    def save(self, incident: Incident) -> Incident:
        """Persist an incident and reject duplicate IDs."""
        if incident.incident_id in self._incidents:
            raise IncidentCreationError(
                f"Incident already exists: {incident.incident_id}"
            )

        self._incidents[incident.incident_id] = incident
        return incident

    def get(self, incident_id: str) -> Incident:
        """Return an incident or raise a creation error."""
        try:
            return self._incidents[incident_id]
        except KeyError as exc:
            raise IncidentCreationError(f"Incident not found: {incident_id}") from exc

    def list(self) -> list[Incident]:
        """Return incidents sorted by their sequence IDs."""
        return [self._incidents[incident_id] for incident_id in sorted(self._incidents)]
