import pytest
from fastapi.testclient import TestClient
from app import app

client = TestClient(app)

def test_get_feeder_status():
    response = client.get("/status/feeder")
    assert response.status_code == 200
    assert "feeder_override_enabled" in response.json()

def test_trigger_feeder():
    response = client.post("/status/feeder/trigger")
    assert response.status_code == 200
    assert response.json()["status"] == "success"

def test_get_goat_sats_sum():
    response = client.get("/status/goat_sats/sum_today")
    assert response.status_code == 200
    assert "total_sats" in response.json()

def test_set_goat_sats():
    new_amount = 1000
    response = client.put("/status/goat_sats/set", json={"new_amount": new_amount})
    assert response.status_code == 200
    assert response.json()["status"] == "success"
    assert response.json()["new_amount"] == new_amount

def test_get_goat_feedings():
    response = client.get("/status/goat_sats/feedings")
    assert response.status_code == 200
    assert "goat_feedings" in response.json()

def test_get_cyberherd_spots():
    response = client.get("/status/cyberherd/spots_remaining")
    assert response.status_code == 200
    assert "spots_remaining" in response.json()

def test_get_trigger_amount():
    response = client.get("/status/trigger")
    assert response.status_code == 200
    assert "trigger_amount" in response.json()
