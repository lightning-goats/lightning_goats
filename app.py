from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
import logging
import asyncio
import os
from pathlib import Path

from routes import main_router
from services.websocket_manager import WebSocketManager
from services.payment_processor import PaymentProcessor
from config import config
from dependencies import get_db, _db, _external_api, _notifier
from services.scheduler import SchedulerService
from services.cache_manager import CacheManager

# Initialize logging
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI()

# Create static directory if it doesn't exist
static_path = os.path.join(os.path.dirname(__file__), "static")
Path(static_path).mkdir(parents=True, exist_ok=True)

# Mount static directory
app.mount("/static", StaticFiles(directory=static_path), name="static")

# Add favicon route
@app.get("/favicon.ico")
async def favicon():
    return await app.send_file("static/favicon.ico")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add routes
app.include_router(main_router)

# Initialize services
payment_processor = PaymentProcessor(_external_api, _notifier, _db)

# WebSocket manager instance with payment processor
websocket_manager = WebSocketManager(
    uri=config['HERD_WEBSOCKET'],
    payment_processor=payment_processor,
    logger=logging.getLogger(__name__)
)

# Initialize additional services
scheduler = SchedulerService(_db, _external_api)
cache_manager = CacheManager(_db)

@app.on_event("startup")
async def startup_event():
    # Connect to database
    await _db.connect()
    
    # Start WebSocket connection
    websocket_task = asyncio.create_task(websocket_manager.connect())
    await websocket_manager.wait_for_connection(timeout=30)

    # Start cache cleanup task
    asyncio.create_task(_db.schedule_cache_cleanup())
    
    # Start scheduler and cache manager
    asyncio.create_task(scheduler.schedule_daily_reset())
    await cache_manager.start_cleanup_task()

@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup resources on shutdown."""
    try:
        # Disconnect from database
        await _db.disconnect()
        
        # Close WebSocket connection
        await websocket_manager.disconnect()
        
        # Close external API client
        await _external_api.close()
        
        logger.info("Cleanup completed successfully")
    except Exception as e:
        logger.error(f"Error during cleanup: {e}")

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logging.exception("Unhandled exception occurred", exc_info=exc)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal Server Error"}
    )
