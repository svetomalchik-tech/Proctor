"""
Main FastAPI Application for Proctoring System
Implements WebSocket handling, REST API, and session management.
"""
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from typing import Dict, Optional
import time
import json

from app.api import proctoring
from app.config import settings
from app.services.session_manager import ProctoringSessionManager, active_sessions, create_session, remove_session

app = FastAPI(
    title="Proctoring System API",
    description="Advanced Proctoring System with AI-based cheating detection (Coursera/ProctorU level)",
    version="2.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production specify exact domains
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routers
app.include_router(proctoring.router, prefix="/api/v1", tags=["proctoring"])


@app.get("/")
async def root():
    """Health check endpoint"""
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
    return {
        "status": "healthy",
        "active_sessions": len(active_sessions),
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
    
    # Create or get session
    if session_id not in active_sessions:
        session = await create_session(session_id, user_id, websocket)
    else:
        session = active_sessions[session_id]
        await session.connect(websocket)
    
    try:
        # Start monitoring loop
        await session.start_monitoring()
    except WebSocketDisconnect:
        print(f"WebSocket disconnected for session {session_id}")
    finally:
        # Cleanup
        await remove_session(session_id)
        print(f"Session {session_id} terminated")


@app.get("/api/v1/sessions/{session_id}/status")
async def get_session_status(session_id: str):
    """Get real-time status of a proctoring session"""
    session = active_sessions.get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found or inactive")
    
    return session.generate_report()


@app.post("/api/v1/sessions/{session_id}/terminate")
async def terminate_session(session_id: str):
    """Manually terminate a proctoring session"""
    if session_id not in active_sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    
    session = active_sessions[session_id]
    report = await session.stop_session()
    del active_sessions[session_id]
    
    return {"message": "Session terminated", "report": report}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=True
    )
