from fastapi import APIRouter, HTTPException, Depends
from services.external_api import ExternalAPIService
from dependencies import get_external_api
import logging

logger = logging.getLogger(__name__)
router = APIRouter()

@router.get("/status")
async def feeder_status(
    external_api: ExternalAPIService = Depends(get_external_api)
):
    """Get feeder override status."""
    try:
        status = await external_api.get_feeder_status()
        return {"feeder_override_enabled": status}
    except Exception as e:
        logger.error(f"Error getting feeder status: {e}")
        raise HTTPException(status_code=500, detail="Failed to get feeder status")

@router.post("/trigger")
async def trigger_feeder(
    external_api: ExternalAPIService = Depends(get_external_api)
):
    """Manually trigger the feeder."""
    try:
        success = await external_api.trigger_feeder()
        if success:
            return {"status": "success", "message": "Feeder triggered successfully"}
        raise HTTPException(status_code=500, detail="Failed to trigger feeder")
    except Exception as e:
        logger.error(f"Error triggering feeder: {e}")
        raise HTTPException(status_code=500, detail="Failed to trigger feeder")
