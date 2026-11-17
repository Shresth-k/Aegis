import uuid
from decimal import Decimal

import psycopg
import pytest
from httpx import Client

BASE_URL = "http://localhost:8000"
DATABASE_URL = "postgresql://acmecloud:acmecloud@localhost:5432/acmecloud"


@pytest.fixture
def client():
    with Client(base_url=BASE_URL) as client:
        yield client


def test_health(client):
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {
        "status": "healthy",
        "service": "checkout-service",
        "version": "2.4.0",
        "database": "healthy",
    }


def test_checkout_creates_order(client):
    customer_id = uuid.uuid4()

    response = client.post(
        "/checkout",
        json={
            "customer_id": str(customer_id),
            "total_amount": "149.99",
            "currency": "usd",
        },
    )

    assert response.status_code == 201

    body = response.json()

    assert body["status"] == "confirmed"
    assert "order_id" in body

    order_id = uuid.UUID(body["order_id"])

    with psycopg.connect(DATABASE_URL) as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT customer_id, status, total_amount, currency
                FROM orders
                WHERE id = %s
                """,
                (order_id,),
            )

            row = cursor.fetchone()

    assert row is not None
    assert row[0] == customer_id
    assert row[1] == "confirmed"
    assert row[2] == Decimal("149.99")
    assert row[3] == "USD"


@pytest.mark.parametrize(
    "payload",
    [
        {
            "customer_id": "not-a-uuid",
            "total_amount": "149.99",
            "currency": "USD",
        },
        {
            "customer_id": str(uuid.uuid4()),
            "total_amount": "0",
            "currency": "USD",
        },
        {
            "customer_id": str(uuid.uuid4()),
            "total_amount": "149.99",
            "currency": "US",
        },
    ],
)
def test_checkout_rejects_invalid_payload(client, payload):
    response = client.post("/checkout", json=payload)

    assert response.status_code == 422
