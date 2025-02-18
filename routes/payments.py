from fastapi import APIRouter, HTTPException, Depends
from ..services.external_api import ExternalAPIService
from ..services.database import DatabaseService
from ..config import config, TRIGGER_AMOUNT_SATS
from ..models import PaymentRequest, HookData
from ..services.cyberherd_manager import CyberHerdManager
import logging

logger = logging.getLogger(__name__)
router = APIRouter()

@router.post("/payment")
async def create_payment(payment: PaymentRequest, external_api: ExternalAPIService = Depends()):
    """Create a new Lightning payment invoice."""
    try:
        invoice = await external_api.create_invoice(
            amount=payment.balance,
            memo="Lightning Goats Payment",
            key=config['HERD_KEY']
        )
        return {"payment_request": invoice}
    except Exception as e:
        logger.error(f"Error creating payment: {e}")
        raise HTTPException(status_code=500, detail="Failed to create payment")

@router.get("/balance/trigger_amount")
async def get_trigger_amount():
    """Get the amount required to trigger the feeder."""
    return {"trigger_amount": TRIGGER_AMOUNT_SATS}

@router.get("/convert/{amount}")
async def convert_usd_to_sats(amount: float, external_api: ExternalAPIService = Depends()):
    """Convert USD amount to satoshis."""
    try:
        sats = await external_api.convert_to_sats(amount)
        return {"sats": sats}
    except Exception as e:
        logger.error(f"Error converting amount: {e}")
        raise HTTPException(status_code=500, detail="Conversion failed")

@router.get("/balance")
async def get_balance(force_refresh: bool = False, external_api: ExternalAPIService = Depends()):
    """Get current wallet balance."""
    try:
        balance = await external_api.get_balance(force_refresh)
        return {"balance": balance}
    except Exception as e:
        logger.error(f"Error getting balance: {e}")
        raise HTTPException(status_code=500, detail="Failed to get balance")

@router.post("/reset")
async def reset_wallet(external_api: ExternalAPIService = Depends()):
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
    hook_data: HookData,
    manager: CyberHerdManager = Depends()
):
    """Handle incoming payment data from webhook."""
    try:
        await manager.process_payment_data(hook_data)
        return {"status": "success"}
    except Exception as e:
        logger.error(f"Error processing payment hook: {e}")
        raise HTTPException(status_code=500, detail="Failed to process payment hook")
