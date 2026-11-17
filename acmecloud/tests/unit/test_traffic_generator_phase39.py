"""Regression tests for the Phase 3.9 traffic integration."""

import json
from uuid import UUID

from simulator.scenarios.traffic import (
    TrafficConfig,
    TrafficGenerator,
    _checkout_payload,
    _send_checkout_request,
)


def test_checkout_payload_preserves_phase36_contract() -> None:
    """Scenario payload remains compatible with the Phase 3.6 contract."""
    first = _checkout_payload(0)
    second = _checkout_payload(0)

    assert first == second
    assert json.loads(first)["customer_id"] == "scenario-customer-0"


def test_real_sender_converts_customer_id_to_valid_uuid() -> None:
    """The real transport sends a UUID accepted by checkout-service."""
    captured: list[bytes] = []

    class Response:
        status = 201

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

    import simulator.scenarios.traffic as traffic_module

    original_urlopen = traffic_module.urllib.request.urlopen
    traffic_module.urllib.request.urlopen = lambda request, timeout: (
        captured.append(request.data) or Response()
    )
    try:
        status = _send_checkout_request(
            "http://checkout-service:8000/checkout",
            _checkout_payload(0),
            1.0,
        )
    finally:
        traffic_module.urllib.request.urlopen = original_urlopen

    assert status == 201
    payload = json.loads(captured[0])
    UUID(payload["customer_id"])


def test_traffic_generator_uses_checkout_endpoint() -> None:
    """Traffic remains POST /checkout with the corrected transport."""
    calls: list[tuple[str, bytes, float]] = []

    def sender(url: str, payload: bytes, timeout: float) -> int:
        calls.append((url, payload, timeout))
        return 200

    result = TrafficGenerator(sender=sender).generate(
        TrafficConfig(
            base_url="http://checkout-service:8000",
            requests_per_second=2,
            duration_seconds=1,
        )
    )

    assert result.requested == 2
    assert result.successful == 2
    assert result.failed == 0
    assert result.success_rate == 1.0
    assert result.errors == ()
    assert [call[0] for call in calls] == [
        "http://checkout-service:8000/checkout",
        "http://checkout-service:8000/checkout",
    ]
