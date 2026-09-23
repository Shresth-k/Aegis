import uuid
from decimal import Decimal

import pytest
from pydantic import ValidationError

from simulator.services.checkout.app.main import CheckoutRequest


def test_checkout_request_accepts_valid_payload():
    customer_id = uuid.uuid4()

    request = CheckoutRequest(
        customer_id=customer_id,
        total_amount="149.99",
        currency="usd",
    )

    assert request.customer_id == customer_id
    assert request.total_amount == Decimal("149.99")
    assert request.currency == "usd"


@pytest.mark.parametrize(
    "payload",
    [
        {
            "customer_id": str(uuid.uuid4()),
            "total_amount": "0",
            "currency": "USD",
        },
        {
            "customer_id": str(uuid.uuid4()),
            "total_amount": "-10.00",
            "currency": "USD",
        },
        {
            "customer_id": "not-a-uuid",
            "total_amount": "10.00",
            "currency": "USD",
        },
        {
            "customer_id": str(uuid.uuid4()),
            "total_amount": "10.00",
            "currency": "US",
        },
    ],
)
def test_checkout_request_rejects_invalid_payload(payload):
    with pytest.raises(ValidationError):
        CheckoutRequest(**payload)
