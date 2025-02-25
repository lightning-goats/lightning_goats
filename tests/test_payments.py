import pytest
from fastapi.testclient import TestClient
from app import app

client = TestClient(app)

def test_create_payment():
    response = client.post("/payments", json={"amount": 1000, "memo": "Test Payment"})
    assert response.status_code == 200
    assert "payment_request" in response.json()

def test_get_balance():
    response = client.get("/payments/balance")
    assert response.status_code == 200
    assert "balance" in response.json()

def test_reset_wallet():
    response = client.post("/payments/reset")
    assert response.status_code == 200
    assert response.json()["success"] is True

def test_payment_hook():
    payment_data = {
        "wallet_balance": 1000,
        "payment": {
            "amount": 1000000,
            "memo": "Test Payment",
            "status": "success",
            "pending": False,
            "time": 1234567890,
            "fee": 0,
        }
    }
    response = client.post("/payments/hook", json=payment_data)
    assert response.status_code == 200
    assert response.json()["status"] == "success"
