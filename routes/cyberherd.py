from fastapi import APIRouter, HTTPException, Depends
from typing import List
from ..services.cyberherd_manager import CyberHerdManager
from ..services.database import DatabaseService
from ..services.external_api import ExternalAPIService
from ..services.notifier import NotifierService
from ..models import CyberHerdData, CyberHerdTreats
from ..config import MAX_HERD_SIZE
import logging

logger = logging.getLogger(__name__)
router = APIRouter()

async def get_cyberherd_manager(
    database: DatabaseService = Depends(),
    external_api: ExternalAPIService = Depends(),
    notifier: NotifierService = Depends()
):
    return CyberHerdManager(database, external_api, notifier)

@router.post("/cyber_herd")
async def update_cyber_herd(
    data: List[CyberHerdData],
    manager: CyberHerdManager = Depends(get_cyberherd_manager)
):
    """Update CyberHerd members and process their data."""
    try:
        current_size = await manager.database.fetch_one(
            "SELECT COUNT(*) as count FROM cyber_herd"
        )
        if current_size['count'] >= MAX_HERD_SIZE:
            return {"status": "herd full"}

        results = []
        for item in data:
            if item.pubkey:
                result = await manager.process_new_member(
                    item.dict(),
                    item.kinds,
                    current_size['count']
                )
                results.append(result)

        return {
            "status": "success",
            "results": results
        }
    except Exception as e:
        logger.error(f"Error updating cyber herd: {e}")
        raise HTTPException(status_code=500, detail="Failed to update cyber herd")

@router.get("/cyber_herd")
async def get_cyber_herd(database: DatabaseService = Depends()):
    """Get all CyberHerd members."""
    try:
        members = await database.fetch_all("SELECT * FROM cyber_herd")
        return members
    except Exception as e:
        logger.error(f"Error retrieving cyber herd: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve cyber herd")

@router.delete("/cyber_herd/{pubkey}")
async def delete_cyber_herd_member(pubkey: str, database: DatabaseService = Depends()):
    """Delete a CyberHerd member."""
    try:
        await database.execute(
            "DELETE FROM cyber_herd WHERE pubkey = :pubkey",
            {"pubkey": pubkey}
        )
        return {"status": "success"}
    except Exception as e:
        logger.error(f"Error deleting cyber herd member: {e}")
        raise HTTPException(status_code=500, detail="Failed to delete member")

@router.post("/messages/cyberherd_treats")
async def handle_cyberherd_treats(
    data: CyberHerdTreats,
    database: DatabaseService = Depends(),
    notifier: NotifierService = Depends()
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
    external_api: ExternalAPIService = Depends()
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
