"""Routes package."""
from fastapi import APIRouter, Depends
from services.external_api import ExternalAPIService
from dependencies import get_external_api
from config import config  # Add this import

from routes.payments import router as payments_router
from routes.cyberherd import router as cyberherd_router
from routes.status import router as status_router
from routes.websocket import router as websocket_router
from routes.webhooks import router as webhooks_router
from routes.feeder import router as feeder_router
from routes.goatsats import router as goatsats_router
from routes.conversion import router as conversion_router  # Add this line
from routes.debug import router as debug_router

# Create main router
main_router = APIRouter()

# Mount routers with correct prefixes
main_router.include_router(payments_router, prefix="/payment", tags=["payments"])
main_router.include_router(cyberherd_router, prefix="/cyberherd", tags=["cyberherd"])
main_router.include_router(status_router, prefix="/status", tags=["status"])
main_router.include_router(websocket_router, prefix="/ws", tags=["websocket"])
main_router.include_router(webhooks_router, prefix="/webhook", tags=["webhooks"])
main_router.include_router(feeder_router, prefix="/feeder", tags=["feeder"])
main_router.include_router(goatsats_router, prefix="/goatsats", tags=["goatsats"])
main_router.include_router(conversion_router, prefix="/convert", tags=["conversion"])  # Add this line

# Include debug router only in DEBUG mode
if config['DEBUG']:
    main_router.include_router(
        debug_router, 
        prefix="/debug", 
        tags=["debug"]
    )

# Add root-level routes
@main_router.get("/balance")
async def get_balance_route(
    force_refresh: bool = False,
    external_api: ExternalAPIService = Depends(get_external_api)
):
    """Get current wallet balance."""
    balance = await external_api.get_balance(force_refresh)
    return {"balance": balance}
