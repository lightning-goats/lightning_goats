from fastapi import APIRouter
from .payments import router as payments_router
from .cyberherd import router as cyberherd_router
from .status import router as status_router
from .websocket import router as websocket_router

# Create main router
main_router = APIRouter()

# Include all routers
main_router.include_router(payments_router, prefix="/payments", tags=["payments"])
main_router.include_router(cyberherd_router, prefix="/cyberherd", tags=["cyberherd"])
main_router.include_router(status_router, prefix="/status", tags=["status"])
main_router.include_router(websocket_router, prefix="/ws", tags=["websocket"])
