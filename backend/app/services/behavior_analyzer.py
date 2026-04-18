"""
Advanced Behavior Analysis Module for Proctoring System
Implements pattern recognition similar to Coursera/ProctorU.
"""
import time
from typing import List, Dict, Optional
from dataclasses import dataclass, field
from enum import Enum
from collections import deque
import statistics

class SeverityLevel(Enum):
    LOW = 1
    MEDIUM = 2
    HIGH = 3
    CRITICAL = 4

class PatternType(Enum):
    SINGLE_EVENT = "single_event"
    FREQUENT_SWITCHING = "frequent_switching"
    PHONE_CHEATING = "phone_cheating"
    SECOND_PERSON = "second_person"
    ABSENCE_FRAUD = "absence_fraud"
    READING_OFF_SCREEN = "reading_off_screen"

@dataclass
class Event:
    timestamp: float
    event_type: str
    severity: SeverityLevel
    metadata: Dict = field(default_factory=dict)

@dataclass
class DetectedPattern:
    pattern_type: PatternType
    confidence: float  # 0.0 to 1.0
    severity: SeverityLevel
    start_time: float
    end_time: float
    description: str
    related_events: List[Event] = field(default_factory=list)

class BehaviorAnalyzer:
    """
    Analyzes streams of events to detect complex cheating patterns.
    Uses sliding windows and state machines.
    """
    
    def __init__(self, session_id: str):
        self.session_id = session_id
        self.event_buffer = deque(maxlen=500)  # Store last 500 events
        self.risk_score = 0.0
        self.max_risk_score = 100.0
        
        # Configuration thresholds
        self.window_size_seconds = 60.0
        self.switch_threshold = 3  # Switches per minute considered suspicious
        self.gaze_avoidance_threshold = 5.0  # Seconds
        self.absence_threshold = 10.0  # Seconds
        
        # State tracking
        self.last_face_seen_time: Optional[float] = None
        self.gaze_avoided_start: Optional[float] = None
        self.consecutive_switches = 0
        self.last_switch_time: Optional[float] = None
        
    def add_event(self, event: Event):
        """Ingest a new event and update analysis."""
        self.event_buffer.append(event)
        self._update_state(event)
        
        # Check for patterns periodically or on specific triggers
        if event.event_type in ['tab_switch', 'face_detected', 'face_lost', 'phone_detected']:
            patterns = self.analyze_patterns()
            return patterns
        return []

    def _update_state(self, event: Event):
        """Update internal state machine based on event."""
        now = event.timestamp
        
        # Face tracking state
        if event.event_type == 'face_detected':
            self.last_face_seen_time = now
            if self.gaze_avoided_start:
                duration = now - self.gaze_avoided_start
                if duration > self.gaze_avoidance_threshold:
                    self._increase_risk(15, "Prolonged gaze avoidance")
                self.gaze_avoided_start = None
                
        elif event.event_type == 'face_lost':
            if self.last_face_seen_time is None:
                self.last_face_seen_time = now # Initialize if first event
            # Start counting absence
            pass 
            
        elif event.event_type == 'gaze_avoided':
            if not self.gaze_avoided_start:
                self.gaze_avoided_start = now
            else:
                duration = now - self.gaze_avoided_start
                if duration > self.gaze_avoidance_threshold:
                    self._increase_risk(10, "Sustained gaze avoidance")

        # Tab switching state
        if event.event_type == 'tab_switch':
            if self.last_switch_time and (now - self.last_switch_time) < 5.0:
                self.consecutive_switches += 1
            else:
                self.consecutive_switches = 1
            self.last_switch_time = now
            
            if self.consecutive_switches >= self.switch_threshold:
                self._increase_risk(20, "Rapid tab switching pattern")

    def _increase_risk(self, amount: int, reason: str):
        self.risk_score = min(self.max_risk_score, self.risk_score + amount)
        print(f"[RISK] +{amount} ({self.risk_score:.1f}): {reason}")

    def analyze_patterns(self) -> List[DetectedPattern]:
        """Run pattern detection algorithms on the current buffer."""
        patterns = []
        now = time.time()
        window_start = now - self.window_size_seconds
        
        # Filter events in window
        window_events = [e for e in self.event_buffer if e.timestamp >= window_start]
        
        # 1. Detect "Phone Cheating" Pattern
        # Logic: Gaze down/away + Phone detected OR Hand movement near face
        phone_events = [e for e in window_events if e.event_type == 'phone_detected']
        gaze_events = [e for e in window_events if e.event_type in ['gaze_down', 'gaze_avoided']]
        
        if phone_events:
            # High confidence if phone is seen
            patterns.append(DetectedPattern(
                pattern_type=PatternType.PHONE_CHEATING,
                confidence=0.95,
                severity=SeverityLevel.HIGH,
                start_time=phone_events[0].timestamp,
                end_time=now,
                description="Mobile phone detected in frame while exam is active.",
                related_events=phone_events
            ))
            self._increase_risk(30, "Phone detected")

        # 2. Detect "Second Person / Consultant" Pattern
        # Logic: Multiple faces OR Face turns away repeatedly + Voice activity (if audio enabled)
        multi_face_events = [e for e in window_events if e.event_type == 'multi_face']
        if multi_face_events:
            patterns.append(DetectedPattern(
                pattern_type=PatternType.SECOND_PERSON,
                confidence=0.90,
                severity=SeverityLevel.CRITICAL,
                start_time=multi_face_events[0].timestamp,
                end_time=now,
                description="Multiple faces detected. Possible consultant presence.",
                related_events=multi_face_events
            ))
            self._increase_risk(40, "Second person detected")

        # 3. Detect "Off-Screen Reading" Pattern
        # Logic: Frequent head turns to same direction + No screen interaction
        head_turns = [e for e in window_events if e.event_type == 'head_turned']
        if len(head_turns) > 4: # More than 4 turns in a minute
            patterns.append(DetectedPattern(
                pattern_type=PatternType.READING_OFF_SCREEN,
                confidence=0.75,
                severity=SeverityLevel.MEDIUM,
                start_time=head_turns[0].timestamp,
                end_time=now,
                description="Repetitive head movements suggesting reading from off-screen notes.",
                related_events=head_turns
            ))
            self._increase_risk(15, "Suspicious head movement pattern")

        # 4. Detect "Absence Fraud" Pattern
        # Logic: Face lost for extended period but mouse/keyboard activity continues
        face_lost_events = [e for e in window_events if e.event_type == 'face_lost']
        input_events = [e for e in window_events if e.event_type in ['mouse_move', 'key_press']]
        
        if face_lost_events and input_events:
            # Check overlap
            if input_events[-1].timestamp > face_lost_events[0].timestamp:
                 patterns.append(DetectedPattern(
                    pattern_type=PatternType.ABSENCE_FRAUD,
                    confidence=0.85,
                    severity=SeverityLevel.HIGH,
                    start_time=face_lost_events[0].timestamp,
                    end_time=now,
                    description="User absent from camera but interacting with the system.",
                    related_events=face_lost_events + input_events[:5]
                ))
                 self._increase_risk(25, "Interaction without face")

        # 5. Detect "Frequent Switching" Pattern (already partially handled in state, but refined here)
        switch_events = [e for e in window_events if e.event_type == 'tab_switch']
        if len(switch_events) >= self.switch_threshold:
             patterns.append(DetectedPattern(
                pattern_type=PatternType.FREQUENT_SWITCHING,
                confidence=0.80,
                severity=SeverityLevel.MEDIUM,
                start_time=switch_events[0].timestamp,
                end_time=now,
                description=f"Excessive tab switching detected ({len(switch_events)} times in 1 min).",
                related_events=switch_events
            ))

        return patterns

    def get_risk_assessment(self) -> Dict:
        """Return current risk assessment."""
        level = "LOW"
        if self.risk_score > 80:
            level = "CRITICAL"
        elif self.risk_score > 50:
            level = "HIGH"
        elif self.risk_score > 20:
            level = "MEDIUM"
            
        return {
            "session_id": self.session_id,
            "risk_score": self.risk_score,
            "risk_level": level,
            "recommendation": "TERMINATE" if level == "CRITICAL" else "MONITOR",
            "timestamp": time.time()
        }
