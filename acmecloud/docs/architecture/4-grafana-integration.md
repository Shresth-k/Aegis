# Grafana Integration

## Purpose

Phase 2.4 adds Grafana as the visualization layer for the observability stack.

The current flow is:

```text
checkout-service
      |
      | /metrics
      v
Prometheus :9090
      |
      | PromQL
      v
Grafana :3000
```

## Repository state

Grafana is provisioned through files committed under `observability/grafana`.

The Prometheus datasource is provisioned automatically and points to the Docker Compose service name:

```text
http://prometheus:9090
```

The checkout dashboard is provisioned from:

```text
observability/grafana/dashboards/checkout-service.json
```

## Dashboard coverage

The initial dashboard visualizes:

- checkout request rate
- checkout error rate
- checkout latency p50 and p95
- active database connections
- database connection acquisition time p50 and p95
- checkout request and error totals

The dashboard uses only metrics already produced by checkout-service in Phase 2.2.

## Design constraint

Grafana does not add application telemetry. It visualizes the Prometheus data already exposed by checkout-service.
