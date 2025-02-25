import pytest
from fastapi.testclient import TestClient
from app import app

client = TestClient(app)

def test_payment_webhook():
    response = client.post("/webhooks/payment", json={"payment_data": {"amount": 1000}})
    assert response.status_code == 200
    assert response.json() == {"status": "success"}

def test_lnurl_webhook():
    response = client.post("/webhooks/lnurl", json={"data": {"lnurl": "test_lnurl"}})
    assert response.status_code == 200
    assert response.json() == {"status": "success"}
