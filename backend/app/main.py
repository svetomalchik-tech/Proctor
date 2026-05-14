"""
Main FastAPI Application for Proctoring System
Implements WebSocket handling, REST API, and session management.
"""
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from typing import Dict, Optional
import time
import json
import signal
import asyncio

from app.api import proctoring
from app.config import settings
from app.services.session_manager import ProctoringSessionManager, active_sessions, create_session, remove_session, get_active_session_ids, get_session_count
from app.core.logging_config import logger, get_logger
from app.core.rate_limiter import RateLimitMiddleware
from app.core.redis_client import init_redis, close_redis, redis_client

# Инициализация логирования
logger.info("Starting Proctoring System v2.0.0")

app = FastAPI(
    title="Proctoring System API",
    description="Advanced Proctoring System with AI-based cheating detection (Coursera/ProctorU level)",
    version="2.0.0"
)

# CORS middleware - безопасная конфигурация
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=settings.CORS_ALLOW_CREDENTIALS,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-Requested-With"],
    expose_headers=["X-RateLimit-Limit", "X-RateLimit-Remaining"],
)

# Rate Limiting middleware
if settings.RATE_LIMIT_ENABLED:
    app.add_middleware(RateLimitMiddleware)
    logger.info("Rate limiting enabled: %d requests per minute", settings.RATE_LIMIT_PER_MINUTE)

# Register routers
app.include_router(proctoring.router, prefix="/api/v1", tags=["proctoring"])


@app.get("/")
async def root(request: Request):
    """Health check endpoint"""
    client_ip = request.client.host if request.client else "unknown"
    logger.info("Health check requested from %s", client_ip)
    return {
        "status": "ok",
        "service": "Proctoring System",
        "version": "2.0.0",
        "features": [
            "Face detection & tracking",
            "Gaze analysis",
            "Phone detection",
            "Multi-person detection",
            "Screen activity monitoring",
            "Pattern-based cheating detection",
            "Real-time risk assessment"
        ]
    }


@app.get("/health")
async def health_check():
    """Health check with session stats"""
    # Get session count from Redis if available, otherwise from memory
    session_count = await get_session_count()
    redis_status = "connected" if redis_client.is_connected else "disconnected"
    
    logger.debug("Health check performed, active sessions: %d, Redis: %s", session_count, redis_status)
    return {
        "status": "healthy",
        "active_sessions": session_count,
        "redis_status": redis_status,
        "timestamp": time.time()
    }


@app.websocket("/ws/{session_id}")
async def websocket_endpoint(websocket: WebSocket, session_id: str):
    """
    WebSocket endpoint for real-time proctoring data stream.
    Handles video frames, screen events, and sends alerts.
    """
    # Get user_id from query params or headers (in production use JWT)
    user_id = websocket.query_params.get("user_id", "anonymous")
    
    logger.info("WebSocket connection attempt for session %s, user: %s", session_id, user_id)
    
    # Create or get session
    if session_id not in active_sessions:
        session = await create_session(session_id, user_id, websocket)
        logger.info("Created new session %s for user %s", session_id, user_id)
    else:
        session = active_sessions[session_id]
        await session.connect(websocket)
        logger.info("Reconnected to existing session %s", session_id)
    
    try:
        # Start monitoring loop
        await session.start_monitoring()
    except WebSocketDisconnect:
        logger.info("WebSocket disconnected for session %s", session_id)
    except Exception as e:
        logger.error("Error in session %s: %s", session_id, str(e), exc_info=True)
    finally:
        # Cleanup
        await remove_session(session_id)
        logger.info("Session %s terminated and cleaned up", session_id)


@app.get("/api/v1/sessions/{session_id}/status")
async def get_session_status(session_id: str):
    """Get real-time status of a proctoring session"""
    logger.debug("Getting status for session %s", session_id)
    
    # Try to get session (now async)
    session = await get_session(session_id)
    if not session:
        logger.warning("Session %s not found", session_id)
        raise HTTPException(status_code=404, detail="Session not found or inactive")
    
    return session.generate_report()


@app.post("/api/v1/sessions/{session_id}/terminate")
async def terminate_session(session_id: str):
    """Manually terminate a proctoring session"""
    logger.info("Manual termination requested for session %s", session_id)
    
    # Check if session exists (using async get)
    session = await get_session(session_id)
    if not session:
        logger.warning("Attempted to terminate non-existent session %s", session_id)
        raise HTTPException(status_code=404, detail="Session not found")
    
    report = await session.stop_session()
    
    # Remove from memory cache
    if session_id in active_sessions:
        del active_sessions[session_id]
    
    # Clean up Redis (handled in remove_session)
    await remove_session(session_id)
    
    logger.info("Session %s terminated successfully", session_id)
    return {"message": "Session terminated", "report": report}


@app.on_event("startup")
async def startup_event():
    """Application startup handler"""
    logger.info("Proctoring System starting up...")
    logger.info("Configuration: HOST=%s, PORT=%d", settings.HOST, settings.PORT)
    logger.info("Allowed origins: %s", settings.ALLOWED_ORIGINS)
    
    # Initialize Redis connection
    redis_connected = await init_redis()
    if redis_connected:
        logger.info("Redis storage enabled for session persistence")
    else:
        logger.warning("Redis not available, using in-memory storage only")


@app.on_event("shutdown")
async def shutdown_event():
    """Graceful shutdown handler"""
    logger.info("Proctoring System shutting down...")
    
    # Gracefully stop all active sessions
    if active_sessions:
        logger.info("Terminating %d active sessions...", len(active_sessions))
        for session_id in list(active_sessions.keys()):
            try:
                session = active_sessions[session_id]
                await session.stop_session()
                logger.info("Session %s stopped", session_id)
            except Exception as e:
                logger.error("Error stopping session %s: %s", session_id, str(e))
    
    # Close Redis connection
    await close_redis()
    
    logger.info("Shutdown complete")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=True
    )
