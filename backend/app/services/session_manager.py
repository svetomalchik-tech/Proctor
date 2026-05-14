"""
Session Manager Module
Orchestrates video processing, screen monitoring, and event logging.
"""
import asyncio
import json
import base64
import time
from typing import Dict, Optional
from fastapi import WebSocket, WebSocketDisconnect
import cv2
import numpy as np

from app.services.behavior_analyzer import BehaviorAnalyzer, Event, SeverityLevel, DetectedPattern
from app.services.cv_processor import CVProcessor
from app.services.screen_analyzer import ScreenActivityAnalyzer, ScreenEventType
from app.core.logging_config import get_logger

logger = get_logger(__name__)

class ProctoringSessionManager:
    """
    Manages a single proctoring session lifecycle.
    Handles WebSocket communication, video stream processing, and event aggregation.
    """
    
    def __init__(self, session_id: str, user_id: str):
        self.session_id = session_id
        self.user_id = user_id
        self.start_time = time.time()
        self.is_active = True
        
        # Initialize analyzers
        self.behavior_analyzer = BehaviorAnalyzer(session_id)
        self.screen_analyzer = ScreenActivityAnalyzer(session_id)
        self.cv_processor = CVProcessor()
        
        # Storage references (mocked for now)
        self.video_frames_count = 0
        self.events_log = []
        
        # WebSocket
        self.websocket: Optional[WebSocket] = None
        
    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.websocket = websocket
        logger.info("Session %s connected for user %s", self.session_id, self.user_id)
        
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
            
            # Feed events to behavior analyzer
            for event in detected_events:
                self.events_log.append({
                    "timestamp": event.timestamp,
                    "type": event.event_type,
                    "severity": event.severity.name,
                    "source": "cv"
                })
                
                patterns = self.behavior_analyzer.add_event(event)
                
                # If high confidence pattern detected, alert client immediately
                for pattern in patterns:
                    if pattern.confidence > 0.8 or pattern.severity.value >= 3:
                        await self._send_alert(pattern)
                        
        except Exception as e:
            logger.error("Error processing video frame for session %s: %s", self.session_id, str(e), exc_info=True)

    async def _handle_screen_event(self, data: Dict):
        """Process screen activity events from client."""
        try:
            screen_events = self.screen_analyzer.process_event(data)
            
            for event in screen_events:
                self.events_log.append({
                    "timestamp": event.timestamp,
                    "type": event.event_type.value,
                    "severity": event.severity_score,
                    "source": "screen",
                    "details": event.details
                })
                
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
        if self.websocket:
            await self.websocket.close()
        self.cv_processor.release()
        
        # Generate final report
        final_report = self.generate_report()
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
            "total_events": len(self.events_log),
            "risk_score": risk_data["risk_score"],
            "risk_level": risk_data["risk_level"],
            "events_summary": self._summarize_events(),
            "screen_activity": screen_data,
            "recommendation": risk_data["recommendation"]
        }
        
    def _summarize_events(self) -> Dict:
        """Summarize events by type."""
        summary = {}
        for event in self.events_log:
            etype = event["type"]
            summary[etype] = summary.get(etype, 0) + 1
        return summary

# Global session store (In production, use Redis)
active_sessions: Dict[str, ProctoringSessionManager] = {}

async def create_session(session_id: str, user_id: str, websocket: WebSocket) -> ProctoringSessionManager:
    """Create a new proctoring session"""
    logger.info("Creating new session %s for user %s", session_id, user_id)
    session = ProctoringSessionManager(session_id, user_id)
    await session.connect(websocket)
    active_sessions[session_id] = session
    return session

def get_session(session_id: str) -> Optional[ProctoringSessionManager]:
    """Get session by ID"""
    return active_sessions.get(session_id)

async def remove_session(session_id: str):
    """Remove and cleanup a session"""
    if session_id in active_sessions:
        logger.info("Removing session %s", session_id)
        session = active_sessions[session_id]
        await session.stop_session()
        del active_sessions[session_id]
        logger.info("Session %s removed successfully", session_id)
