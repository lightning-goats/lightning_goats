from fastapi import APIRouter, HTTPException, Depends
from services.external_api import ExternalAPIService
from dependencies import get_external_api
import logging

logger = logging.getLogger(__name__)
router = APIRouter()

@router.get("/{amount}")
async def convert(
    amount: float,
    external_api: ExternalAPIService = Depends(get_external_api)
):
    """Convert USD amount to satoshis."""
    try:
        sats = await external_api.convert_to_sats(amount)
        return {"sats": sats}
    except Exception as e:
        logger.error(f"Error converting USD to sats: {e}")
        raise HTTPException(status_code=500, detail="Failed to convert amount")
