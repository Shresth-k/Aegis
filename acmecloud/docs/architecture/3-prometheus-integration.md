# Phase 2.3 — Prometheus Integration

## Purpose

Phase 2.3 connects the existing checkout-service Prometheus exposition
endpoint to a real Prometheus server in the AcmeCloud Docker Compose stack.

## Data flow

```text
checkout-service
      |
      | GET /metrics
      v
Prometheus
      |
      v
Prometheus time-series database
```

Prometheus reaches the checkout service through the Docker Compose service
name `checkout-service` on port `8000`.

## Scrape configuration

The Prometheus server uses:

- scrape interval: 5 seconds
- evaluation interval: 5 seconds
- job name: `checkout-service`
- metrics path: `/metrics`
- target: `checkout-service:8000`

## Scope

This phase does not add Grafana dashboards. Dashboard work is Phase 2.4.

It also does not change checkout-service application metrics. Those were
implemented and verified in Phase 2.2.

## Operational endpoints

- Checkout metrics: `http://localhost:8000/metrics`
- Prometheus UI: `http://localhost:9090`
- Prometheus targets: `http://localhost:9090/targets`

## Verification

Start the stack:

```bash
docker compose up -d --build
```

Verify containers:

```bash
docker compose ps
```

Verify the checkout endpoint:

```bash
curl http://localhost:8000/metrics
```

Verify Prometheus is reachable:

```bash
curl -s http://localhost:9090/-/ready
```

Expected response:

```text
Prometheus Server is Ready.
```

Verify the target through the Prometheus API:

```bash
curl -s http://localhost:9090/api/v1/targets
```

The `checkout-service` target should report an `up` state.

Query a metric:

```bash
curl -s 'http://localhost:9090/api/v1/query?query=checkout_requests_total'
```

A successful response has `"status":"success"` and should contain the
checkout metric once Prometheus has completed a scrape.
