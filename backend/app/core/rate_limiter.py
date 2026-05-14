"""
Rate Limiting Middleware
Protects against DDoS and abuse by limiting requests per IP.
"""
import time
from collections import defaultdict
from typing import Dict, Tuple
from fastapi import Request, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

import config
from app.core.logging_config import get_logger

settings = config.Settings()
logger = get_logger(__name__)


class RateLimiter:
    """Simple in-memory rate limiter (use Redis for production)"""
    
    def __init__(self, max_requests: int = 60, window_seconds: int = 60):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        # {ip: [(timestamp, count), ...]}
        self.requests: Dict[str, list] = defaultdict(list)
    
    def is_allowed(self, client_ip: str) -> Tuple[bool, int]:
        """
        Check if request is allowed for given IP.
        
        Returns:
            Tuple of (is_allowed, remaining_requests)
        """
        current_time = time.time()
        window_start = current_time - self.window_seconds
        
        # Clean old requests
        self.requests[client_ip] = [
            ts for ts in self.requests[client_ip]
            if ts > window_start
        ]
        
        # Check limit
        current_count = len(self.requests[client_ip])
        remaining = self.max_requests - current_count
        
        if current_count >= self.max_requests:
            return False, 0
        
        # Record this request
        self.requests[client_ip].append(current_time)
        return True, remaining - 1
    
    def cleanup(self):
        """Remove expired entries to prevent memory leak"""
        current_time = time.time()
        window_start = current_time - self.window_seconds
        
        for ip in list(self.requests.keys()):
            self.requests[ip] = [
                ts for ts in self.requests[ip]
                if ts > window_start
            ]
            if not self.requests[ip]:
                del self.requests[ip]


# Global rate limiter instance
rate_limiter = RateLimiter(
    max_requests=settings.RATE_LIMIT_PER_MINUTE,
    window_seconds=60
)


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Middleware to enforce rate limiting"""
    
    async def dispatch(self, request: Request, call_next):
        if not settings.RATE_LIMIT_ENABLED:
            return await call_next(request)
        
        # Get client IP (handle proxies)
        client_ip = request.client.host if request.client else "unknown"
        
        # Check rate limit
        allowed, remaining = rate_limiter.is_allowed(client_ip)
        
        if not allowed:
            logger.warning(f"Rate limit exceeded for IP: {client_ip}")
            raise HTTPException(
                status_code=429,
                detail="Too many requests. Please try again later.",
                headers={
                    "Retry-After": "60",
                    "X-RateLimit-Limit": str(rate_limiter.max_requests),
                    "X-RateLimit-Remaining": "0"
                }
            )
        
        # Process request
        response = await call_next(request)
        
        # Add rate limit headers
        response.headers["X-RateLimit-Limit"] = str(rate_limiter.max_requests)
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        
        return response
