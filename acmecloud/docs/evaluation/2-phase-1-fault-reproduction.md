# Phase 1: Fault Reproduction Test

## Purpose

The Phase 1 integration test verifies that the deliberately faulty checkout-service deployment produces the expected failure behavior under concurrent traffic.

Test file:

```text
tests/integration/test_checkout_fault.py
```

## Test Contract

The test:

1. Queries `/health`.
2. Requires checkout-service version `2.4.1`.
3. Confirms the service and database report healthy at the dependency level.
4. Sends 20 concurrent checkout requests.
5. Requires all requests to return an HTTP response.
6. Allows only HTTP 201 and HTTP 500 results.
7. Requires at least one HTTP 201.
8. Requires at least one HTTP 500.

The test intentionally does not require an exact success/failure ratio.

## Running the Test

Start the faulty deployment:

```bash
CHECKOUT_VERSION=2.4.1 docker compose down
CHECKOUT_VERSION=2.4.1 docker compose up -d --build
```

Run only the Phase 1 fault test:

```bash
CHECKOUT_VERSION=2.4.1 uv run pytest tests/integration/test_checkout_fault.py -v
```

When the healthy deployment is running, the test skips:

```text
1 skipped
```

This keeps the standard test suite safe to run against the normal 2.4.0 environment.

## Normal Test Suite

After restoring 2.4.0:

```bash
CHECKOUT_VERSION=2.4.0 docker compose down
CHECKOUT_VERSION=2.4.0 docker compose up -d --build
```

Run:

```bash
uv run ruff check .
uv run ruff format --check .
uv run pytest
```

The verified healthy baseline is:

```text
10 passed
```

## Manual Fault Evidence

The Phase 1 fault was manually reproduced with 20 concurrent checkout requests.

Observed result:

```text
201: 5
500: 15
total: 20
```

The exact ratio is not part of the automated contract; it is recorded as verification evidence for the tested run.

## Completion Status

The Phase 1 implementation has been verified to:

- run checkout-service 2.4.0;
- run checkout-service 2.4.1;
- apply distinct deployment configuration;
- reproduce HTTP 500 failures under concurrent traffic;
- preserve the healthy integration test suite;
- provide an automated fault reproduction test.

Phase 1 is therefore ready to be closed before starting Phase 2 observability work.
