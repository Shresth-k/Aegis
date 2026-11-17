# Checkout Service API

## Overview

`checkout-service` is an AcmeCloud application in the simulated enterprise environment.

Current service version:

```text
2.4.0
```

Phase 0 exposes two HTTP endpoints:

```text
GET  /health
POST /checkout
```

Base URL for local development:

```text
http://localhost:8000
```

## `GET /health`

Checks service availability and PostgreSQL connectivity.

### Success

HTTP status:

```text
200 OK
```

Response:

```json
{
  "status": "healthy",
  "service": "checkout-service",
  "version": "2.4.0",
  "database": "healthy"
}
```

The endpoint executes `SELECT 1` through the configured database session.

### Database Failure

If the database check fails, the endpoint returns:

```text
503 Service Unavailable
```

with an unhealthy response containing the service name and database availability status.

## `POST /checkout`

Creates and persists a basic order.

### Request

Content type:

```text
application/json
```

Example:

```json
{
  "customer_id": "00000000-0000-0000-0000-000000000001",
  "total_amount": "149.99",
  "currency": "usd"
}
```

### Validation

`customer_id` must be a valid UUID.

`total_amount` must be greater than zero.

`currency` must contain exactly three characters. The application uppercases the value before persistence.

Invalid request bodies are rejected by FastAPI/Pydantic with HTTP `422`.

### Success Response

HTTP status:

```text
201 Created
```

Example:

```json
{
  "order_id": "<generated-order-uuid>",
  "status": "confirmed"
}
```

The generated order is persisted in PostgreSQL before the response is returned.

## Persistence Model

The service maps the `orders` table using SQLAlchemy.

```text
orders
- id
- customer_id
- status
- total_amount
- currency
- created_at
```

Transactions are committed explicitly by the checkout operation. Database sessions are closed after each request.

## Configuration

The service requires:

```text
DATABASE_URL
```

Docker Compose constructs the value from the PostgreSQL environment variables and the Docker service name `postgres`.

The application does not hard-code environment-specific database credentials.

## Local Container

The service is built from:

```text
simulator/services/checkout/Dockerfile
```

The container runs Uvicorn on:

```text
0.0.0.0:8000
```

The local host mapping is:

```text
localhost:8000 -> checkout-service:8000
```

## Phase 0 Limitations

The endpoint currently persists an order only. It does not call payment, inventory, notification, authentication, Redis, or other AcmeCloud services.

Those dependencies are part of the broader AcmeCloud design and will be introduced in later phases.
