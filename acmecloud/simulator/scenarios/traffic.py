"""Deterministic HTTP traffic generation for Scenario Engine runs."""

from __future__ import annotations

import json
import time
import urllib.error
import urllib.request
import uuid
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from typing import Protocol


class TrafficGeneratorError(ValueError):
    """Raised when traffic configuration is invalid."""


@dataclass(frozen=True)
class TrafficConfig:
    """Configuration for one bounded traffic run."""

    base_url: str
    requests_per_second: int
    duration_seconds: float = 1.0
    request_timeout_seconds: float = 5.0

    def __post_init__(self) -> None:
        """Validate traffic configuration."""
        if not self.base_url.strip():
            raise TrafficGeneratorError("base_url is required")
        if self.requests_per_second <= 0:
            raise TrafficGeneratorError("requests_per_second must be positive")
        if self.duration_seconds <= 0:
            raise TrafficGeneratorError("duration_seconds must be positive")
        if self.request_timeout_seconds <= 0:
            raise TrafficGeneratorError("request_timeout_seconds must be positive")


@dataclass(frozen=True)
class TrafficResult:
    """Outcome of one bounded traffic run."""

    requested: int
    completed: int
    successful: int
    failed: int
    status_codes: dict[int, int]
    errors: tuple[str, ...]

    @property
    def success_rate(self) -> float:
        """Return the fraction of completed requests that succeeded."""
        if self.completed == 0:
            return 0.0
        return self.successful / self.completed


class RequestSender(Protocol):
    """Protocol for sending one checkout request."""

    def __call__(
        self,
        url: str,
        payload: bytes,
        timeout: float,
    ) -> int:
        """Send a request and return its HTTP status code."""


class TrafficGenerator:
    """Generate deterministic bounded POST /checkout traffic."""

    def __init__(self, sender: RequestSender | None = None) -> None:
        """Create a generator with an optional injectable request sender."""
        self._sender = sender or _send_checkout_request

    def generate(self, config: TrafficConfig) -> TrafficResult:
        """Generate the configured number of checkout requests."""
        total_requests = round(config.requests_per_second * config.duration_seconds)
        max_workers = min(
            total_requests,
            max(config.requests_per_second * 2, 1),
        )

        start = time.monotonic()
        futures = {}

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            for request_number in range(total_requests):
                target_time = start + (request_number / config.requests_per_second)
                sleep_for = target_time - time.monotonic()
                if sleep_for > 0:
                    time.sleep(sleep_for)

                payload = _checkout_payload(request_number)
                future = executor.submit(
                    self._sender,
                    f"{config.base_url.rstrip('/')}/checkout",
                    payload,
                    config.request_timeout_seconds,
                )
                futures[future] = request_number

            outcomes: list[tuple[int, int | None, str | None]] = []

            for future in as_completed(futures):
                request_number = futures[future]
                try:
                    status_code = future.result()
                except Exception as exc:
                    outcomes.append(
                        (
                            request_number,
                            None,
                            f"{type(exc).__name__}: {exc}",
                        )
                    )
                else:
                    outcomes.append((request_number, status_code, None))

        outcomes.sort(key=lambda outcome: outcome[0])

        status_codes = Counter(
            status_code for _, status_code, error in outcomes if status_code is not None
        )
        errors = tuple(error for _, _, error in outcomes if error is not None)
        successful = sum(
            status_code is not None and 200 <= status_code < 400
            for _, status_code, _ in outcomes
        )

        return TrafficResult(
            requested=total_requests,
            completed=len(outcomes),
            successful=successful,
            failed=len(outcomes) - successful,
            status_codes=dict(status_codes),
            errors=errors,
        )


def _checkout_payload(request_number: int) -> bytes:
    """Build the deterministic Phase 3.6 checkout payload."""
    payload = {
        "customer_id": f"scenario-customer-{request_number}",
        "total_amount": "149.99",
        "currency": "usd",
    }
    return json.dumps(payload).encode("utf-8")


def _send_checkout_request(
    url: str,
    payload: bytes,
    timeout: float,
) -> int:
    """Send one checkout request with a UUID accepted by the real API."""
    request_payload = json.loads(payload)
    customer_id = request_payload["customer_id"]

    if customer_id.startswith("scenario-customer-"):
        request_number = customer_id.removeprefix("scenario-customer-")
        request_payload["customer_id"] = str(
            uuid.uuid5(
                uuid.NAMESPACE_URL,
                f"opspilot-scenario-customer-{request_number}",
            )
        )

    body = json.dumps(request_payload).encode("utf-8")
    request = urllib.request.Request(
        url,
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return response.status
    except urllib.error.HTTPError as exc:
        return exc.code
