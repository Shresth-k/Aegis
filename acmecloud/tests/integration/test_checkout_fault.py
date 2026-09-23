"""Integration test for the Phase 1 controlled checkout fault."""

import concurrent.futures
import os
import uuid

import httpx
import pytest

BASE_URL = os.getenv("CHECKOUT_TEST_BASE_URL", "http://localhost:8000")
FAULTY_VERSION = "2.4.1"
REQUEST_COUNT = 20


def _checkout(_: int) -> int:
    """Send one checkout request and return its HTTP status."""
    payload = {
        "customer_id": str(uuid.uuid4()),
        "total_amount": "149.99",
        "currency": "usd",
    }

    try:
        response = httpx.post(
            f"{BASE_URL}/checkout",
            json=payload,
            timeout=5.0,
        )
    except httpx.HTTPError as exc:
        pytest.fail(f"Checkout request failed without an HTTP response: {exc}")

    return response.status_code


def test_phase_1_fault_reproduces_checkout_failures():
    """Verify faulty deployment produces both successful and failed requests."""
    health = httpx.get(f"{BASE_URL}/health", timeout=5.0)
    health.raise_for_status()

    health_data = health.json()

    if health_data["version"] != FAULTY_VERSION:
        pytest.skip(
            f"Phase 1 fault test requires checkout-service "
            f"{FAULTY_VERSION}; running {health_data['version']}."
        )

    assert health_data["status"] == "healthy"
    assert health_data["database"] == "healthy"

    with concurrent.futures.ThreadPoolExecutor(max_workers=REQUEST_COUNT) as executor:
        results = list(executor.map(_checkout, range(REQUEST_COUNT)))

    assert len(results) == REQUEST_COUNT
    assert all(status in {201, 500} for status in results)
    assert 201 in results
    assert 500 in results
