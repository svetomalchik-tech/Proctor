"""
Session Manager Module
Orchestrates video processing, screen monitoring, and event logging.
Now uses Redis for distributed session storage.
"""
import asyncio
import json
import base64
import time
from typing import Dict, Optional, List
from fastapi import WebSocket, WebSocketDisconnect
import cv2
import numpy as np

from app.services.behavior_analyzer import BehaviorAnalyzer, Event, SeverityLevel, DetectedPattern
from app.services.cv_processor import CVProcessor
from app.services.screen_analyzer import ScreenActivityAnalyzer, ScreenEventType
from app.core.logging_config import get_logger
from app.core.redis_client import redis_client

logger = get_logger(__name__)

class ProctoringSessionManager:
    """
    Manages a single proctoring session lifecycle.
    Handles WebSocket communication, video stream processing, and event aggregation.
    Session data is stored in Redis for distributed access and persistence.
    """
    
    # Redis key prefixes
    SESSION_PREFIX = "proctor:session:"
    EVENTS_PREFIX = "proctor:events:"
    ACTIVE_SESSIONS_SET = "proctor:active_sessions"
    
    def __init__(self, session_id: str, user_id: str):
        self.session_id = session_id
        self.user_id = user_id
        self.start_time = time.time()
        self.is_active = True
        
        # Initialize analyzers
        self.behavior_analyzer = BehaviorAnalyzer(session_id)
        self.screen_analyzer = ScreenActivityAnalyzer(session_id)
        self.cv_processor = CVProcessor()
        
        # Storage references
        self.video_frames_count = 0
        self.redis_key = f"{self.SESSION_PREFIX}{session_id}"
        self.events_key = f"{self.EVENTS_PREFIX}{session_id}"
        
        # WebSocket
        self.websocket: Optional[WebSocket] = None
        
    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.websocket = websocket
        
        # Save session metadata to Redis
        await self._save_session_metadata()
        
        # Add to active sessions set
        if redis_client.is_connected:
            await redis_client.sadd(self.ACTIVE_SESSIONS_SET, self.session_id)
        
        logger.info("Session %s connected for user %s", self.session_id, self.user_id)
    
    async def _save_session_metadata(self):
        """Save session metadata to Redis."""
        if not redis_client.is_connected:
            return
            
        try:
            session_data = {
                "session_id": self.session_id,
                "user_id": self.user_id,
                "start_time": self.start_time,
                "is_active": self.is_active,
                "video_frames_count": self.video_frames_count,
            }
            await redis_client.set(self.redis_key, session_data, expire=3600)  # 1 hour TTL
        except Exception as e:
            logger.error("Failed to save session metadata: %s", str(e))
        
    async def start_monitoring(self):
        """Start the main monitoring loop."""
        try:
            logger.info("Starting monitoring for session %s", self.session_id)
            while self.is_active:
                # Receive data from client
                data = await self.websocket.receive_json()
                await self._process_message(data)
        except WebSocketDisconnect:
            logger.info("Client disconnected for session %s", self.session_id)
            self.is_active = False
        except Exception as e:
            logger.error("Error in session %s: %s", self.session_id, str(e), exc_info=True)
            self.is_active = False
            
    async def _process_message(self, data: Dict):
        """Route incoming messages to appropriate handlers."""
        msg_type = data.get("type")
        
        if msg_type == "video_frame":
            await self._handle_video_frame(data)
        elif msg_type == "screen_event":
            await self._handle_screen_event(data)
        elif msg_type == "heartbeat":
            await self._handle_heartbeat(data)
        elif msg_type == "consent_given":
            logger.info("Consent given for session %s", self.session_id)
            await self._send_confirmation("Consent recorded", "info")
        else:
            logger.warning("Unknown message type: %s for session %s", msg_type, self.session_id)
            
    async def _handle_video_frame(self, data: Dict):
        """Process base64 encoded video frame."""
        frame_data = data.get("frame")
        if not frame_data:
            return
            
        try:
            # Decode base64 image
            header, encoded = frame_data.split(",", 1)
            binary_data = base64.b64decode(encoded)
            
            # Convert to numpy array for OpenCV
            nparr = np.frombuffer(binary_data, np.uint8)
            frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            
            if frame is None:
                logger.warning("Failed to decode frame for session %s", self.session_id)
                return
                
            self.video_frames_count += 1
            
            # Process with CV
            detected_events = self.cv_processor.process_frame(frame)
            
            # Feed events to behavior analyzer and store in Redis
            for event in detected_events:
                event_data = {
                    "timestamp": event.timestamp,
                    "type": event.event_type,
                    "severity": event.severity.name,
                    "source": "cv"
                }
                
                # Store event in Redis list
                if redis_client.is_connected:
                    await redis_client.lpush(self.events_key, event_data)
                    # Keep only last 1000 events per session
                    await redis_client.client.ltrim(self.events_key, 0, 999)
                
                patterns = self.behavior_analyzer.add_event(event)
                
                # If high confidence pattern detected, alert client immediately
                for pattern in patterns:
                    if pattern.confidence > 0.8 or pattern.severity.value >= 3:
                        await self._send_alert(pattern)
            
            # Update frame count in Redis periodically
            if self.video_frames_count % 10 == 0 and redis_client.is_connected:
                await redis_client.hset(self.redis_key, "video_frames_count", self.video_frames_count)
                        
        except Exception as e:
            logger.error("Error processing video frame for session %s: %s", self.session_id, str(e), exc_info=True)

    async def _handle_screen_event(self, data: Dict):
        """Process screen activity events from client."""
        try:
            screen_events = self.screen_analyzer.process_event(data)
            
            for event in screen_events:
                event_data = {
                    "timestamp": event.timestamp,
                    "type": event.event_type.value,
                    "severity": event.severity_score,
                    "source": "screen",
                    "details": event.details
                }
                
                # Store event in Redis
                if redis_client.is_connected:
                    await redis_client.lpush(self.events_key, event_data)
                    # Keep only last 1000 events per session
                    await redis_client.client.ltrim(self.events_key, 0, 999)
                
                # Immediate feedback for critical screen events
                if event.severity_score >= 8:
                    await self._send_alert({
                        "type": "SCREEN_VIOLATION",
                        "description": f"Suspicious activity: {event.event_type.value}",
                        "severity": "HIGH"
                    })
        except Exception as e:
            logger.error("Error processing screen event for session %s: %s", self.session_id, str(e), exc_info=True)

    async def _handle_heartbeat(self, data: Dict):
        """Handle heartbeat and send back risk assessment."""
        risk_assessment = self.behavior_analyzer.get_risk_assessment()
        screen_risks = self.screen_analyzer.get_risk_factors()
        
        response = {
            "type": "heartbeat_ack",
            "risk_assessment": risk_assessment,
            "screen_stats": screen_risks,
            "session_duration": time.time() - self.start_time
        }
        await self.websocket.send_json(response)

    async def _send_alert(self, pattern: Dict):
        """Send immediate alert to client."""
        if self.websocket:
            await self.websocket.send_json({
                "type": "alert",
                "data": pattern
            })
            
    async def _send_confirmation(self, message: str, level: str = "info"):
        if self.websocket:
            await self.websocket.send_json({
                "type": "system_message",
                "message": message,
                "level": level
            })

    async def stop_session(self):
        """Gracefully stop the session and cleanup."""
        self.is_active = False
        
        # Update session status in Redis
        if redis_client.is_connected:
            await redis_client.hset(self.redis_key, "is_active", False)
            await redis_client.hset(self.redis_key, "end_time", time.time())
            
            # Remove from active sessions set
            await redis_client.srem(self.ACTIVE_SESSIONS_SET, self.session_id)
        
        if self.websocket:
            await self.websocket.close()
        self.cv_processor.release()
        
        # Generate final report
        final_report = self.generate_report()
        
        # Save final report to Redis
        if redis_client.is_connected:
            await redis_client.set(f"{self.redis_key}:report", final_report, expire=86400)  # 24 hours
        
        return final_report

    def generate_report(self) -> Dict:
        """Generate comprehensive session report."""
        risk_data = self.behavior_analyzer.get_risk_assessment()
        screen_data = self.screen_analyzer.get_risk_factors()
        
        return {
            "session_id": self.session_id,
            "user_id": self.user_id,
            "duration_seconds": time.time() - self.start_time,
            "frames_processed": self.video_frames_count,
            "risk_score": risk_data["risk_score"],
            "risk_level": risk_data["risk_level"],
            "events_summary": self._summarize_events(),
            "screen_activity": screen_data,
            "recommendation": risk_data["recommendation"]
        }
        
    async def _get_events_from_redis(self) -> List[Dict]:
        """Retrieve events from Redis for report generation."""
        if not redis_client.is_connected:
            return []
        
        try:
            # Get last 1000 events (most recent first, reverse for chronological order)
            events = await redis_client.lrange(self.events_key, 0, 999)
            return list(reversed(events))
        except Exception as e:
            logger.error("Failed to get events from Redis: %s", str(e))
            return []
        
    def _summarize_events(self) -> Dict:
        """Summarize events by type."""
        # For backward compatibility, still works without Redis
        # In production, use _get_events_from_redis()
        summary = {}
        
        # If Redis is available, fetch events from there
        if redis_client.is_connected:
            # We can't use async here, so this is a limitation
            # Events are counted during processing instead
            pass
        
        # Return summary based on behavior analyzer's internal state
        return self.behavior_analyzer.event_counts

# Global session store - now backed by Redis for distributed deployments
# In-memory cache for fast access, Redis for persistence
active_sessions: Dict[str, ProctoringSessionManager] = {}


async def create_session(session_id: str, user_id: str, websocket: WebSocket) -> ProctoringSessionManager:
    """Create a new proctoring session and store in Redis."""
    logger.info("Creating new session %s for user %s", session_id, user_id)
    
    # Check if session already exists in Redis
    if redis_client.is_connected:
        exists = await redis_client.exists(f"{ProctoringSessionManager.SESSION_PREFIX}{session_id}")
        if exists:
            logger.warning("Session %s already exists", session_id)
    
    session = ProctoringSessionManager(session_id, user_id)
    await session.connect(websocket)
    
    # Store in both memory and Redis
    active_sessions[session_id] = session
    
    logger.info("Session %s created successfully", session_id)
    return session


async def get_session(session_id: str) -> Optional[ProctoringSessionManager]:
    """
    Get session by ID.
    First checks in-memory cache, then falls back to Redis.
    """
    # Check in-memory cache first
    if session_id in active_sessions:
        return active_sessions[session_id]
    
    # If not in memory, check Redis
    if redis_client.is_connected:
        session_data = await redis_client.get(f"{ProctoringSessionManager.SESSION_PREFIX}{session_id}")
        if session_data:
            logger.info("Session %s found in Redis, recreating...", session_id)
            # Note: We can't fully recreate the session from Redis alone
            # as WebSocket connection and analyzers state are not serializable
            # This is mainly for metadata lookup
            return None
    
    return None


async def remove_session(session_id: str):
    """Remove and cleanup a session from both memory and Redis."""
    if session_id in active_sessions:
        logger.info("Removing session %s", session_id)
        session = active_sessions[session_id]
        await session.stop_session()
        del active_sessions[session_id]
    
    # Also clean up Redis data
    if redis_client.is_connected:
        redis_key = f"{ProctoringSessionManager.SESSION_PREFIX}{session_id}"
        events_key = f"{ProctoringSessionManager.EVENTS_PREFIX}{session_id}"
        
        # Remove session data and events
        deleted = await redis_client.delete(redis_key, f"{redis_key}:report", events_key)
        await redis_client.srem(ProctoringSessionManager.ACTIVE_SESSIONS_SET, session_id)
        
        if deleted > 0:
            logger.info("Removed %d Redis keys for session %s", deleted, session_id)
    
    logger.info("Session %s removed successfully", session_id)


async def get_active_session_ids() -> List[str]:
    """Get list of all active session IDs from Redis."""
    if redis_client.is_connected:
        sessions = await redis_client.smembers(ProctoringSessionManager.ACTIVE_SESSIONS_SET)
        return list(sessions)
    
    # Fallback to in-memory
    return list(active_sessions.keys())


async def get_session_count() -> int:
    """Get count of active sessions."""
    if redis_client.is_connected:
        # Get count from Redis set
        pipe = redis_client.client.pipeline()
        await pipe.scard(ProctoringSessionManager.ACTIVE_SESSIONS_SET)
        results = await pipe.execute()
        return results[0] if results else 0
    
    return len(active_sessions)
