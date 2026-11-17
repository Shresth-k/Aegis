# Checkout Service Deployment Versions

## Overview

The checkout service deployment version is selected through the `CHECKOUT_VERSION` environment variable used by Docker Compose.

Available Phase 1 versions:

```text
2.4.0
2.4.1
```

## Healthy Deployment

Start version 2.4.0 with:

```bash
CHECKOUT_VERSION=2.4.0 docker compose down
CHECKOUT_VERSION=2.4.0 docker compose up -d --build
```

Verify:

```bash
curl http://localhost:8000/health
```

Expected response:

```json
{
  "status": "healthy",
  "service": "checkout-service",
  "version": "2.4.0",
  "database": "healthy"
}
```

## Faulty Deployment

Start version 2.4.1 with:

```bash
CHECKOUT_VERSION=2.4.1 docker compose down
CHECKOUT_VERSION=2.4.1 docker compose up -d --build
```

Verify:

```bash
curl http://localhost:8000/health
```

Expected response reports version `2.4.1` and a healthy database dependency.

Inspect the deployment configuration:

```bash
docker exec acmecloud-checkout env | grep -E 'SERVICE_VERSION|DB_CONNECTION_POOL|DB_POOL_TIMEOUT|DB_OPERATION_DELAY'
```

Expected values:

```text
SERVICE_VERSION=2.4.1
DB_CONNECTION_POOL=5
DB_POOL_TIMEOUT=0.5
DB_OPERATION_DELAY_MS=2000
```

## Reset to Healthy State

After testing the fault, restore version 2.4.0:

```bash
CHECKOUT_VERSION=2.4.0 docker compose down
CHECKOUT_VERSION=2.4.0 docker compose up -d --build
```

## Deployment Configuration Files

The version-specific configuration is stored under:

```text
simulator/deployments/checkout-service/
```

with:

```text
2.4.0.env
2.4.1.env
```

Docker Compose selects the corresponding file using:

```yaml
env_file:
  - ./simulator/deployments/checkout-service/${CHECKOUT_VERSION:-2.4.0}.env
```

The default version is therefore 2.4.0 when `CHECKOUT_VERSION` is not supplied.

## Important Testing Boundary

The normal integration tests expect the healthy deployment contract.

The Phase 1 fault test is specifically intended for a running 2.4.1 deployment. When the service is running another version, the fault test skips rather than changing the healthy service expectations.
