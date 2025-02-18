import logging
from typing import Optional, List, Dict, Any
from databases import Database
from sqlalchemy import create_engine, text
from tenacity import retry, stop_after_attempt, wait_exponential
import time
import json
import asyncio
from ..config import config

logger = logging.getLogger(__name__)

class DatabaseService:
    def __init__(self, database_url: str = config['DATABASE_URL']):
        self.database_url = database_url
        self.database = Database(database_url)
        self.engine = create_engine(database_url)

    async def connect(self):
        """Connect to the database."""
        try:
            await self.database.connect()
            await self.create_tables()
            logger.info("Successfully connected to database")
        except Exception as e:
            logger.error(f"Failed to connect to database: {e}")
            raise

    async def disconnect(self):
        """Disconnect from the database."""
        try:
            await self.database.disconnect()
            logger.info("Successfully disconnected from database")
        except Exception as e:
            logger.error(f"Error disconnecting from database: {e}")
            raise

    async def create_tables(self):
        """Create necessary database tables if they don't exist."""
        try:
            queries = [
                """
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
                """,
                """
                CREATE TABLE IF NOT EXISTS cache (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL,
                    expires_at REAL NOT NULL
                )
                """
            ]
            
            for query in queries:
                await self.database.execute(query=query)
            
            logger.info("Database tables created successfully")
        except Exception as e:
            logger.error(f"Error creating database tables: {e}")
            raise

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
    async def fetch_one(self, query: str, values: Optional[Dict] = None) -> Optional[Dict]:
        """Execute a query and return one result."""
        try:
            result = await self.database.fetch_one(query=query, values=values)
            return dict(result) if result else None
        except Exception as e:
            logger.error(f"Error executing fetch_one query: {e}")
            raise

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
    async def fetch_all(self, query: str, values: Optional[Dict] = None) -> List[Dict]:
        """Execute a query and return all results."""
        try:
            results = await self.database.fetch_all(query=query, values=values)
            return [dict(row) for row in results]
        except Exception as e:
            logger.error(f"Error executing fetch_all query: {e}")
            raise

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
    async def execute(self, query: str, values: Optional[Dict] = None) -> Any:
        """Execute a query and return the result."""
        try:
            return await self.database.execute(query=query, values=values)
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
        query = """
            UPDATE cyber_herd
            SET notified = :status
            WHERE pubkey = :pubkey
        """
        values = {"pubkey": pubkey, "status": status}
        await self.execute(query, values)
