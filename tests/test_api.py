import pytest
from fastapi.testclient import TestClient
from app import app

client = TestClient(app)

def test_get_balance():
    response = client.get("/balance")
    assert response.status_code == 200
    assert "balance" in response.json()

def test_get_cyberherd_spots():
    response = client.get("/cyberherd/spots_remaining")
    assert response.status_code == 200
    assert "spots_remaining" in response.json()

def test_get_trigger_amount():
    response = client.get("/status/trigger")
    assert response.status_code == 200
    assert "trigger_amount" in response.json()

def test_create_payment():
    response = client.post("/debug/simulate_payment", json={"amount": 1000, "memo": "test payment"})
    assert response.status_code == 200
    assert "status" in response.json()
    assert response.json()["status"] == "success"

def test_convert_usd_to_sats():
    response = client.get("/convert/1.0")
    assert response.status_code == 200
    assert "sats" in response.json()
