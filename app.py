from fastapi import FastAPI, Request, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import logging
import asyncio

from .routes import main_router
from .services.database import DatabaseService
from .services.websocket_manager import WebSocketManager
from .config import config
from .services.cyberherd_manager import CyberHerdManager
from .services.external_api import ExternalAPIService

# Initialize FastAPI app
app = FastAPI(dependencies=[Depends(ExternalAPIService), Depends(DatabaseService)])

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add routes
app.include_router(main_router)

# Database instance
database = DatabaseService()

# WebSocket manager instance
websocket_manager = WebSocketManager(
    uri=config['HERD_WEBSOCKET'],
    logger=logging.getLogger(__name__)
)

@app.on_event("startup")
async def startup_event():
    # Connect to database
    await database.connect()
    
    # Start WebSocket connection
    websocket_task = asyncio.create_task(websocket_manager.connect())
    await websocket_manager.wait_for_connection(timeout=30)

    # Start cache cleanup task
    asyncio.create_task(database.schedule_cache_cleanup())

    # Start daily reset task
    cyberherd_manager = CyberHerdManager(database, ExternalAPIService(), None)
    asyncio.create_task(cyberherd_manager.schedule_daily_reset())

@app.on_event("shutdown")
async def shutdown_event():
    # Disconnect from database
    await database.disconnect()
    
    # Close WebSocket connection
    await websocket_manager.disconnect()

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logging.exception("Unhandled exception occurred", exc_info=exc)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal Server Error"}
    )
