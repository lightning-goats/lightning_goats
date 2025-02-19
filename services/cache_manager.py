import json
import time
import logging
import asyncio
from typing import Any, Optional
from services.database import DatabaseService

logger = logging.getLogger(__name__)

class CacheManager:
    def __init__(self, database: DatabaseService):
        self.database = database
        self._cleanup_task = None

    async def get(self, key: str, default: Any = None) -> Any:
        """Get a cached value."""
        query = "SELECT value, expires_at FROM cache WHERE key = :key"
        result = await self.database.fetch_one(query, {"key": key})
        
        if result and result["expires_at"] > time.time():
            return json.loads(result["value"])
        return default

    async def set(self, key: str, value: Any, ttl: int = 300) -> None:
        """Set a cache value with TTL."""
        expires_at = time.time() + ttl
        query = """
            INSERT INTO cache (key, value, expires_at)
            VALUES (:key, :value, :expires_at)
            ON CONFLICT(key) DO UPDATE SET
                value = :value,
                expires_at = :expires_at
        """
        await self.database.execute(query, {
            "key": key,
            "value": json.dumps(value),
            "expires_at": expires_at
        })

    async def cleanup(self) -> None:
        """Remove expired cache entries."""
        query = "DELETE FROM cache WHERE expires_at < :current_time"
        await self.database.execute(query, {"current_time": time.time()})
        
    async def start_cleanup_task(self) -> None:
        """Start periodic cache cleanup."""
        async def cleanup_loop():
            while True:
                try:
                    await self.cleanup()
                    await asyncio.sleep(1800)  # Run every 30 minutes
                except Exception as e:
                    logger.error(f"Error in cache cleanup: {e}")
                    await asyncio.sleep(60)  # Wait a minute before retrying
                    
        self._cleanup_task = asyncio.create_task(cleanup_loop())
