# Phase 0 AcmeCloud Foundation

## Purpose

This document records the implemented Phase 0 foundation of AcmeCloud, the simulated enterprise environment used by OpsPilot.

OpsPilot is intended to investigate incidents in a simulated production environment, reason from operational evidence and organizational knowledge, perform approved remediation, verify recovery, and evaluate its behavior. AcmeCloud is the environment on which those workflows will operate.

## Phase 0 Scope

The project requirements define Phase 0 as the AcmeCloud foundation:

* checkout-service
* PostgreSQL
* Docker
* health endpoint
* basic API

The Phase 0 success condition is that checkout works locally.

Phase 0 intentionally does not implement the complete AcmeCloud dependency graph, controlled failures, observability stack, Scenario Engine, MCP, RAG, LangGraph, policy, approval, remediation, verification, or MLflow workflow.

## Current Repository Components

The implemented Phase 0 components are:

```text
AcmeCloud
|
+-- checkout-service
|   +-- FastAPI application
|   +-- SQLAlchemy database access
|   +-- PostgreSQL health check
|   +-- POST /checkout
|   +-- GET /health
|
+-- PostgreSQL 17
|   +-- orders table
|
+-- Docker Compose
    +-- postgres
    +-- checkout-service
```

The repository separates AcmeCloud behavior under `simulator/` from the future OpsPilot platform layers.

## Runtime Architecture

```text
Client
  |
  | HTTP
  v
checkout-service :8000
  |
  | SQLAlchemy / psycopg
  v
PostgreSQL :5432
  |
  v
orders
```

Docker Compose provides the local runtime. The checkout service waits for PostgreSQL to become healthy before starting.

## Checkout Service

The service is currently versioned as `2.4.0`.

Its Phase 0 API consists of:

```text
GET  /health
POST /checkout
```

The service uses environment configuration rather than embedding database credentials in application code. The database URL is supplied through `DATABASE_URL` by Docker Compose.

## Database

The PostgreSQL database belongs to the simulated AcmeCloud environment. It is intentionally separate from the future OpsPilot operational database.

Phase 0 creates the following table:

```text
orders
- id UUID primary key
- customer_id UUID not null
- status VARCHAR(32) not null
- total_amount NUMERIC(12, 2) not null
- currency VARCHAR(3) not null
- created_at TIMESTAMPTZ not null
```

Indexes currently exist on `customer_id` and `created_at`.

The schema is initialized from `database/init/001_init.sql` when the PostgreSQL data volume is initialized.

## Health Model

The checkout service does not consider the HTTP process alone sufficient for a healthy state.

`GET /health` executes `SELECT 1` against PostgreSQL. A successful response reports both service and database health. If the database cannot be reached, the endpoint returns HTTP `503` with an unhealthy status.

This dependency-aware health behavior provides a foundation for the observability and verification phases that follow.

## Checkout Flow

A successful checkout request:

1. Validates `customer_id` as a UUID.
2. Validates `total_amount` as a positive decimal.
3. Validates `currency` as exactly three characters.
4. Creates an order UUID.
5. Sets the initial order status to `confirmed`.
6. Uppercases the currency value.
7. Persists the order in PostgreSQL.
8. Returns HTTP `201` with the order ID and status.

Payment, inventory, notification, authentication, and other dependencies are deliberately not part of this Phase 0 flow.

## Relationship to Later Phases

The requirements define later work as follows:

```text
Phase 1  Service versions + controlled fault
Phase 2  Observability
Phase 3  Scenario Engine
Phase 4  MCP
Phase 5  LangGraph
Phase 6  RAG
Phase 7  Policy and Risk
Phase 8  Remediation
Phase 9  Verification
Phase 10 Human-in-the-loop
Phase 11 MLflow
```

The first planned controlled failure uses checkout-service versions `2.4.0` and `2.4.1`. Version `2.4.1` is intended to introduce a deliberately faulty database connection pool configuration and produce failures under controlled traffic. That behavior is not implemented in Phase 0.

## Current Boundary

At the end of Phase 0, the environment provides a real HTTP application and a real PostgreSQL dependency running in Docker. It is a foundation for the later incident simulation rather than an incident-resolution system itself.
