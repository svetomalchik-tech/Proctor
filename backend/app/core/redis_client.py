"""
Redis Client Module
Provides async Redis connection and utilities for session storage.
"""
import json
import redis.asyncio as redis
from typing import Optional, Dict, Any, List
from app.core.logging_config import get_logger
from config import settings

logger = get_logger(__name__)


class RedisClient:
    """
    Async Redis client for session storage and caching.
    Provides connection pooling and automatic reconnection.
    """
    
    def __init__(self):
        self.client: Optional[redis.Redis] = None
        self.is_connected = False
        
    async def connect(self) -> bool:
        """
        Establish connection to Redis.
        Returns True if successful, False if Redis is unavailable.
        """
        if not settings.REDIS_URL:
            logger.warning("REDIS_URL not configured, running without Redis")
            return False
            
        try:
            self.client = redis.from_url(
                settings.REDIS_URL,
                encoding="utf-8",
                decode_responses=True,
                max_connections=50,
                socket_timeout=5.0,
                socket_connect_timeout=5.0,
                retry_on_timeout=True,
            )
            
            # Test connection
            await self.client.ping()
            self.is_connected = True
            logger.info("Successfully connected to Redis at %s", settings.REDIS_URL)
            return True
            
        except Exception as e:
            logger.error("Failed to connect to Redis: %s", str(e))
            self.is_connected = False
            return False
    
    async def disconnect(self):
        """Close Redis connection."""
        if self.client:
            await self.client.close()
            self.is_connected = False
            logger.info("Redis connection closed")
    
    async def set(self, key: str, value: Any, expire: Optional[int] = None) -> bool:
        """
        Set a value in Redis.
        
        Args:
            key: Redis key
            value: Value to store (will be JSON serialized if dict/list)
            expire: Optional TTL in seconds
            
        Returns:
            True if successful
        """
        if not self.is_connected:
            return False
            
        try:
            if isinstance(value, (dict, list)):
                value = json.dumps(value)
            
            if expire:
                await self.client.setex(key, expire, value)
            else:
                await self.client.set(key, value)
                
            return True
        except Exception as e:
            logger.error("Redis SET error for key %s: %s", key, str(e))
            return False
    
    async def get(self, key: str) -> Optional[Any]:
        """
        Get a value from Redis.
        
        Args:
            key: Redis key
            
        Returns:
            Deserialized value or None
        """
        if not self.is_connected:
            return None
            
        try:
            value = await self.client.get(key)
            
            if value is None:
                return None
                
            # Try to deserialize JSON
            try:
                return json.loads(value)
            except (json.JSONDecodeError, TypeError):
                return value
                
        except Exception as e:
            logger.error("Redis GET error for key %s: %s", key, str(e))
            return None
    
    async def delete(self, *keys: str) -> int:
        """
        Delete one or more keys.
        
        Returns:
            Number of keys deleted
        """
        if not self.is_connected:
            return 0
            
        try:
            return await self.client.delete(*keys)
        except Exception as e:
            logger.error("Redis DELETE error: %s", str(e))
            return 0
    
    async def exists(self, key: str) -> bool:
        """Check if a key exists."""
        if not self.is_connected:
            return False
            
        try:
            return bool(await self.client.exists(key))
        except Exception as e:
            logger.error("Redis EXISTS error: %s", str(e))
            return False
    
    async def expire(self, key: str, seconds: int) -> bool:
        """Set expiration time for a key."""
        if not self.is_connected:
            return False
            
        try:
            return await self.client.expire(key, seconds)
        except Exception as e:
            logger.error("Redis EXPIRE error: %s", str(e))
            return False
    
    async def hset(self, name: str, key: str, value: Any) -> int:
        """Set a hash field."""
        if not self.is_connected:
            return 0
            
        try:
            if isinstance(value, (dict, list)):
                value = json.dumps(value)
            return await self.client.hset(name, key, value)
        except Exception as e:
            logger.error("Redis HSET error: %s", str(e))
            return 0
    
    async def hget(self, name: str, key: str) -> Optional[Any]:
        """Get a hash field."""
        if not self.is_connected:
            return None
            
        try:
            value = await self.client.hget(name, key)
            
            if value is None:
                return None
                
            try:
                return json.loads(value)
            except (json.JSONDecodeError, TypeError):
                return value
                
        except Exception as e:
            logger.error("Redis HGET error: %s", str(e))
            return None
    
    async def hgetall(self, name: str) -> Dict[str, Any]:
        """Get all fields from a hash."""
        if not self.is_connected:
            return {}
            
        try:
            data = await self.client.hgetall(name)
            
            # Deserialize JSON values
            result = {}
            for k, v in data.items():
                try:
                    result[k] = json.loads(v)
                except (json.JSONDecodeError, TypeError):
                    result[k] = v
                    
            return result
        except Exception as e:
            logger.error("Redis HGETALL error: %s", str(e))
            return {}
    
    async def hdel(self, name: str, *keys: str) -> int:
        """Delete hash fields."""
        if not self.is_connected:
            return 0
            
        try:
            return await self.client.hdel(name, *keys)
        except Exception as e:
            logger.error("Redis HDEL error: %s", str(e))
            return 0
    
    async def sadd(self, name: str, *values: str) -> int:
        """Add members to a set."""
        if not self.is_connected:
            return 0
            
        try:
            return await self.client.sadd(name, *values)
        except Exception as e:
            logger.error("Redis SADD error: %s", str(e))
            return 0
    
    async def srem(self, name: str, *values: str) -> int:
        """Remove members from a set."""
        if not self.is_connected:
            return 0
            
        try:
            return await self.client.srem(name, *values)
        except Exception as e:
            logger.error("Redis SREM error: %s", str(e))
            return 0
    
    async def smembers(self, name: str) -> set:
        """Get all members of a set."""
        if not self.is_connected:
            return set()
            
        try:
            return await self.client.smembers(name)
        except Exception as e:
            logger.error("Redis SMEMBERS error: %s", str(e))
            return set()
    
    async def lpush(self, name: str, *values: Any) -> int:
        """Push values to a list."""
        if not self.is_connected:
            return 0
            
        try:
            serialized = [json.dumps(v) if isinstance(v, (dict, list)) else str(v) for v in values]
            return await self.client.lpush(name, *serialized)
        except Exception as e:
            logger.error("Redis LPUSH error: %s", str(e))
            return 0
    
    async def lrange(self, name: str, start: int, end: int) -> List[Any]:
        """Get range of list elements."""
        if not self.is_connected:
            return []
            
        try:
            data = await self.client.lrange(name, start, end)
            
            # Deserialize JSON values
            result = []
            for item in data:
                try:
                    result.append(json.loads(item))
                except (json.JSONDecodeError, TypeError):
                    result.append(item)
                    
            return result
        except Exception as e:
            logger.error("Redis LRANGE error: %s", str(e))
            return []
    
    async def llen(self, name: str) -> int:
        """Get length of a list."""
        if not self.is_connected:
            return 0
            
        try:
            return await self.client.llen(name)
        except Exception as e:
            logger.error("Redis LLEN error: %s", str(e))
            return 0
    
    async def incr(self, name: str, amount: int = 1) -> int:
        """Increment a key's value."""
        if not self.is_connected:
            return 0
            
        try:
            return await self.client.incr(name, amount)
        except Exception as e:
            logger.error("Redis INCR error: %s", str(e))
            return 0
    
    async def ping(self) -> bool:
        """Test Redis connection."""
        if not self.is_connected:
            return False
            
        try:
            return await self.client.ping()
        except Exception:
            return False


# Global Redis client instance
redis_client = RedisClient()


async def init_redis() -> bool:
    """Initialize Redis connection."""
    return await redis_client.connect()


async def close_redis():
    """Close Redis connection."""
    await redis_client.disconnect()
