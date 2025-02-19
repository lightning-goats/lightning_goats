from fastapi import APIRouter, HTTPException, Depends
from services.external_api import ExternalAPIService
from services.database import DatabaseService
from models import SetGoatSatsData
import logging

logger = logging.getLogger(__name__)
router = APIRouter()

@router.get("/feeder_status")
async def get_feeder_status(external_api: ExternalAPIService = Depends()):
    """Check if feeder override is enabled."""
    try:
        status = await external_api.get_feeder_status()
        return {"feeder_override_enabled": status}
    except Exception as e:
        logger.error(f"Error checking feeder status: {e}")
        raise HTTPException(status_code=500, detail="Failed to check feeder status")

@router.post("/feeder/trigger")
async def trigger_feeder(external_api: ExternalAPIService = Depends()):
    """Manually trigger the feeder."""
    try:
        if await external_api.get_feeder_status():
            raise HTTPException(status_code=400, detail="Feeder override is enabled")
        
        success = await external_api.trigger_feeder()
        if success:
            return {"status": "success", "message": "Feeder triggered"}
        raise HTTPException(status_code=500, detail="Failed to trigger feeder")
    except Exception as e:
        logger.error(f"Error triggering feeder: {e}")
        raise HTTPException(status_code=500, detail="Failed to trigger feeder")

@router.get("/goat_sats/sum_today")
async def get_goat_sats_sum(external_api: ExternalAPIService = Depends()):
    """Get total sats received today."""
    try:
        return await external_api.get_goat_sats_sum_today()
    except Exception as e:
        logger.error(f"Error getting goat sats sum: {e}")
        raise HTTPException(status_code=500, detail="Failed to get goat sats sum")

@router.put("/goat_sats/set")
async def set_goat_sats(data: SetGoatSatsData, external_api: ExternalAPIService = Depends()):
    """Set the goat sats counter."""
    try:
        await external_api.update_goat_sats(data.new_amount)
        return {"status": "success", "new_amount": data.new_amount}
    except Exception as e:
        logger.error(f"Error setting goat sats: {e}")
        raise HTTPException(status_code=500, detail="Failed to set goat sats")

@router.get("/goat_sats/feedings")
async def get_goat_feedings(external_api: ExternalAPIService = Depends()):
    """Get the number of goat feedings today."""
    try:
        feedings = await external_api.get_goat_feedings()
        return {"goat_feedings": feedings}
    except Exception as e:
        logger.error(f"Error getting goat feedings: {e}")
        raise HTTPException(status_code=500, detail="Failed to get goat feedings")

@router.get("/cyberherd/spots_remaining")
async def get_cyberherd_spots(database: DatabaseService = Depends()):
    """Get remaining spots in the CyberHerd."""
    try:
        result = await database.fetch_one(
            "SELECT COUNT(*) as count FROM cyber_herd"
        )
        spots_remaining = MAX_HERD_SIZE - result['count']
        return {"spots_remaining": spots_remaining}
    except Exception as e:
        logger.error(f"Error getting spots remaining: {e}")
        raise HTTPException(status_code=500, detail="Failed to get spots remaining")
