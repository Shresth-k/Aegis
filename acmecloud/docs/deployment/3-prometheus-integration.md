# Phase 2.3 — Prometheus Deployment

## Compose service

Prometheus is added as the `prometheus` service in `docker-compose.yml`.

Configuration is mounted read-only from:

```text
observability/prometheus/prometheus.yml
```

Prometheus data is stored in the named Docker volume:

```text
prometheus_data
```

The host port is:

```text
9090
```

## Start

```bash
docker compose up -d --build
```

## Verify

```bash
docker compose ps
```

Then:

```bash
curl -s http://localhost:9090/-/ready
```

and:

```bash
curl -s http://localhost:9090/api/v1/targets
```

The checkout target should be healthy after the first successful scrape.

## Troubleshooting

If the target is down, inspect:

```bash
docker compose logs prometheus --tail=100
```

and verify that checkout is reachable from the Prometheus container:

```bash
docker exec acmecloud-prometheus   wget -qO- http://checkout-service:8000/metrics
```

Do not use `localhost:8000` inside the Prometheus container. `localhost`
would refer to the Prometheus container itself; Docker Compose service
discovery requires `checkout-service:8000`.
