import pytest
from fastapi.testclient import TestClient
from app import app

client = TestClient(app)

def test_get_cyberherd_list():
    response = client.get("/cyberherd")
    assert response.status_code == 200
    assert "members" in response.json()

def test_get_remaining_spots():
    response = client.get("/cyberherd/spots_remaining")
    assert response.status_code == 200
    assert "spots_remaining" in response.json()

def test_add_cyberherd_member():
    new_member = {
        "pubkey": "test_pubkey",
        "display_name": "Test User",
        "event_id": "test_event_id",
        "note": "test_note",
        "kinds": "9734",
        "nprofile": "nprofile1qqstest...",
        "lud16": "testuser@getalby.com",
        "payouts": 0.3,
        "amount": 21,
        "picture": "https://example.com/avatar.jpg"
    }
    response = client.post("/cyberherd", json=[new_member])
    assert response.status_code == 200
    assert response.json()["status"] == "success"

def test_delete_cyberherd_member():
    lud16 = "testuser@getalby.com"
    response = client.delete(f"/cyberherd/delete/{lud16}")
    assert response.status_code == 200
    assert response.json()["status"] == "success"

def test_update_cyberherd_member():
    updated_member = {
        "pubkey": "test_pubkey",
        "display_name": "Updated User",
        "event_id": "updated_event_id",
        "note": "updated_note",
        "kinds": "6,9734",
        "nprofile": "nprofile1qqstest...",
        "lud16": "testuser@getalby.com",
        "payouts": 0.5,
        "amount": 42,
        "picture": "https://example.com/avatar.jpg"
    }
    response = client.post("/cyberherd", json=[updated_member])
    assert response.status_code == 200
    assert response.json()["status"] == "success"
