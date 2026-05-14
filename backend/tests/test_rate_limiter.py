"""
Unit Tests for Rate Limiter Module
Tests rate limiting logic, IP tracking, and middleware functionality.
"""
import pytest
import time
from app.core.rate_limiter import RateLimiter, RateLimitMiddleware
from fastapi import Request, HTTPException
from starlette.responses import JSONResponse
from unittest.mock import AsyncMock, MagicMock


class TestRateLimiterInitialization:
    """Test RateLimiter initialization and defaults."""
    
    def test_init_default_values(self):
        """Test limiter initializes with correct defaults."""
        limiter = RateLimiter()
        
        assert limiter.max_requests == 60
        assert limiter.window_seconds == 60
        assert len(limiter.requests) == 0
    
    def test_init_custom_values(self):
        """Test limiter initializes with custom values."""
        limiter = RateLimiter(max_requests=10, window_seconds=30)
        
        assert limiter.max_requests == 10
        assert limiter.window_seconds == 30
    
    def test_init_empty_request_dict(self):
        """Test that request dict starts empty."""
        limiter = RateLimiter()
        
        assert dict(limiter.requests) == {}


class TestRateLimiterIsAllowed:
    """Test is_allowed method for rate limiting logic."""
    
    def test_first_request_allowed(self):
        """Test first request from new IP is allowed."""
        limiter = RateLimiter(max_requests=5, window_seconds=60)
        
        allowed, remaining = limiter.is_allowed("192.168.1.1")
        
        assert allowed is True
        assert remaining == 4  # 5 - 1 = 4
    
    def test_requests_within_limit_allowed(self):
        """Test multiple requests within limit are allowed."""
        limiter = RateLimiter(max_requests=5, window_seconds=60)
        
        for i in range(5):
            allowed, remaining = limiter.is_allowed("192.168.1.1")
            assert allowed is True
            assert remaining == 4 - i
    
    def test_request_over_limit_blocked(self):
        """Test request over limit is blocked."""
        limiter = RateLimiter(max_requests=3, window_seconds=60)
        
        # Use up all requests
        for _ in range(3):
            limiter.is_allowed("192.168.1.1")
        
        # Next request should be blocked
        allowed, remaining = limiter.is_allowed("192.168.1.1")
        
        assert allowed is False
        assert remaining == 0
    
    def test_different_ips_tracked_separately(self):
        """Test different IPs have separate limits."""
        limiter = RateLimiter(max_requests=2, window_seconds=60)
        
        # Exhaust IP1 limit
        for _ in range(2):
            limiter.is_allowed("192.168.1.1")
        
        # IP2 should still be allowed
        allowed, remaining = limiter.is_allowed("192.168.1.2")
        
        assert allowed is True
        assert remaining == 1
    
    def test_remaining_count_accurate(self):
        """Test remaining count decreases correctly."""
        limiter = RateLimiter(max_requests=10, window_seconds=60)
        
        for i in range(7):
            allowed, remaining = limiter.is_allowed("192.168.1.1")
            assert allowed is True
            assert remaining == 9 - i


class TestRateLimiterWindowExpiration:
    """Test time window expiration and cleanup."""
    
    def test_requests_expire_after_window(self):
        """Test requests expire after window passes."""
        limiter = RateLimiter(max_requests=2, window_seconds=1)
        
        # Use up limit
        limiter.is_allowed("192.168.1.1")
        limiter.is_allowed("192.168.1.1")
        
        # Should be blocked now
        allowed, _ = limiter.is_allowed("192.168.1.1")
        assert allowed is False
        
        # Wait for window to expire
        time.sleep(1.1)
        
        # Should be allowed again
        allowed, remaining = limiter.is_allowed("192.168.1.1")
        assert allowed is True
        assert remaining == 1
    
    def test_cleanup_removes_expired_entries(self):
        """Test cleanup method removes expired entries."""
        limiter = RateLimiter(max_requests=5, window_seconds=1)
        
        # Add some requests
        limiter.is_allowed("192.168.1.1")
        limiter.is_allowed("192.168.1.2")
        
        # Wait for expiration
        time.sleep(1.1)
        
        # Cleanup
        limiter.cleanup()
        
        # All entries should be removed
        assert len(limiter.requests) == 0
    
    def test_cleanup_keeps_valid_entries(self):
        """Test cleanup keeps non-expired entries."""
        limiter = RateLimiter(max_requests=5, window_seconds=60)
        
        # Add recent request
        limiter.is_allowed("192.168.1.1")
        
        # Wait a bit (but not enough to expire)
        time.sleep(0.1)
        
        # Cleanup
        limiter.cleanup()
        
        # Entry should still exist
        assert "192.168.1.1" in limiter.requests


class TestRateLimiterEdgeCases:
    """Test edge cases and boundary conditions."""
    
    def test_zero_max_requests(self):
        """Test behavior with zero max requests."""
        limiter = RateLimiter(max_requests=0, window_seconds=60)
        
        allowed, remaining = limiter.is_allowed("192.168.1.1")
        
        assert allowed is False
        assert remaining == 0
    
    def test_very_large_limit(self):
        """Test behavior with very large limit."""
        limiter = RateLimiter(max_requests=1000000, window_seconds=60)
        
        allowed, remaining = limiter.is_allowed("192.168.1.1")
        
        assert allowed is True
        assert remaining == 999999
    
    def test_ip_with_special_characters(self):
        """Test IP addresses with various formats."""
        limiter = RateLimiter(max_requests=5, window_seconds=60)
        
        # IPv4
        allowed1, _ = limiter.is_allowed("192.168.1.1")
        assert allowed1 is True
        
        # IPv6 localhost
        allowed2, _ = limiter.is_allowed("::1")
        assert allowed2 is True
        
        # Different IPs tracked separately
        assert dict(limiter.requests).keys() == {"192.168.1.1", "::1"}
    
    def test_unknown_ip_address(self):
        """Test handling of 'unknown' IP."""
        limiter = RateLimiter(max_requests=5, window_seconds=60)
        
        allowed, remaining = limiter.is_allowed("unknown")
        
        assert allowed is True
        assert remaining == 4


class TestRateLimitMiddleware:
    """Test RateLimitMiddleware functionality."""
    
    @pytest.mark.asyncio
    async def test_middleware_passes_allowed_requests(self):
        """Test middleware allows requests under limit."""
        middleware = RateLimitMiddleware(app=MagicMock())
        request = MagicMock(spec=Request)
        request.client.host = "192.168.1.1"
        
        next_call = AsyncMock(return_value=JSONResponse(content={"test": "data"}))
        
        response = await middleware.dispatch(request, next_call)
        
        assert response.status_code == 200
        assert "X-RateLimit-Limit" in response.headers
        assert "X-RateLimit-Remaining" in response.headers
    
    @pytest.mark.asyncio
    async def test_middleware_blocks_exceeded_requests(self):
        """Test middleware blocks requests over limit."""
        # Create limiter with very low limit
        from app.core import rate_limiter
        original_limiter = rate_limiter.rate_limiter
        
        # Replace with test limiter
        test_limiter = RateLimiter(max_requests=1, window_seconds=60)
        rate_limiter.rate_limiter = test_limiter
        
        try:
            middleware = RateLimitMiddleware(app=MagicMock())
            request = MagicMock(spec=Request)
            request.client.host = "192.168.1.100"
            
            # First request should pass
            next_call = AsyncMock(return_value=JSONResponse(content={}))
            await middleware.dispatch(request, next_call)
            
            # Second request should be blocked
            with pytest.raises(HTTPException) as exc_info:
                await middleware.dispatch(request, next_call)
            
            assert exc_info.value.status_code == 429
            assert "Too many requests" in str(exc_info.value.detail)
        finally:
            # Restore original limiter
            rate_limiter.rate_limiter = original_limiter
    
    @pytest.mark.asyncio
    async def test_middleware_disabled_when_setting_false(self):
        """Test middleware bypasses limiting when disabled."""
        from app.core import rate_limiter
        original_settings = rate_limiter.settings
        
        # Mock settings to disable rate limiting
        mock_settings = MagicMock()
        mock_settings.RATE_LIMIT_ENABLED = False
        rate_limiter.settings = mock_settings
        
        try:
            middleware = RateLimitMiddleware(app=MagicMock())
            request = MagicMock(spec=Request)
            request.client.host = "192.168.1.1"
            
            next_call = AsyncMock(return_value=JSONResponse(content={}))
            response = await middleware.dispatch(request, next_call)
            
            # Should call next without checking limit
            next_call.assert_called_once()
            assert response.status_code == 200
        finally:
            # Restore original settings
            rate_limiter.settings = original_settings
    
    @pytest.mark.asyncio
    async def test_middleware_handles_missing_client(self):
        """Test middleware handles missing client info."""
        middleware = RateLimitMiddleware(app=MagicMock())
        request = MagicMock(spec=Request)
        request.client = None  # No client info
        
        next_call = AsyncMock(return_value=JSONResponse(content={}))
        
        # Should not crash, should use "unknown" as IP
        response = await middleware.dispatch(request, next_call)
        
        assert response.status_code == 200


class TestRateLimitHeaders:
    """Test rate limit headers in responses."""
    
    @pytest.mark.asyncio
    async def test_headers_include_limit_info(self):
        """Test response includes rate limit headers."""
        middleware = RateLimitMiddleware(app=MagicMock())
        request = MagicMock(spec=Request)
        request.client.host = "192.168.1.50"
        
        next_call = AsyncMock(return_value=JSONResponse(content={}))
        
        response = await middleware.dispatch(request, next_call)
        
        assert "X-RateLimit-Limit" in response.headers
        assert "X-RateLimit-Remaining" in response.headers
        assert int(response.headers["X-RateLimit-Limit"]) > 0
    
    @pytest.mark.asyncio
    async def test_429_includes_retry_after(self):
        """Test 429 response includes Retry-After header."""
        from app.core import rate_limiter
        original_limiter = rate_limiter.rate_limiter
        
        test_limiter = RateLimiter(max_requests=1, window_seconds=60)
        rate_limiter.rate_limiter = test_limiter
        
        try:
            middleware = RateLimitMiddleware(app=MagicMock())
            request = MagicMock(spec=Request)
            request.client.host = "192.168.1.200"
            
            # Exhaust limit
            next_call = AsyncMock(return_value=JSONResponse(content={}))
            await middleware.dispatch(request, next_call)
            
            # Try to exceed - should get 429 with Retry-After
            with pytest.raises(HTTPException) as exc_info:
                await middleware.dispatch(request, next_call)
            
            assert exc_info.value.headers is not None
            assert "Retry-After" in exc_info.value.headers
            assert exc_info.value.headers["Retry-After"] == "60"
        finally:
            rate_limiter.rate_limiter = original_limiter


class TestConcurrentAccess:
    """Test concurrent access patterns."""
    
    def test_many_ips_simultaneous(self):
        """Test handling many different IPs."""
        limiter = RateLimiter(max_requests=5, window_seconds=60)
        
        # Simulate 100 different IPs
        for i in range(100):
            ip = f"192.168.{i // 256}.{i % 256}"
            allowed, _ = limiter.is_allowed(ip)
            assert allowed is True
        
        # All IPs should be tracked
        assert len(limiter.requests) == 100
    
    def test_same_ip_rapid_requests(self):
        """Test rapid requests from same IP."""
        limiter = RateLimiter(max_requests=10, window_seconds=60)
        
        # Make 15 rapid requests
        results = []
        for _ in range(15):
            allowed, remaining = limiter.is_allowed("192.168.1.1")
            results.append((allowed, remaining))
        
        # First 10 should be allowed
        for i in range(10):
            assert results[i][0] is True
        
        # Last 5 should be blocked
        for i in range(10, 15):
            assert results[i][0] is False
            assert results[i][1] == 0
