# Phase 1: Controlled Faults

## Overview

Phase 1 introduces versioned checkout-service deployments and a deterministic, deployment-controlled fault.

The goal is to make the AcmeCloud simulator capable of representing a healthy deployment and a deliberately faulty deployment that produces HTTP 500 responses under concurrent traffic.

## Deployments

### Version 2.4.0

The healthy deployment uses:

```dotenv
SERVICE_VERSION=2.4.0
DB_CONNECTION_POOL=50
DB_POOL_TIMEOUT=5
DB_OPERATION_DELAY_MS=0
```

This configuration represents the normal checkout-service state.

### Version 2.4.1

The faulty deployment uses:

```dotenv
SERVICE_VERSION=2.4.1
DB_CONNECTION_POOL=5
DB_POOL_TIMEOUT=0.5
DB_OPERATION_DELAY_MS=2000
```

The smaller connection pool combined with the deliberate database operation delay creates contention under concurrent requests.

## Fault Mechanism

The checkout service creates a SQLAlchemy database session for each request.

For the faulty deployment:

1. The connection pool is limited to five connections.
2. A checkout database operation holds its database connection for 2000 ms.
3. The pool timeout is 0.5 seconds.
4. Concurrent requests that cannot obtain a connection before the timeout fail.
5. The API converts the database failure into HTTP 500.

This makes the Phase 1 failure reproducible without depending on external infrastructure failures.

## Expected Behavior

The healthy deployment should successfully process checkout requests.

The faulty deployment should produce a mixture of successful and failed requests under sufficient concurrent traffic.

The automated Phase 1 test therefore checks for both:

- HTTP 201 responses
- HTTP 500 responses

It does not require a fixed success/failure ratio because request scheduling can vary between runs.

## Phase 1 Completion Criteria

Phase 1 is complete when:

- checkout-service can run as version 2.4.0;
- checkout-service can run as version 2.4.1;
- the two deployments have distinct configuration;
- version 2.4.1 reproducibly produces failures under concurrent traffic;
- the healthy 2.4.0 deployment passes the normal integration suite;
- the controlled fault has an automated reproduction test.

## Relationship to Later Phases

The controlled failure introduced here becomes the basis for later observability and incident-resolution work.

Later phases will use the failure to exercise:

- metrics;
- logs;
- investigation;
- diagnosis;
- policy;
- approval;
- rollback;
- verification.
