from fastapi.testclient import TestClient


def test_stripe_webhook_charge_failed(client: TestClient):
    payload = {
        "id": "evt_stripe_fail_01",
        "type": "charge.failed",
        "data": {
            "object": {
                "id": "ch_stripe_fail_01",
                "customer": "cus_stripe_123",
                "customer_name": "Sarah Connor",
                "customer_email": "sarah@cyberdyne.demo",
                "amount": 4900,
                "currency": "usd",
                "failure_code": "insufficient_funds",
                "failure_message": "Card has insufficient funds",
                "payment_method_details": {"card": {"brand": "visa"}},
            }
        },
    }
    response = client.post("/api/webhooks/stripe", json=payload)
    assert response.status_code == 200
    assert response.json()["accepted"] is True

    # Duplicate should be safely ignored
    dup = client.post("/api/webhooks/stripe", json=payload)
    assert dup.status_code == 200
    assert "duplicate" in dup.json()["message"].lower()

    # Verify case was ingested
    cases = client.get("/api/cases").json()["items"]
    matching = [c for c in cases if c["customer_name"] == "Sarah Connor"]
    assert len(matching) == 1
    assert matching[0]["amount"] == 49.0
    assert matching[0]["gateway"] == "stripe"


def test_stripe_webhook_payment_succeeded(client: TestClient):
    # First fail a charge
    fail_payload = {
        "id": "evt_stripe_fail_02",
        "type": "charge.failed",
        "data": {
            "object": {
                "id": "ch_stripe_succ_01",
                "customer": "cus_stripe_456",
                "customer_name": "John Matrix",
                "amount": 9900,
                "currency": "usd",
            }
        },
    }
    client.post("/api/webhooks/stripe", json=fail_payload)

    # Next send invoice.payment_succeeded
    succ_payload = {
        "id": "evt_stripe_succ_01",
        "type": "invoice.payment_succeeded",
        "data": {
            "object": {
                "id": "inv_stripe_01",
                "payment_intent": "ch_stripe_succ_01",
            }
        },
    }
    response = client.post("/api/webhooks/stripe", json=succ_payload)
    assert response.status_code == 200
    assert response.json()["accepted"] is True


def test_paddle_webhook_payment_failed(client: TestClient):
    payload = {
        "event_id": "p_evt_001",
        "event_type": "subscription_payment_failed",
        "data": {
            "customer_id": "p_cust_999",
            "email": "paddle_user@example.com",
            "amount": 199.0,
            "currency": "USD",
            "transaction_id": "p_tx_999",
            "error_code": "insufficient_funds",
        },
    }
    response = client.post("/api/webhooks/paddle", json=payload)
    assert response.status_code == 200
    assert response.json()["accepted"] is True

    # Duplicate
    dup = client.post("/api/webhooks/paddle", json=payload)
    assert dup.status_code == 200
    assert "duplicate" in dup.json()["message"].lower()


def test_braintree_webhook_declined(client: TestClient):
    payload = {
        "event_id": "bt_evt_001",
        "kind": "subscription_charged_unsuccessfully",
        "customer_id": "bt_cust_111",
        "amount": 75.0,
        "currency": "USD",
        "transaction_id": "bt_tx_111",
        "message": "Processor Declined",
    }
    response = client.post("/api/webhooks/braintree", json=payload)
    assert response.status_code == 200
    assert response.json()["accepted"] is True
