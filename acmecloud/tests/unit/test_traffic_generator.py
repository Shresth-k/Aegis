"""Unit tests for the Phase 3.6 traffic generator."""

import time

import pytest

from simulator.scenarios.traffic import (
    TrafficConfig,
    TrafficGenerator,
    TrafficGeneratorError,
)


def test_traffic_config_validates_positive_values() -> None:
    """Traffic configuration rejects non-positive values."""
    with pytest.raises(TrafficGeneratorError, match="base_url"):
        TrafficConfig(
            base_url="",
            requests_per_second=10,
        )

    with pytest.raises(TrafficGeneratorError, match="requests_per_second"):
        TrafficConfig(
            base_url="http://localhost:8000",
            requests_per_second=0,
        )

    with pytest.raises(TrafficGeneratorError, match="duration_seconds"):
        TrafficConfig(
            base_url="http://localhost:8000",
            requests_per_second=10,
            duration_seconds=0,
        )

    with pytest.raises(
        TrafficGeneratorError,
        match="request_timeout_seconds",
    ):
        TrafficConfig(
            base_url="http://localhost:8000",
            requests_per_second=10,
            request_timeout_seconds=0,
        )


def test_traffic_generator_sends_expected_number_of_requests() -> None:
    """Generated request count is derived from rate and duration."""
    requests = []

    def sender(url: str, payload: bytes, timeout: float) -> int:
        requests.append((url, payload, timeout))
        return 201

    generator = TrafficGenerator(sender=sender)

    result = generator.generate(
        TrafficConfig(
            base_url="http://localhost:8000",
            requests_per_second=5,
            duration_seconds=1,
        )
    )

    assert result.requested == 5
    assert result.completed == 5
    assert result.successful == 5
    assert result.failed == 0
    assert result.status_codes == {201: 5}
    assert result.errors == ()
    assert result.success_rate == 1.0
    assert len(requests) == 5


def test_traffic_generator_uses_checkout_endpoint_and_deterministic_payloads() -> None:
    """Requests use POST /checkout and stable request-specific payloads."""
    requests = []

    def sender(url: str, payload: bytes, timeout: float) -> int:
        requests.append((url, payload.decode(), timeout))
        return 201

    result = TrafficGenerator(sender=sender).generate(
        TrafficConfig(
            base_url="http://localhost:8000/",
            requests_per_second=3,
            duration_seconds=1,
        )
    )

    assert result.completed == 3
    assert {request[0] for request in requests} == {"http://localhost:8000/checkout"}
    assert {request[1] for request in requests} == {
        '{"customer_id": "scenario-customer-0", "total_amount": "149.99", '
        '"currency": "usd"}',
        '{"customer_id": "scenario-customer-1", "total_amount": "149.99", '
        '"currency": "usd"}',
        '{"customer_id": "scenario-customer-2", "total_amount": "149.99", '
        '"currency": "usd"}',
    }


def test_traffic_generator_counts_http_failures_without_raising() -> None:
    """HTTP error responses are recorded as outcomes."""

    def sender(url: str, payload: bytes, timeout: float) -> int:
        return 500

    result = TrafficGenerator(sender=sender).generate(
        TrafficConfig(
            base_url="http://localhost:8000",
            requests_per_second=4,
            duration_seconds=1,
        )
    )

    assert result.requested == 4
    assert result.completed == 4
    assert result.successful == 0
    assert result.failed == 4
    assert result.status_codes == {500: 4}
    assert result.errors == ()
    assert result.success_rate == 0.0


def test_traffic_generator_records_request_exceptions() -> None:
    """Transport failures are recorded instead of aborting the run."""

    def sender(url: str, payload: bytes, timeout: float) -> int:
        raise TimeoutError("request timed out")

    result = TrafficGenerator(sender=sender).generate(
        TrafficConfig(
            base_url="http://localhost:8000",
            requests_per_second=2,
            duration_seconds=1,
        )
    )

    assert result.requested == 2
    assert result.completed == 2
    assert result.successful == 0
    assert result.failed == 2
    assert result.status_codes == {}
    assert result.errors == (
        "TimeoutError: request timed out",
        "TimeoutError: request timed out",
    )


def test_traffic_generator_handles_mixed_outcomes() -> None:
    """Successful responses, HTTP failures, and transport failures coexist."""
    counter = 0

    def sender(url: str, payload: bytes, timeout: float) -> int:
        nonlocal counter
        counter += 1

        if counter == 1:
            return 201
        if counter == 2:
            return 500

        raise ConnectionError("connection refused")

    result = TrafficGenerator(sender=sender).generate(
        TrafficConfig(
            base_url="http://localhost:8000",
            requests_per_second=3,
            duration_seconds=1,
        )
    )

    assert result.requested == 3
    assert result.completed == 3
    assert result.successful == 1
    assert result.failed == 2
    assert result.status_codes == {201: 1, 500: 1}
    assert result.errors == ("ConnectionError: connection refused",)


def test_traffic_generator_is_bounded_by_duration() -> None:
    """Scheduling uses the requested duration rather than an open-ended loop."""
    sent_at = []

    def sender(url: str, payload: bytes, timeout: float) -> int:
        sent_at.append(time.monotonic())
        return 201

    start = time.monotonic()

    result = TrafficGenerator(sender=sender).generate(
        TrafficConfig(
            base_url="http://localhost:8000",
            requests_per_second=5,
            duration_seconds=0.4,
        )
    )

    elapsed = time.monotonic() - start

    assert result.requested == 2
    assert result.completed == 2
    assert len(sent_at) == 2
    assert elapsed < 1.0
