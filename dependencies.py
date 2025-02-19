from typing import AsyncGenerator
from fastapi import Depends
from services.database import DatabaseService
from services.external_api import ExternalAPIService
from services.cyberherd_manager import CyberHerdManager
from services.notifier import NotifierService

# Singleton instances
_db = DatabaseService()
_external_api = ExternalAPIService()
_notifier = NotifierService()

async def get_db() -> AsyncGenerator[DatabaseService, None]:
    """Database dependency."""
    try:
        await _db.connect()
        yield _db
    finally:
        await _db.disconnect()

async def get_external_api() -> AsyncGenerator[ExternalAPIService, None]:
    """External API dependency."""
    try:
        yield _external_api
    finally:
        await _external_api.close()

async def get_notifier() -> NotifierService:
    """Notifier service dependency."""
    return _notifier

async def get_cyberherd_manager(
    db: DatabaseService = Depends(get_db),
    api: ExternalAPIService = Depends(get_external_api),
    notifier: NotifierService = Depends(get_notifier)
) -> CyberHerdManager:
    """CyberHerd manager dependency."""
    return CyberHerdManager(db, api, notifier)
