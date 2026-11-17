# Local Development

## Purpose

This document describes the Phase 0 local development environment for OpsPilot and its simulated AcmeCloud foundation.

## Prerequisites

The current development environment uses:

* Fedora Linux
* Python 3.12
* uv
* Docker
* Docker Compose

The repository pins the Python major/minor version through `.python-version`.

Python dependencies are managed with uv.

## Environment Variables

Create a local `.env` file at the repository root:

```dotenv
POSTGRES_DB=acmecloud
POSTGRES_USER=acmecloud
POSTGRES_PASSWORD=acmecloud
```

`.env` is ignored by Git and must not be committed.

Docker Compose uses these variables to configure PostgreSQL and to construct the checkout service `DATABASE_URL`.

## Start the Environment

From the repository root:

```bash
docker compose up -d
```

Check service state:

```bash
docker compose ps
```

Expected Phase 0 services:

```text
acmecloud-postgres
acmecloud-checkout
```

PostgreSQL should report a healthy container state.

## Verify Checkout Service

Check the health endpoint:

```bash
curl http://localhost:8000/health
```

A healthy response reports `checkout-service` version `2.4.0` and a healthy PostgreSQL dependency.

Create a test order with:

```bash
curl -X POST http://localhost:8000/checkout \
  -H 'Content-Type: application/json' \
  -d '{
    "customer_id": "00000000-0000-0000-0000-000000000001",
    "total_amount": "149.99",
    "currency": "usd"
  }'
```

The expected HTTP status is `201`.

## PostgreSQL Inspection

PostgreSQL runs inside Docker and is exposed locally on port `5432`.

The database can be inspected with DBeaver using:

```text
Host: localhost
Port: 5432
Database: acmecloud
User: acmecloud
Password: value from .env
```

The Phase 0 schema contains the `orders` table.

The repository does not require a host PostgreSQL installation.

## Useful Docker Commands

View running services:

```bash
docker compose ps
```

View checkout logs:

```bash
docker compose logs --tail=50 checkout-service
```

View PostgreSQL logs:

```bash
docker compose logs --tail=50 postgres
```

Stop the environment:

```bash
docker compose down
```

Stop the environment and remove its database volume:

```bash
docker compose down -v
```

The final command destroys the local PostgreSQL data volume and should only be used when resetting the local database is intentional.

## Python Environment

Create or synchronize the environment with:

```bash
uv sync
```

Activate the environment when desired:

```bash
source .venv/bin/activate
```

The repository lockfile is `uv.lock`.

## Code Quality

Run Ruff linting:

```bash
uv run ruff check .
```

Check formatting:

```bash
uv run ruff format --check .
```

Apply formatting when needed:

```bash
uv run ruff format .
```

## API Testing

Bruno is the planned API testing tool for the project. Its Phase 0 collection will cover the checkout service health and checkout endpoints.

Automated Python tests will cover application behavior and integration with the running Phase 0 environment.

## Phase 0 Runtime Boundary

The current local environment contains only the implemented Phase 0 foundation:

```text
Docker Compose
   |
   +-- PostgreSQL
   |
   +-- checkout-service
```

Prometheus, Grafana, OpenTelemetry, the Scenario Engine, MCP services, RAG, LangGraph, policy enforcement, approval workflows, remediation, verification, and MLflow are later phases and are not required to run the current Phase 0 environment.
