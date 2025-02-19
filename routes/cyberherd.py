from fastapi import APIRouter, HTTPException, Depends
from typing import List, Dict
import logging
from models import CyberHerdData, CyberHerdTreats
from services.database import DatabaseService
from services.external_api import ExternalAPIService
from services.notifier import NotifierService
from services.cyberherd_manager import CyberHerdManager
from config import config, MAX_HERD_SIZE
from dependencies import (
    get_db,
    get_external_api,
    get_notifier,
    get_cyberherd_manager
)

logger = logging.getLogger(__name__)
router = APIRouter()

@router.get("")
async def get_cyber_herd(
    external_api: ExternalAPIService = Depends(get_external_api)
):
    """Get list of current CyberHerd members."""
    try:
        members = await external_api.fetch_cyberherd_targets()
        return {"members": members}
    except Exception as e:
        logger.error(f"Error getting CyberHerd members: {e}")
        raise HTTPException(status_code=500, detail="Failed to get CyberHerd members")

@router.post("")
async def update_cyber_herd(
    data: List[CyberHerdData],
    db: DatabaseService = Depends(get_db),
    external_api: ExternalAPIService = Depends(get_external_api),
    notifier: NotifierService = Depends(get_notifier)
):
    """Update CyberHerd with new members."""
    try:
        query = "SELECT COUNT(*) as count FROM cyber_herd"
        result = await db.fetch_one(query)
        current_herd_size = result['count']

        if current_herd_size >= MAX_HERD_SIZE:
            logger.info(f"Herd full: {current_herd_size} members")
            return {"status": "herd full"}

        # Process each member
        # ... implement member processing logic ...

        return {"status": "success"}
    except Exception as e:
        logger.error(f"Failed to update cyber herd: {e}")
        raise HTTPException(status_code=500, detail="Internal Server Error")

@router.get("/spots_remaining")
async def get_cyberherd_spots_remaining(db: DatabaseService = Depends(get_db)):
    """Get remaining spots in CyberHerd."""
    try:
        query = "SELECT COUNT(*) as count FROM cyber_herd"
        result = await db.fetch_one(query)
        current_spots_taken = result['count']
        spots_remaining = MAX_HERD_SIZE - current_spots_taken
        return {"spots_remaining": spots_remaining}
    except Exception as e:
        logger.error(f"Error retrieving remaining spots: {e}")
        raise HTTPException(status_code=500, detail="Internal Server Error")

@router.delete("/delete/{lud16}")
async def delete_cyber_herd(
    lud16: str,
    db: DatabaseService = Depends(get_db)
):
    """Delete a CyberHerd member by lud16."""
    try:
        logger.info(f"Attempting to delete record with lud16: {lud16}")
        select_query = "SELECT * FROM cyber_herd WHERE lud16 = :lud16"
        record = await db.fetch_one(select_query, {"lud16": lud16})
        
        if not record:
            logger.warning(f"No record found with lud16: {lud16}")
            raise HTTPException(status_code=404, detail="Record not found")
            
        delete_query = "DELETE FROM cyber_herd WHERE lud16 = :lud16"
        await db.execute(delete_query, {"lud16": lud16})
        
        logger.info(f"Record with lud16 {lud16} deleted successfully.")
        return {
            "status": "success",
            "message": f"Record with lud16 {lud16} deleted successfully."
        }
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"Failed to delete record: {e}")
        raise HTTPException(status_code=500, detail="Internal Server Error")

@router.post("/messages/cyberherd_treats")
async def handle_cyberherd_treats(
    data: CyberHerdTreats,
    database: DatabaseService = Depends(get_db),
    notifier: NotifierService = Depends(get_notifier)
):
    """Send treats to CyberHerd members."""
    try:
        member = await database.fetch_one(
            "SELECT * FROM cyber_herd WHERE pubkey = :pubkey",
            {"pubkey": data.pubkey}
        )
        
        if member:
            await notifier.send_cyberherd_notification(
                member,
                difference=0,
                spots_remaining=0
            )
            return {"status": "success"}
        return {"status": "error", "message": "Member not found"}
    except Exception as e:
        logger.error(f"Error handling cyberherd treats: {e}")
        raise HTTPException(status_code=500, detail="Failed to handle treats")

@router.post("/reset")
async def reset_cyber_herd(manager: CyberHerdManager = Depends(get_cyberherd_manager)):
    """Reset the CyberHerd and redistribute rewards."""
    try:
        # Get current balance before reset
        balance = await manager.external_api.get_balance(force_refresh=True)
        
        # Distribute rewards if there's a balance
        if balance > 0:
            await manager.distribute_rewards(balance)

        # Reset the CyberHerd table
        await manager.database.execute("DELETE FROM cyber_herd")
        
        # Reset the LNbits targets
        await manager.external_api.reset_cyberherd_targets()

        return {
            "status": "success",
            "message": "CyberHerd reset successfully"
        }
    except Exception as e:
        logger.error(f"Error resetting CyberHerd: {e}")
        raise HTTPException(status_code=500, detail="Failed to reset CyberHerd")

@router.post("/distribute_rewards")
async def distribute_cyberherd_rewards(manager: CyberHerdManager = Depends(get_cyberherd_manager)):
    """Manually trigger reward distribution."""
    try:
        balance = await manager.external_api.get_balance(force_refresh=True)
        if balance > 0:
            await manager.distribute_rewards(balance)
            return {"status": "success", "distributed_amount": balance}
        return {"status": "success", "message": "No balance to distribute"}
    except Exception as e:
        logger.error(f"Error distributing rewards: {e}")
        raise HTTPException(status_code=500, detail="Failed to distribute rewards")

@router.post("/lnurl/pay/{lud16}")
async def zap_lud16_endpoint(
    lud16: str, 
    sats: int = 1, 
    text: str = "CyberHerd Treats.",
    external_api: ExternalAPIService = Depends(get_external_api)
):
    """Send LNURL payment to a specified address."""
    try:
        msat_amount = sats * 1000
        response = await external_api.make_lnurl_payment(
            lud16=lud16,
            msat_amount=msat_amount,
            description=text,
            key=config['HERD_KEY']
        )
        
        if response:
            return {"status": "success", "result": response}
        raise HTTPException(status_code=500, detail="Failed to LNURL pay.")
    except Exception as e:
        logger.error(f"Error making LNURL payment: {e}")
        raise HTTPException(status_code=500, detail="Failed to make LNURL payment")

@router.get("/list")
async def list_cyberherd_members(
    external_api: ExternalAPIService = Depends(get_external_api)
):
    """Get list of current CyberHerd members."""
    members = await external_api.fetch_cyberherd_targets()
    return {"members": members}

@router.get("/spots")
async def get_spots_remaining():
    """Get remaining spots in CyberHerd."""
    from config import MAX_HERD_SIZE
    # For now, just return max size since we don't track current members
    return {"spots_remaining": MAX_HERD_SIZE}
