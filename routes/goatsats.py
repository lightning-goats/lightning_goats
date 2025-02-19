from fastapi import APIRouter, HTTPException, Depends
from services.external_api import ExternalAPIService
from dependencies import get_external_api
from models import SetGoatSatsData
import logging

logger = logging.getLogger(__name__)
router = APIRouter()

@router.get("/sum_today")
async def get_goat_sats_sum_today(
    external_api: ExternalAPIService = Depends(get_external_api)
):
    """Get total goat sats for today."""
    return await external_api.get_goat_sats_sum_today()

@router.get("/feedings")
async def get_goat_feedings(
    external_api: ExternalAPIService = Depends(get_external_api)
):
    """Get total goat feedings."""
    feedings = await external_api.get_goat_feedings()
    return {"goat_feedings": feedings}

@router.put("/set")
async def set_goat_sats(
    data: SetGoatSatsData,
    external_api: ExternalAPIService = Depends(get_external_api)
):
    """Set goat sats to a specific value."""
    try:
        new_state = await external_api.update_goat_sats(data.new_amount)
        return {"status": "success", "new_state": new_state}
    except Exception as e:
        logger.error(f"Error setting goat sats: {e}")
        raise HTTPException(status_code=500, detail="Failed to set goat sats")
