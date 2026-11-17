"""Integration tests for checkout-service Prometheus metrics."""

import os
import uuid

import httpx
import pytest

BASE_URL = os.getenv("CHECKOUT_TEST_BASE_URL", "http://localhost:8000")


def _metrics() -> str:
    """Return the current Prometheus exposition output."""
    response = httpx.get(f"{BASE_URL}/metrics", timeout=5.0)
    response.raise_for_status()
    return response.text


def _metric_value(metrics: str, name: str) -> float:
    """Extract a plain Prometheus metric value."""
    for line in metrics.splitlines():
        if line.startswith(f"{name} "):
            return float(line.split()[-1])
    pytest.fail(f"Metric {name!r} was not found.")


def _checkout() -> httpx.Response:
    """Create one valid checkout order."""
    payload = {
        "customer_id": str(uuid.uuid4()),
        "total_amount": "49.99",
        "currency": "usd",
    }

    return httpx.post(
        f"{BASE_URL}/checkout",
        json=payload,
        timeout=5.0,
    )


def test_checkout_metrics_are_exposed():
    """Verify the checkout and database metrics are exposed."""
    response = httpx.get(f"{BASE_URL}/health", timeout=5.0)
    response.raise_for_status()

    metrics = _metrics()

    assert "checkout_requests_total" in metrics
    assert "checkout_errors_total" in metrics
    assert "checkout_latency" in metrics
    assert "db_connections_active" in metrics
    assert "db_connection_wait_time" in metrics


def test_checkout_request_updates_checkout_metrics():
    """Verify a checkout request increments the checkout request counter."""
    before = _metrics()

    response = _checkout()
    response.raise_for_status()

    after = _metrics()

    assert _metric_value(after, "checkout_requests_total") == (
        _metric_value(before, "checkout_requests_total") + 1
    )


def test_health_request_does_not_update_checkout_metrics():
    """Verify health traffic is excluded from checkout request metrics."""
    before = _metrics()

    response = httpx.get(f"{BASE_URL}/health", timeout=5.0)
    response.raise_for_status()

    after = _metrics()

    assert _metric_value(after, "checkout_requests_total") == _metric_value(
        before,
        "checkout_requests_total",
    )
