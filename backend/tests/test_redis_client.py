"""
Unit Tests for Redis Client Module
Tests Redis integration with fallback to in-memory when Redis is unavailable.
"""
import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from app.core.redis_client import RedisClient, redis_client


class TestRedisClientInitialization:
    """Test Redis client initialization."""
    
    def test_init_default_values(self):
        """Test default initialization values."""
        client = RedisClient()
        assert client.client is None
        assert client.is_connected is False
    
    def test_singleton_pattern(self):
        """Test that global redis_client is a singleton."""
        assert isinstance(redis_client, RedisClient)


class TestRedisClientConnect:
    """Test Redis connection logic."""
    
    @pytest.mark.asyncio
    async def test_connect_without_url(self):
        """Test connection fails gracefully without REDIS_URL."""
        with patch('app.core.redis_client.settings') as mock_settings:
            mock_settings.REDIS_URL = None
            
            client = RedisClient()
            result = await client.connect()
            
            assert result is False
            assert client.is_connected is False
    
    @pytest.mark.asyncio
    async def test_connect_success(self):
        """Test successful Redis connection."""
        mock_redis = AsyncMock()
        mock_redis.ping = AsyncMock(return_value=True)
        
        with patch('app.core.redis_client.settings') as mock_settings:
            mock_settings.REDIS_URL = "redis://localhost:6379/0"
            
            with patch('app.core.redis_client.redis.from_url', return_value=mock_redis):
                client = RedisClient()
                result = await client.connect()
                
                assert result is True
                assert client.is_connected is True
                assert client.client == mock_redis
                mock_redis.ping.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_connect_failure(self):
        """Test connection handles failures gracefully."""
        with patch('app.core.redis_client.settings') as mock_settings:
            mock_settings.REDIS_URL = "redis://invalid:6379/0"
            
            with patch('app.core.redis_client.redis.from_url', side_effect=Exception("Connection refused")):
                client = RedisClient()
                result = await client.connect()
                
                assert result is False
                assert client.is_connected is False


class TestRedisClientOperations:
    """Test Redis operations with connection check."""
    
    @pytest.mark.asyncio
    async def test_set_without_connection(self):
        """Test SET returns False when not connected."""
        client = RedisClient()
        result = await client.set("key", "value")
        assert result is False
    
    @pytest.mark.asyncio
    async def test_get_without_connection(self):
        """Test GET returns None when not connected."""
        client = RedisClient()
        result = await client.get("key")
        assert result is None
    
    @pytest.mark.asyncio
    async def test_delete_without_connection(self):
        """Test DELETE returns 0 when not connected."""
        client = RedisClient()
        result = await client.delete("key1", "key2")
        assert result == 0
    
    @pytest.mark.asyncio
    async def test_exists_without_connection(self):
        """Test EXISTS returns False when not connected."""
        client = RedisClient()
        result = await client.exists("key")
        assert result is False


class TestRedisClientWithMock:
    """Test Redis operations with mocked client."""
    
    @pytest.fixture
    async def mock_redis_client(self):
        """Create a mock Redis client."""
        mock_redis = AsyncMock()
        mock_redis.ping = AsyncMock(return_value=True)
        mock_redis.set = AsyncMock(return_value=True)
        mock_redis.get = AsyncMock(return_value=None)
        mock_redis.delete = AsyncMock(return_value=1)
        mock_redis.exists = AsyncMock(return_value=1)
        mock_redis.expire = AsyncMock(return_value=True)
        mock_redis.hset = AsyncMock(return_value=1)
        mock_redis.hget = AsyncMock(return_value=None)
        mock_redis.hgetall = AsyncMock(return_value={})
        mock_redis.hdel = AsyncMock(return_value=1)
        mock_redis.sadd = AsyncMock(return_value=1)
        mock_redis.srem = AsyncMock(return_value=1)
        mock_redis.smembers = AsyncMock(return_value=set())
        mock_redis.lpush = AsyncMock(return_value=1)
        mock_redis.lrange = AsyncMock(return_value=[])
        mock_redis.llen = AsyncMock(return_value=0)
        mock_redis.incr = AsyncMock(return_value=1)
        mock_redis.setex = AsyncMock(return_value=True)
        mock_redis.close = AsyncMock()
        
        client = RedisClient()
        client.client = mock_redis
        client.is_connected = True
        
        return client
    
    @pytest.mark.asyncio
    async def test_set_dict_value(self, mock_redis_client):
        """Test SET serializes dict to JSON."""
        data = {"session_id": "123", "user_id": "user1"}
        result = await mock_redis_client.set("key", data)
        
        assert result is True
        mock_redis_client.client.set.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_set_with_expire(self, mock_redis_client):
        """Test SET with expiration uses setex."""
        result = await mock_redis_client.set("key", "value", expire=3600)
        
        assert result is True
        mock_redis_client.client.setex.assert_called_once_with("key", 3600, "value")
    
    @pytest.mark.asyncio
    async def test_get_json_deserialization(self, mock_redis_client):
        """Test GET deserializes JSON."""
        import json
        mock_redis_client.client.get = AsyncMock(return_value=json.dumps({"key": "value"}))
        
        result = await mock_redis_client.get("key")
        
        assert result == {"key": "value"}
    
    @pytest.mark.asyncio
    async def test_get_plain_string(self, mock_redis_client):
        """Test GET returns plain string if not JSON."""
        mock_redis_client.client.get = AsyncMock(return_value="plain_text")
        
        result = await mock_redis_client.get("key")
        
        assert result == "plain_text"
    
    @pytest.mark.asyncio
    async def test_hset_serializes_dict(self, mock_redis_client):
        """Test HSET serializes dict values."""
        data = {"field": "value"}
        result = await mock_redis_client.hset("hash", "field", data)
        
        assert result == 1
    
    @pytest.mark.asyncio
    async def test_lpush_serializes_list(self, mock_redis_client):
        """Test LPUSH serializes list/dict values."""
        data = [{"event": "test"}, "plain"]
        result = await mock_redis_client.lpush("list", *data)
        
        assert result == 1
    
    @pytest.mark.asyncio
    async def test_lrange_deserializes(self, mock_redis_client):
        """Test LRANGE deserializes JSON values."""
        import json
        items = [json.dumps({"event": "test"}), "plain"]
        mock_redis_client.client.lrange = AsyncMock(return_value=items)
        
        result = await mock_redis_client.lrange("list", 0, -1)
        
        assert len(result) == 2
        assert result[0] == {"event": "test"}
        assert result[1] == "plain"
    
    @pytest.mark.asyncio
    async def test_sadd_multiple_values(self, mock_redis_client):
        """Test SADD adds multiple members."""
        result = await mock_redis_client.sadd("set", "member1", "member2", "member3")
        
        assert result == 1
        mock_redis_client.client.sadd.assert_called_once_with("set", "member1", "member2", "member3")
    
    @pytest.mark.asyncio
    async def test_ping_success(self, mock_redis_client):
        """Test PING returns True when connected."""
        result = await mock_redis_client.ping()
        assert result is True
    
    @pytest.mark.asyncio
    async def test_ping_failure(self, mock_redis_client):
        """Test PING returns False on error."""
        mock_redis_client.client.ping = AsyncMock(side_effect=Exception("Connection lost"))
        
        result = await mock_redis_client.ping()
        assert result is False


class TestRedisClientDisconnect:
    """Test Redis disconnection."""
    
    @pytest.mark.asyncio
    async def test_disconnect_with_client(self):
        """Test disconnect closes client."""
        mock_redis = AsyncMock()
        mock_redis.close = AsyncMock()
        
        client = RedisClient()
        client.client = mock_redis
        client.is_connected = True
        
        await client.disconnect()
        
        assert client.is_connected is False
        mock_redis.close.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_disconnect_without_client(self):
        """Test disconnect handles missing client."""
        client = RedisClient()
        
        # Should not raise
        await client.disconnect()
        assert client.is_connected is False


class TestRedisInitFunctions:
    """Test module-level init functions."""
    
    @pytest.mark.asyncio
    async def test_init_redis(self):
        """Test init_redis calls connect."""
        with patch.object(RedisClient, 'connect', new_callable=AsyncMock) as mock_connect:
            mock_connect.return_value = True
            
            from app.core.redis_client import init_redis
            result = await init_redis()
            
            assert result is True
            mock_connect.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_close_redis(self):
        """Test close_redis calls disconnect."""
        with patch.object(RedisClient, 'disconnect', new_callable=AsyncMock) as mock_disconnect:
            from app.core.redis_client import close_redis
            await close_redis()
            
            mock_disconnect.assert_called_once()


class TestIntegrationScenarios:
    """Test integration scenarios."""
    
    @pytest.mark.asyncio
    async def test_fallback_when_redis_unavailable(self):
        """Test operations gracefully degrade when Redis is down."""
        client = RedisClient()
        # Not connected
        
        # All operations should return safe defaults
        assert await client.set("key", "value") is False
        assert await client.get("key") is None
        assert await client.delete("key") == 0
        assert await client.exists("key") is False
        assert await client.hgetall("hash") == {}
        assert await client.smembers("set") == set()
        assert await client.lrange("list", 0, -1) == []
    
    @pytest.mark.asyncio
    async def test_error_handling_in_operations(self):
        """Test errors are caught and logged."""
        mock_redis = AsyncMock()
        mock_redis.get = AsyncMock(side_effect=Exception("Redis error"))
        
        client = RedisClient()
        client.client = mock_redis
        client.is_connected = True
        
        # Should return None instead of raising
        result = await client.get("key")
        assert result is None
