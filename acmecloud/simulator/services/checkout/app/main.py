"""HTTP API for the AcmeCloud checkout service.

Short overview:
- Exposes health, checkout, and Prometheus metrics endpoints.
- Reads service metadata without requiring database configuration at import time.
- Applies deployment-controlled database delay for Phase 1 fault scenarios.
- Persists checkout orders in PostgreSQL.
- Emits structured request logs with request IDs and latency.
- Records Prometheus HTTP request and latency metrics for checkout traffic.
"""

import logging
import time
import uuid
from decimal import Decimal

from fastapi import Depends, FastAPI, HTTPException, Request
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest
from pydantic import BaseModel, Field
from sqlalchemy import text
from sqlalchemy.orm import Session
from starlette.responses import HTMLResponse, Response

from .config import get_service_settings, get_settings
from .db import get_db
from .logging import configure_logging
from .metrics import (
    CHECKOUT_ERRORS_TOTAL,
    CHECKOUT_LATENCY,
    CHECKOUT_REQUESTS_TOTAL,
)
from .models import Order

SERVICE_NAME = "checkout-service"
SERVICE_VERSION = get_service_settings().service_version

app = FastAPI(
    title="AcmeCloud Checkout Service",
    version=SERVICE_VERSION,
    description="Checkout API belonging to the simulated AcmeCloud environment.",
)

@app.get("/", response_class=HTMLResponse)
def root():
    return HTMLResponse(
        """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>AcmeCloud Checkout Microservice</title>
    <style>
        body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; background: #0b0f19; color: #f3f4f6; margin: 0; padding: 40px; display: flex; justify-content: center; align-items: center; min-height: 80vh; }
        .card { background: #111827; border: 1px solid #1f2937; border-radius: 12px; padding: 36px; max-width: 580px; width: 100%; box-shadow: 0 10px 30px rgba(0,0,0,0.6); }
        h1 { margin-top: 12px; color: #60a5fa; font-size: 24px; font-weight: 700; }
        p { color: #9ca3af; line-height: 1.6; font-size: 14px; }
        .badge { display: inline-block; padding: 4px 12px; border-radius: 9999px; font-size: 12px; font-weight: 600; background: #064e3b; color: #34d399; }
        .btn-group { margin-top: 24px; display: flex; gap: 12px; }
        .btn { display: inline-flex; align-items: center; justify-content: center; padding: 10px 20px; border-radius: 8px; background: #2563eb; color: #ffffff; text-decoration: none; font-weight: 600; font-size: 14px; cursor: pointer; border: none; }
        .btn:hover { background: #1d4ed8; }
        .btn-sec { background: #1f2937; color: #93c5fd; border: 1px solid #374151; }
        .btn-sec:hover { background: #374151; }
        .meta-box { margin-top: 24px; border-top: 1px solid #1f2937; padding-top: 16px; display: flex; justify-content: space-between; font-size: 13px; color: #6b7280; }
        .meta-box a { color: #60a5fa; text-decoration: none; }
        .meta-box a:hover { text-decoration: underline; }
    </style>
</head>
<body>
    <div class="card">
        <span class="badge">ACTIVE MICROSERVICE</span>
        <h1>AcmeCloud Checkout Service</h1>
        <p>This is the backend checkout microservice running in the cloud environment. It exposes endpoints for checkout transactions, database state, and telemetry metrics.</p>
        <p>To view the <strong>Aegis Autonomous IT Operations Mission Control UI</strong>, please navigate to port <strong>3000</strong>.</p>
        <div class="btn-group">
            <a href="#" onclick="location.port='3000'; return false;" class="btn">Open Aegis Mission Control (Port 3000)</a>
            <a href="/docs" class="btn btn-sec">API Docs (Swagger UI)</a>
        </div>
        <div class="meta-box">
            <span>Version: <strong>2.4.0</strong></span>
            <div>
                <a href="/health">Health Status</a> &bull;
                <a href="/metrics">Prometheus Metrics</a>
            </div>
        </div>
    </div>
</body>
</html>"""
    )

configure_logging()
logger = logging.getLogger(__name__)


@app.middleware("http")
async def request_logging_middleware(
    request: Request,
    call_next,
) -> Response:
    """Log and measure every application HTTP request."""
    request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
    start_time = time.perf_counter()

    # These metrics describe checkout traffic, not generic HTTP traffic.
    # Keep /health, /metrics, documentation routes, and other endpoints out
    # of the checkout request/error/latency series.
    instrument_checkout = request.method == "POST" and request.url.path == "/checkout"

    if instrument_checkout:
        CHECKOUT_REQUESTS_TOTAL.inc()

    try:
        response = await call_next(request)
    except Exception:
        duration_seconds = time.perf_counter() - start_time

        if instrument_checkout:
            CHECKOUT_ERRORS_TOTAL.inc()
            CHECKOUT_LATENCY.observe(duration_seconds)

        duration_ms = round(duration_seconds * 1000, 2)

        logger.exception(
            "Request failed",
            extra={
                "service": SERVICE_NAME,
                "version": SERVICE_VERSION,
                "request_id": request_id,
                "method": request.method,
                "path": request.url.path,
                "duration_ms": duration_ms,
                "error": "unhandled_exception",
            },
        )
        raise

    duration_seconds = time.perf_counter() - start_time

    if instrument_checkout:
        CHECKOUT_LATENCY.observe(duration_seconds)

        if response.status_code >= 500:
            CHECKOUT_ERRORS_TOTAL.inc()

    duration_ms = round(duration_seconds * 1000, 2)

    logger.info(
        "Request completed",
        extra={
            "service": SERVICE_NAME,
            "version": SERVICE_VERSION,
            "request_id": request_id,
            "method": request.method,
            "path": request.url.path,
            "status_code": response.status_code,
            "duration_ms": duration_ms,
        },
    )

    response.headers["X-Request-ID"] = request_id

    return response


class CheckoutRequest(BaseModel):
    """Request payload for creating an order."""

    customer_id: uuid.UUID
    total_amount: Decimal = Field(gt=0)
    currency: str = Field(min_length=3, max_length=3)


class CheckoutResponse(BaseModel):
    """Response returned after creating an order."""

    order_id: uuid.UUID
    status: str


@app.get("/health")
def health(db: Session = Depends(get_db)) -> dict[str, str]:
    """Return service and database health information."""
    try:
        db.execute(text("SELECT 1"))
    except Exception as exc:
        logger.exception(
            "Health check failed",
            extra={
                "service": SERVICE_NAME,
                "version": SERVICE_VERSION,
                "error": "database_unhealthy",
            },
        )
        raise HTTPException(
            status_code=503,
            detail={
                "status": "unhealthy",
                "service": SERVICE_NAME,
                "version": SERVICE_VERSION,
                "database": "unhealthy",
            },
        ) from exc

    return {
        "status": "healthy",
        "service": SERVICE_NAME,
        "version": SERVICE_VERSION,
        "database": "healthy",
    }


@app.get("/metrics")
def metrics() -> Response:
    """Expose Prometheus metrics."""
    return Response(
        content=generate_latest(),
        media_type=CONTENT_TYPE_LATEST,
    )


@app.post("/checkout", response_model=CheckoutResponse, status_code=201)
def checkout(
    request: CheckoutRequest,
    db: Session = Depends(get_db),
) -> CheckoutResponse:
    """Create and persist a basic checkout order."""
    order = Order(
        id=uuid.uuid4(),
        customer_id=request.customer_id,
        status="confirmed",
        total_amount=request.total_amount,
        currency=request.currency.upper(),
    )

    try:
        db.add(order)

        settings = get_settings()

        if settings.db_operation_delay_ms:
            db.execute(
                text("SELECT pg_sleep(:delay)"),
                {"delay": settings.db_operation_delay_ms / 1000},
            )

        db.commit()
    except Exception as exc:
        db.rollback()
        logger.exception(
            "Checkout persistence failed",
            extra={
                "service": SERVICE_NAME,
                "version": SERVICE_VERSION,
                "error": "checkout_persistence_failed",
            },
        )
        raise HTTPException(
            status_code=500,
            detail="Unable to create checkout order.",
        ) from exc

    return CheckoutResponse(
        order_id=order.id,
        status=order.status,
    )
