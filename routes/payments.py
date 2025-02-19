from fastapi import APIRouter, HTTPException, Depends
from dependencies import get_external_api, get_cyberherd_manager
from services.external_api import ExternalAPIService
from config import config, TRIGGER_AMOUNT_SATS
from models import PaymentRequest, CyberHerdTreats
import logging
from pydantic import BaseModel

logger = logging.getLogger(__name__)
router = APIRouter()

class PaymentCreate(BaseModel):
    amount: int
    memo: str = "Lightning Goats Payment"

@router.post("")
async def create_payment(
    payment: PaymentCreate,
    external_api: ExternalAPIService = Depends(get_external_api)
):
    """Create a new payment invoice."""
    try:
        payment_request = await external_api.create_invoice(
            amount=payment.amount,
            memo=payment.memo,
            key=config['HERD_KEY']
        )
        return {"payment_request": payment_request}
    except Exception as e:
        logger.error(f"Error creating payment: {e}")
        raise HTTPException(status_code=500, detail="Failed to create payment")

@router.get("/balance/trigger_amount")
async def get_trigger_amount():
    """Get the amount required to trigger the feeder."""
    return {"trigger_amount": TRIGGER_AMOUNT_SATS}

@router.get("/convert/{amount}")
async def convert_usd_to_sats(
    amount: float,
    external_api: ExternalAPIService = Depends(get_external_api)
):
    """Convert USD amount to satoshis."""
    try:
        sats = await external_api.convert_to_sats(amount)
        return {"sats": sats}
    except Exception as e:
        logger.error(f"Error converting amount: {e}")
        raise HTTPException(status_code=500, detail="Conversion failed")

@router.get("/balance")
async def get_balance(
    force_refresh: bool = False,
    external_api = Depends(get_external_api)  # Update to use dependency
):
    """Get current wallet balance."""
    try:
        balance = await external_api.get_balance(force_refresh)
        return {"balance": balance}
    except Exception as e:
        logger.error(f"Error getting balance: {e}")
        raise HTTPException(status_code=500, detail="Failed to get balance")

@router.post("/reset")
async def reset_wallet(
    external_api = Depends(get_external_api)  # Update to use dependency
):
    """Reset wallet by sending remaining balance."""
    try:
        balance = await external_api.get_balance(force_refresh=True)
        if balance > 0:
            payment_request = await external_api.create_invoice(
                amount=balance,
                memo='Reset Herd Wallet',
                key=config['HERD_KEY']
            )
            payment_status = await external_api.pay_invoice(
                payment_request=payment_request,
                key=config['HERD_KEY']
            )
            return {"success": True, "data": payment_status}
        return {"success": True, "message": "No balance to reset"}
    except Exception as e:
        logger.error(f"Error resetting wallet: {e}")
        raise HTTPException(status_code=500, detail="Failed to reset wallet")

@router.post("/hook")
async def payment_hook(
    payment_data: dict,
    manager = Depends(get_cyberherd_manager)
):
    """Handle incoming payment data from webhook."""
    try:
        if config['DEBUG']:
            logger.debug(f"Received webhook data: {payment_data}")
            
        await manager.process_payment_data(payment_data)
        
        if config['DEBUG']:
            logger.debug("Successfully processed payment hook")
            
        return {"status": "success"}
    except Exception as e:
        logger.error(f"Error processing payment hook: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to process payment hook")
