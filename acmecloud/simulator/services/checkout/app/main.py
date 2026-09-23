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
from starlette.responses import Response

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
