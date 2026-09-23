"""Prometheus metrics for the AcmeCloud checkout service."""

from prometheus_client import Counter, Gauge, Histogram

CHECKOUT_REQUESTS_TOTAL = Counter(
    "checkout_requests_total",
    "Total number of checkout HTTP requests.",
)

CHECKOUT_ERRORS_TOTAL = Counter(
    "checkout_errors_total",
    "Total number of failed checkout HTTP requests.",
)

CHECKOUT_LATENCY = Histogram(
    "checkout_latency",
    "Checkout HTTP request latency in seconds.",
)

DB_CONNECTIONS_ACTIVE = Gauge(
    "db_connections_active",
    "Currently checked-out database connections.",
)

DB_CONNECTION_WAIT_TIME = Histogram(
    "db_connection_wait_time",
    "Time spent waiting for a checkout database connection in seconds.",
)
