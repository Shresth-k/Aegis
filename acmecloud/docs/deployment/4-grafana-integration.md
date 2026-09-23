# Grafana Deployment

## Start the stack

From the repository root:

```bash
docker compose up -d --build
```

Check the containers:

```bash
docker compose ps
```

Grafana is exposed at:

```text
http://localhost:3000
```

Prometheus remains available at:

```text
http://localhost:9090
```

## Provisioning

Grafana receives its configuration through read-only Compose mounts:

```text
observability/grafana/provisioning
    -> /etc/grafana/provisioning

observability/grafana/dashboards
    -> /var/lib/grafana/dashboards
```

The Prometheus datasource is provisioned automatically.

The checkout dashboard is provisioned automatically under the `OpsPilot` folder.

## Verification

Verify the Grafana container:

```bash
docker compose ps grafana
```

Check Grafana logs:

```bash
docker compose logs grafana --tail=100
```

Verify the Grafana HTTP endpoint:

```bash
curl -s http://localhost:3000/api/health
```

Expected response includes:

```json
{
  "database": "ok",
  "version": "12.1.1"
}
```

Verify the Prometheus datasource from Grafana:

```bash
curl -s http://localhost:3000/api/datasources
```

Verify the provisioned dashboard:

```bash
curl -s http://localhost:3000/api/search
```

The response should contain the `OpsPilot - Checkout Service` dashboard.

## Browser verification

Open:

```text
http://localhost:3000
```

The initial Grafana login is:

```text
admin / admin
```

Change the password when Grafana prompts for it.

Open the `OpsPilot` folder and select:

```text
OpsPilot - Checkout Service
```

The panels should populate once Prometheus has scraped checkout-service.

## Fault verification

For the Phase 1 faulty deployment, start the service with:

```bash
CHECKOUT_VERSION=2.4.1 docker compose up -d --build
```

Generate concurrent checkout traffic using the existing integration test or another controlled load source.

The dashboard should show the observable effects of the fault:

- increased request latency
- increased database connection acquisition time
- checkout errors under contention
- active database connections approaching the configured pool size

The exact error ratio depends on traffic timing and concurrency and should not be treated as deterministic.

## Reset

Return to the healthy deployment:

```bash
CHECKOUT_VERSION=2.4.0 docker compose up -d --build
```
