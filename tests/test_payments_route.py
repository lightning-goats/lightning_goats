import pytest
import httpx
from fastapi import FastAPI
from ..routes import payments
from ..services.external_api import ExternalAPIService
from ..services.database import DatabaseService
from ..config import config
from unittest.mock import AsyncMock

@pytest.fixture
def test_app():
    app = FastAPI()
    app.include_router(payments.router)
    return app

@pytest.mark.asyncio
async def test_create_payment(test_app, mock_external_api_service):
    mock_external_api_service.create_invoice.return_value = "test_payment_request"
    async with httpx.AsyncClient(app=test_app, base_url="http://testserver") as client:
        response = await client.post("/payments/payment", json={"balance": 1000})
        assert response.status_code == 200
        assert response.json() == {"payment_request": "test_payment_request"}
        mock_external_api_service.create_invoice.assert_called_once_with(
            amount=1000, memo="Lightning Goats Payment", key=config['HERD_KEY']
        )

@pytest.mark.asyncio
async def test_get_balance(test_app, mock_external_api_service):
    mock_external_api_service.get_balance.return_value = 5000
    async with httpx.AsyncClient(app=test_app, base_url="http://testserver") as client:
        response = await client.get("/payments/balance")
        assert response.status_code == 200
        assert response.json() == {"balance": 5000}
        mock_external_api_service.get_balance.assert_called_once_with(False)

@pytest.mark.asyncio
async def test_reset_wallet(test_app, mock_external_api_service):
    mock_external_api_service.get_balance.return_value = 1000
    mock_external_api_service.create_invoice.return_value = "test_payment_request"
    mock_external_api_service.pay_invoice.return_value = {"status": "success"}
    async with httpx.AsyncClient(app=test_app, base_url="http://testserver") as client:
        response = await client.post("/payments/reset")
        assert response.status_code == 200
        assert response.json() == {"success": True, "data": {"status": "success"}}
        mock_external_api_service.get_balance.assert_called_once_with(force_refresh=True)
        mock_external_api_service.create_invoice.assert_called_once_with(
            amount=1000, memo="Reset Herd Wallet", key=config['HERD_KEY']
        )
        mock_external_api_service.pay_invoice.assert_called_once_with(
            payment_request="test_payment_request", key=config['HERD_KEY']
        )

@pytest.mark.asyncio
async def test_reset_wallet_no_balance(test_app, mock_external_api_service):
    mock_external_api_service.get_balance.return_value = 0
    async with httpx.AsyncClient(app=test_app, base_url="http://testserver") as client:
        response = await client.post("/payments/reset")
        assert response.status_code == 200
        assert response.json() == {"success": True, "message": "No balance to reset"}
        mock_external_api_service.get_balance.assert_called_once_with(force_refresh=True)
        mock_external_api_service.create_invoice.assert_not_called()
        mock_external_api_service.pay_invoice.assert_not_called()

@pytest.mark.asyncio
async def test_payment_hook(test_app, mock_cyberherd_manager):
    mock_cyberherd_manager.process_payment_data.return_value = None
    async with httpx.AsyncClient(app=test_app, base_url="http://testserver") as client:
        response = await client.post(
            "/payments/hook", json={"payment_hash": "test_event_id", "amount": 100}
        )
        assert response.status_code == 200
        assert response.json() == {"status": "success"}
        mock_cyberherd_manager.process_payment_data.assert_called_once()
