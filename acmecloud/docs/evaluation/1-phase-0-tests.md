# Phase 0 Tests

## Purpose

The Phase 0 test suite verifies the AcmeCloud checkout service at two levels:

- unit tests for request validation
- integration tests against the running Docker service and PostgreSQL database

The tests use the real checkout service and real PostgreSQL instance. The integration tests do not mock the HTTP or database layers.

## Test Layout

```text
tests/
├── integration/
│   └── test_checkout_service.py
└── unit/
    └── test_checkout_api.py
```

## Unit Tests

`tests/unit/test_checkout_api.py` validates the `CheckoutRequest` Pydantic model.

Covered behavior:

- valid UUID customer IDs
- positive checkout amounts
- three-character currencies
- rejection of zero amounts
- rejection of negative amounts
- rejection of invalid UUIDs
- rejection of invalid currency lengths

These tests do not require a running database.

## Integration Tests

`tests/integration/test_checkout_service.py` communicates with the running checkout service at:

```text
http://localhost:8000
```

The tests verify:

- `/health` returns HTTP 200
- health reports the expected service name and version
- PostgreSQL dependency health is reported
- `/checkout` creates an order
- the created order is persisted in PostgreSQL
- persisted customer ID is correct
- persisted order status is `confirmed`
- persisted amount is `Decimal("149.99")`
- currency is normalized to uppercase
- invalid checkout payloads return HTTP 422

The integration tests connect directly to the AcmeCloud PostgreSQL container to verify persistence.

## Running Tests

Run the complete test suite with:

```bash
uv run pytest
```

Run Ruff:

```bash
uv run ruff check .
```

Check formatting:

```bash
uv run ruff format --check .
```

The Phase 0 baseline currently passes:

```text
10 passed
```

## Test Environment

Integration tests expect the Phase 0 Docker environment to be running:

```bash
docker compose up -d
```

The checkout service must be available on port `8000`, and PostgreSQL must be available on port `5432`.

## Scope

This test suite intentionally covers only the Phase 0 checkout functionality.

It does not yet test:

- controlled deployment faults
- service version switching
- metrics
- distributed tracing
- logs
- scenario execution
- remediation
- rollback
- policy evaluation
- approvals
- MCP tools
- RAG
- LangGraph workflows

Those capabilities belong to later phases.
