from typing import Dict, Any, List, Optional
import asyncio
from datetime import datetime

import asyncpg
from motor.motor_asyncio import AsyncIOMotorClient
import redis.asyncio as redis

from config import Config

class Database:
    """Database handler class"""
    
    def __init__(self):
        """Initialize database connections"""
        self.pg_pool = None
        self.mongo_client = None
        self.redis_client = None
    
    async def connect(self):
        """Connect to all databases"""
        # PostgreSQL connection
        self.pg_pool = await asyncpg.create_pool(
            Config.get_db_url(),
            min_size=5,
            max_size=20
        )
        
        # MongoDB connection
        self.mongo_client = AsyncIOMotorClient(Config.MONGO_URI)
        self.mongo_db = self.mongo_client.get_default_database()
        
        # Redis connection
        self.redis_client = redis.Redis(
            host=Config.REDIS_CONFIG["host"],
            port=Config.REDIS_CONFIG["port"],
            db=Config.REDIS_CONFIG["db"]
        )
        
        await self._init_tables()
    
    async def close(self):
        """Close all database connections"""
        if self.pg_pool:
            await self.pg_pool.close()
        
        if self.mongo_client:
            self.mongo_client.close()
        
        if self.redis_client:
            await self.redis_client.close()
    
    async def _init_tables(self):
        """Initialize database tables"""
        async with self.pg_pool.acquire() as conn:
            # Users table
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id SERIAL PRIMARY KEY,
                    telegram_id BIGINT UNIQUE NOT NULL,
                    username VARCHAR(255),
                    first_name VARCHAR(255),
                    last_name VARCHAR(255),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Requests table
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS requests (
                    id SERIAL PRIMARY KEY,
                    user_id INTEGER REFERENCES users(id),
                    category VARCHAR(50),
                    status VARCHAR(20),
                    message TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Request files table
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS request_files (
                    id SERIAL PRIMARY KEY,
                    request_id INTEGER REFERENCES requests(id),
                    file_name VARCHAR(255) NOT NULL,
                    file_type VARCHAR(50),
                    file_size INTEGER,
                    s3_key VARCHAR(255) NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Materials table
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS materials (
                    id SERIAL PRIMARY KEY,
                    title VARCHAR(255) NOT NULL,
                    description TEXT,
                    category VARCHAR(50),
                    file_url VARCHAR(255),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
    
    async def get_or_create_user(self, user_data: Dict[str, Any]) -> int:
        """Get or create user in database"""
        async with self.pg_pool.acquire() as conn:
            user = await conn.fetchrow(
                """
                INSERT INTO users (telegram_id, username, first_name, last_name)
                VALUES ($1, $2, $3, $4)
                ON CONFLICT (telegram_id) 
                DO UPDATE SET 
                    username = EXCLUDED.username,
                    first_name = EXCLUDED.first_name,
                    last_name = EXCLUDED.last_name
                RETURNING id
                """,
                user_data["telegram_id"],
                user_data.get("username"),
                user_data.get("first_name"),
                user_data.get("last_name")
            )
            return user["id"]
    
    async def create_request(self, user_id: int, category: str, message: str) -> int:
        """Create new request"""
        async with self.pg_pool.acquire() as conn:
            request = await conn.fetchrow(
                """
                INSERT INTO requests (user_id, category, status, message)
                VALUES ($1, $2, 'new', $3)
                RETURNING id
                """,
                user_id,
                category,
                message
            )
            return request["id"]
    
    async def get_user_requests(self, user_id: int) -> List[Dict[str, Any]]:
        """Get all requests for a user"""
        async with self.pg_pool.acquire() as conn:
            requests = await conn.fetch(
                """
                SELECT * FROM requests
                WHERE user_id = $1
                ORDER BY created_at DESC
                """,
                user_id
            )
            return [dict(r) for r in requests]
    
    async def get_materials(self, category: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get materials by category"""
        async with self.pg_pool.acquire() as conn:
            if category:
                materials = await conn.fetch(
                    """
                    SELECT * FROM materials
                    WHERE category = $1
                    ORDER BY created_at DESC
                    """,
                    category
                )
            else:
                materials = await conn.fetch(
                    """
                    SELECT * FROM materials
                    ORDER BY created_at DESC
                    """
                )
            return [dict(m) for m in materials]
    
    async def store_analytics(self, data: Dict[str, Any]):
        """Store analytics data in MongoDB"""
        await self.mongo_db.analytics.insert_one({
            **data,
            "timestamp": datetime.utcnow()
        })
    
    async def cache_set(self, key: str, value: str, expire: int = 3600):
        """Set cache value"""
        await self.redis_client.set(key, value, ex=expire)
    
    async def cache_get(self, key: str) -> Optional[str]:
        """Get cache value"""
        value = await self.redis_client.get(key)
        return value.decode() if value else None

    async def add_request_file(self, request_id: int, file_data: Dict[str, Any]) -> int:
        """Add file to request"""
        async with self.pg_pool.acquire() as conn:
            file = await conn.fetchrow(
                """
                INSERT INTO request_files (
                    request_id, file_name, file_type, file_size, s3_key
                )
                VALUES ($1, $2, $3, $4, $5)
                RETURNING id
                """,
                request_id,
                file_data["file_name"],
                file_data["file_type"],
                file_data["file_size"],
                file_data["s3_key"]
            )
            return file["id"]

    async def get_request_files(self, request_id: int) -> List[Dict[str, Any]]:
        """Get all files for a request"""
        async with self.pg_pool.acquire() as conn:
            files = await conn.fetch(
                """
                SELECT * FROM request_files
                WHERE request_id = $1
                ORDER BY created_at DESC
                """,
                request_id
            )
            return [dict(f) for f in files]

    async def delete_request_file(self, file_id: int) -> bool:
        """Delete file from request"""
        async with self.pg_pool.acquire() as conn:
            result = await conn.execute(
                """
                DELETE FROM request_files
                WHERE id = $1
                RETURNING id
                """,
                file_id
            )
            return result != "DELETE 0" 