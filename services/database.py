import logging
import asyncio
import json
import time
from typing import Dict, List, Optional, Any
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import text
from config import config

logger = logging.getLogger(__name__)

DEFAULT_DATABASE_URL = "sqlite+aiosqlite:///./lightning_goats.db"

class DatabaseService:
    def __init__(self, database_url: str = None):
        self.database_url = database_url or config.get('DATABASE_URL', DEFAULT_DATABASE_URL)
        if not self.database_url.startswith('sqlite+aiosqlite://'):
            self.database_url = self.database_url.replace('sqlite://', 'sqlite+aiosqlite://')
        
        self.engine = create_async_engine(self.database_url, echo=True)
        self.async_session = sessionmaker(
            self.engine, class_=AsyncSession, expire_on_commit=False
        )

    async def connect(self):
        """Initialize database connection and create tables."""
        try:
            async with self.engine.begin() as conn:
                # Create tables
                await conn.execute(text("""
                    CREATE TABLE IF NOT EXISTS cyber_herd (
                        pubkey TEXT PRIMARY KEY,
                        display_name TEXT,
                        event_id TEXT,
                        note TEXT,
                        kinds TEXT,
                        nprofile TEXT,
                        lud16 TEXT,
                        notified TEXT,
                        payouts REAL,
                        amount INTEGER,
                        picture TEXT
                    )
                """))
                
                await conn.execute(text("""
                    CREATE TABLE IF NOT EXISTS cache (
                        key TEXT PRIMARY KEY,
                        value TEXT NOT NULL,
                        expires_at REAL NOT NULL
                    )
                """))
            
            logger.info("Successfully connected to database and created tables")
        except Exception as e:
            logger.error(f"Failed to connect to database: {e}")
            raise

    async def disconnect(self):
        """Close database connection."""
        try:
            await self.engine.dispose()
            logger.info("Successfully disconnected from database")
        except Exception as e:
            logger.error(f"Error disconnecting from database: {e}")
            raise

    async def fetch_one(self, query: str, values: Optional[Dict] = None) -> Optional[Dict]:
        """Execute a query and return one result."""
        try:
            if config['DEBUG']:
                logger.debug(f"Executing fetch_one query: {query}")
                logger.debug(f"With values: {values}")
                
            async with self.async_session() as session:
                result = await session.execute(text(query), values or {})
                row = result.first()
                if config['DEBUG']:
                    logger.debug(f"Query result: {row._mapping if row else None}")
                return dict(row._mapping) if row else None
        except Exception as e:
            logger.error(f"Error executing fetch_one query: {e}", exc_info=True)
            raise

    async def fetch_all(self, query: str, values: Optional[Dict] = None) -> List[Dict]:
        """Execute a query and return all results."""
        try:
            async with self.async_session() as session:
                result = await session.execute(text(query), values or {})
                return [dict(row._mapping) for row in result]
        except Exception as e:
            logger.error(f"Error executing fetch_all query: {e}")
            raise

    async def execute(self, query: str, values: Optional[Dict] = None) -> Any:
        """Execute a query."""
        try:
            async with self.async_session() as session:
                result = await session.execute(text(query), values or {})
                await session.commit()
                return result
        except Exception as e:
            logger.error(f"Error executing query: {e}")
            raise

    async def cache_set(self, key: str, value: Any, ttl: int = 300):
        """Set a cache value with TTL."""
        expires_at = time.time() + ttl
        query = """
            INSERT INTO cache (key, value, expires_at)
            VALUES (:key, :value, :expires_at)
            ON CONFLICT(key) DO UPDATE SET
                value = :value,
                expires_at = :expires_at
        """
        await self.execute(query, {
            "key": key,
            "value": json.dumps(value),
            "expires_at": expires_at
        })

    async def cache_get(self, key: str) -> Optional[Any]:
        """Get a cache value if not expired."""
        query = "SELECT value, expires_at FROM cache WHERE key = :key"
        result = await self.fetch_one(query, {"key": key})
        if result and result["expires_at"] > time.time():
            return json.loads(result["value"])
        return None

    async def cache_cleanup(self):
        """Remove expired cache entries."""
        query = "DELETE FROM cache WHERE expires_at < :current_time"
        await self.execute(query, {"current_time": time.time()})

    async def schedule_cache_cleanup(self):
        """Schedule periodic cache cleanup."""
        while True:
            await asyncio.sleep(1800)  # Every 30 minutes
            try:
                await self.cache_cleanup()
            except Exception as e:
                logger.error(f"Error cleaning up cache: {e}")

    async def update_notified_field(self, pubkey: str, status: str):
        """Update the 'notified' field for a CyberHerd member."""
        if config['DEBUG']:
            logger.debug(f"Updating notified field for pubkey {pubkey} to {status}")
            
        query = """
            UPDATE cyber_herd
            SET notified = :status
            WHERE pubkey = :pubkey
        """
        values = {"pubkey": pubkey, "status": status}
        try:
            result = await self.execute(query, values)
            if config['DEBUG']:
                logger.debug(f"Update result: {result}")
        except Exception as e:
            logger.error(f"Error updating notified field: {e}", exc_info=True)
            raise
