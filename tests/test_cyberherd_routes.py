import pytest
import httpx
from fastapi import FastAPI
from ..routes import cyberherd
from ..services.database import DatabaseService
from ..services.external_api import ExternalAPIService
from ..services.notifier import NotifierService
from ..services.cyberherd_manager import CyberHerdManager
from ..models import CyberHerdData
from typing import List

@pytest.fixture
def test_app():
    app = FastAPI()
    app.include_router(cyberherd.router)
    return app

@pytest.mark.asyncio
async def test_update_cyber_herd(test_app):
    async with httpx.AsyncClient(app=test_app, base_url="http://testserver") as client:
        data = [
            {
                "pubkey": "test_pubkey",
                "event_id": "test_event_id",
                "note": "test_note",
                "kinds": [9734],
                "nprofile": "test_nprofile",
                "lud16": "test@example.com"
            }
        ]
        response = await client.post("/cyberherd/cyber_herd", json=data)
        assert response.status_code == 200
        assert response.json()["status"] == "success"

@pytest.mark.asyncio
async def test_get_cyber_herd(test_app):
    async with httpx.AsyncClient(app=test_app, base_url="http://testserver") as client:
        response = await client.get("/cyberherd/cyber_herd")
        assert response.status_code == 200

@pytest.mark.asyncio
async def test_delete_cyber_herd_member(test_app):
    async with httpx.AsyncClient(app=test_app, base_url="http://testserver") as client:
        response = await client.delete("/cyberherd/cyber_herd/test_pubkey")
        assert response.status_code == 200
        assert response.json()["status"] == "success"
