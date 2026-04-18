"""
Screen Activity Monitor
Detects tab switching, window focus loss, and suspicious application usage.
Integrates with browser events via WebSocket.
"""
import time
from typing import Dict, List, Optional
from dataclasses import dataclass
from enum import Enum

class ScreenEventType(Enum):
    TAB_SWITCH = "tab_switch"
    WINDOW_BLUR = "window_blur"
    FULLSCREEN_EXIT = "fullscreen_exit"
    CLIPBOARD_COPY = "clipboard_copy"
    PRINT_SCREEN = "print_screen"
    DEVTOOLS_OPEN = "devtools_open"
    MULTI_MONITOR = "multi_monitor"
    SUSPICIOUS_APP = "suspicious_app"

@dataclass
class ScreenEvent:
    timestamp: float
    event_type: ScreenEventType
    details: Dict
    severity_score: int  # 1-10

class ScreenActivityAnalyzer:
    """
    Analyzes screen-related events sent from the client.
    Detects patterns of cheating via screen manipulation.
    """
    
    def __init__(self, session_id: str):
        self.session_id = session_id
        self.events: List[ScreenEvent] = []
        self.start_time = time.time()
        
        # Configuration
        self.allowed_apps = ["chrome", "firefox", "edge", "safari", "exam_client"]
        self.blocked_keywords = ["telegram", "whatsapp", "skype", "discord", "notion", "google docs"]
        
        # State
        self.tab_switch_count = 0
        self.last_tab_switch_time = 0
        self.focus_lost_start: Optional[float] = None
        self.fullscreen_state = True
        
    def process_event(self, event_data: Dict) -> List[ScreenEvent]:
        """
        Process raw event data from frontend.
        Returns list of generated ScreenEvents.
        """
        generated_events = []
        now = time.time()
        event_type_str = event_data.get("type")
        
        # Map string types to Enum
        try:
            event_type = ScreenEventType(event_type_str)
        except ValueError:
            return [] # Unknown event type
            
        details = event_data.get("details", {})
        
        # Calculate severity based on context
        severity = self._calculate_severity(event_type, details, now)
        
        screen_event = ScreenEvent(
            timestamp=now,
            event_type=event_type,
            details=details,
            severity_score=severity
        )
        
        self.events.append(screen_event)
        generated_events.append(screen_event)
        
        # Update state machines
        self._update_state(screen_event, now)
        
        return generated_events

    def _calculate_severity(self, event_type: ScreenEventType, details: Dict, now: float) -> int:
        """
        Determine severity score (1-10) based on event type and context.
        """
        base_scores = {
            ScreenEventType.TAB_SWITCH: 3,
            ScreenEventType.WINDOW_BLUR: 4,
            ScreenEventType.FULLSCREEN_EXIT: 6,
            ScreenEventType.CLIPBOARD_COPY: 2,
            ScreenEventType.PRINT_SCREEN: 8,
            ScreenEventType.DEVTOOLS_OPEN: 9,
            ScreenEventType.MULTI_MONITOR: 5,
            ScreenEventType.SUSPICIOUS_APP: 7
        }
        
        score = base_scores.get(event_type, 5)
        
        # Contextual adjustments
        if event_type == ScreenEventType.TAB_SWITCH:
            # Higher severity if rapid switching
            if now - self.last_tab_switch_time < 2.0:
                score += 2
                
        if event_type == ScreenEventType.SUSPICIOUS_APP:
            app_name = details.get("app_name", "").lower()
            if any(kw in app_name for kw in ["telegram", "whatsapp"]):
                score = 10 # Critical
        
        return min(score, 10)

    def _update_state(self, event: ScreenEvent, now: float):
        """Update internal state for pattern detection."""
        
        if event.event_type == ScreenEventType.TAB_SWITCH:
            if now - self.last_tab_switch_time < 5.0:
                self.tab_switch_count += 1
            else:
                self.tab_switch_count = 1
            self.last_tab_switch_time = now
            
        elif event.event_type == ScreenEventType.WINDOW_BLUR:
            self.focus_lost_start = now
            
        elif event.event_type == ScreenEventType.FULLSCREEN_EXIT:
            self.fullscreen_state = False
            
        # Auto-reset focus if focus gained event comes (handled by client usually)
        # Assuming client sends 'window_focus' event too if implemented

    def get_risk_factors(self) -> Dict:
        """
        Analyze accumulated events to return risk factors.
        """
        now = time.time()
        duration = now - self.start_time
        minutes = duration / 60.0 if duration > 0 else 1.0
        
        # Calculate rates
        switch_rate = self.tab_switch_count / minutes
        
        risk_factors = {
            "tab_switch_rate_per_min": round(switch_rate, 2),
            "total_blur_events": len([e for e in self.events if e.event_type == ScreenEventType.WINDOW_BLUR]),
            "fullscreen_violations": len([e for e in self.events if e.event_type == ScreenEventType.FULLSCREEN_EXIT]),
            "suspicious_apps_detected": len([e for e in self.events if e.event_type == ScreenEventType.SUSPICIOUS_APP]),
            "high_severity_count": len([e for e in self.events if e.severity_score >= 7])
        }
        
        # Add qualitative assessment
        if switch_rate > 5:
            risk_factors["warning"] = "Excessive tab switching detected"
        if risk_factors["suspicious_apps_detected"] > 0:
            risk_factors["warning"] = "Forbidden applications detected"
            
        return risk_factors

    def is_allowed_app(self, app_name: str) -> bool:
        """Check if application is in allowed list."""
        name_lower = app_name.lower()
        if any(blocked in name_lower for blocked in self.blocked_keywords):
            return False
        return True
