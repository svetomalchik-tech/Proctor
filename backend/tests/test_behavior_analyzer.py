"""
Unit Tests for Behavior Analyzer Module
Tests pattern detection, risk scoring, and event processing.
"""
import pytest
import time
from app.services.behavior_analyzer import (
    BehaviorAnalyzer, Event, SeverityLevel, 
    PatternType, DetectedPattern
)


class TestEvent:
    """Test Event dataclass creation and properties."""
    
    def test_create_event_basic(self):
        """Test creating a basic event with required fields."""
        event = Event(
            timestamp=1234567890.0,
            event_type="face_detected",
            severity=SeverityLevel.LOW
        )
        
        assert event.timestamp == 1234567890.0
        assert event.event_type == "face_detected"
        assert event.severity == SeverityLevel.LOW
        assert event.metadata == {}
    
    def test_create_event_with_metadata(self):
        """Test creating an event with metadata."""
        event = Event(
            timestamp=time.time(),
            event_type="tab_switch",
            severity=SeverityLevel.MEDIUM,
            metadata={"url": "https://google.com", "count": 1}
        )
        
        assert event.metadata["url"] == "https://google.com"
        assert event.metadata["count"] == 1
    
    def test_severity_levels(self):
        """Test all severity level values."""
        assert SeverityLevel.LOW.value == 1
        assert SeverityLevel.MEDIUM.value == 2
        assert SeverityLevel.HIGH.value == 3
        assert SeverityLevel.CRITICAL.value == 4


class TestBehaviorAnalyzerInitialization:
    """Test BehaviorAnalyzer initialization and default state."""
    
    def test_init_default_values(self):
        """Test analyzer initializes with correct default values."""
        analyzer = BehaviorAnalyzer("test_session_123")
        
        assert analyzer.session_id == "test_session_123"
        assert analyzer.risk_score == 0.0
        assert analyzer.max_risk_score == 100.0
        assert analyzer.window_size_seconds == 60.0
        assert analyzer.switch_threshold == 3
        assert len(analyzer.event_buffer) == 0
    
    def test_init_state_variables(self):
        """Test initial state variables are None or zero."""
        analyzer = BehaviorAnalyzer("session_456")
        
        assert analyzer.last_face_seen_time is None
        assert analyzer.gaze_avoided_start is None
        assert analyzer.consecutive_switches == 0
        assert analyzer.last_switch_time is None


class TestBehaviorAnalyzerRiskScoring:
    """Test risk score calculation and updates."""
    
    def test_initial_risk_assessment(self):
        """Test risk assessment returns LOW for zero risk score."""
        analyzer = BehaviorAnalyzer("test_session")
        assessment = analyzer.get_risk_assessment()
        
        assert assessment["risk_score"] == 0.0
        assert assessment["risk_level"] == "LOW"
        assert assessment["recommendation"] == "MONITOR"
        assert assessment["session_id"] == "test_session"
    
    def test_risk_score_increase(self):
        """Test that risk score increases correctly."""
        analyzer = BehaviorAnalyzer("test_session")
        
        # Manually increase risk (simulating internal behavior)
        analyzer._increase_risk(15, "Test reason")
        
        assert analyzer.risk_score == 15.0
    
    def test_risk_score_capped_at_max(self):
        """Test that risk score doesn't exceed maximum."""
        analyzer = BehaviorAnalyzer("test_session")
        
        # Try to add more than max
        analyzer._increase_risk(120, "Test reason")
        
        assert analyzer.risk_score == 100.0  # Capped at max_risk_score
    
    def test_risk_level_medium(self):
        """Test MEDIUM risk level (20-50)."""
        analyzer = BehaviorAnalyzer("test_session")
        analyzer._increase_risk(25, "Test")
        
        assessment = analyzer.get_risk_assessment()
        assert assessment["risk_level"] == "MEDIUM"
    
    def test_risk_level_high(self):
        """Test HIGH risk level (50-80)."""
        analyzer = BehaviorAnalyzer("test_session")
        analyzer._increase_risk(55, "Test")
        
        assessment = analyzer.get_risk_assessment()
        assert assessment["risk_level"] == "HIGH"
    
    def test_risk_level_critical(self):
        """Test CRITICAL risk level (>80)."""
        analyzer = BehaviorAnalyzer("test_session")
        analyzer._increase_risk(85, "Test")
        
        assessment = analyzer.get_risk_assessment()
        assert assessment["risk_level"] == "CRITICAL"
        assert assessment["recommendation"] == "TERMINATE"


class TestFaceDetectionEvents:
    """Test face detection event handling."""
    
    def test_face_detected_event(self):
        """Test processing face_detected event."""
        analyzer = BehaviorAnalyzer("test_session")
        
        event = Event(
            timestamp=time.time(),
            event_type="face_detected",
            severity=SeverityLevel.LOW
        )
        
        patterns = analyzer.add_event(event)
        
        assert analyzer.last_face_seen_time is not None
        assert len(patterns) == 0  # Single face detection shouldn't trigger patterns
    
    def test_face_lost_event(self):
        """Test processing face_lost event."""
        analyzer = BehaviorAnalyzer("test_session")
        
        event = Event(
            timestamp=time.time(),
            event_type="face_lost",
            severity=SeverityLevel.MEDIUM
        )
        
        patterns = analyzer.add_event(event)
        
        # Face lost alone doesn't trigger immediate patterns
        assert len(patterns) == 0
    
    def test_multi_face_detection(self):
        """Test multi_face event triggers pattern."""
        analyzer = BehaviorAnalyzer("test_session")
        
        event = Event(
            timestamp=time.time(),
            event_type="multi_face",
            severity=SeverityLevel.CRITICAL,
            metadata={"count": 2}
        )
        
        patterns = analyzer.add_event(event)
        
        # Should detect second person pattern
        assert len(patterns) > 0
        assert any(p.pattern_type == PatternType.SECOND_PERSON for p in patterns)
        
        # Risk should increase significantly
        assert analyzer.risk_score >= 40


class TestGazeTrackingEvents:
    """Test gaze tracking and avoidance detection."""
    
    def test_gaze_avoided_event(self):
        """Test gaze_avoided event processing."""
        analyzer = BehaviorAnalyzer("test_session")
        
        event = Event(
            timestamp=time.time(),
            event_type="gaze_avoided",
            severity=SeverityLevel.MEDIUM
        )
        
        patterns = analyzer.add_event(event)
        
        assert analyzer.gaze_avoided_start is not None
    
    def test_gaze_down_event(self):
        """Test gaze_down event processing."""
        analyzer = BehaviorAnalyzer("test_session")
        
        event = Event(
            timestamp=time.time(),
            event_type="gaze_down",
            severity=SeverityLevel.LOW
        )
        
        patterns = analyzer.add_event(event)
        
        # Gaze down alone doesn't start avoidance timer
        assert analyzer.gaze_avoided_start is None


class TestTabSwitchingEvents:
    """Test tab switching pattern detection."""
    
    def test_single_tab_switch(self):
        """Test single tab switch event."""
        analyzer = BehaviorAnalyzer("test_session")
        
        event = Event(
            timestamp=time.time(),
            event_type="tab_switch",
            severity=SeverityLevel.MEDIUM
        )
        
        patterns = analyzer.add_event(event)
        
        assert analyzer.consecutive_switches == 1
        assert analyzer.last_switch_time is not None
    
    def test_rapid_tab_switching_pattern(self):
        """Test rapid tab switching triggers pattern."""
        analyzer = BehaviorAnalyzer("test_session")
        base_time = time.time()
        
        # Simulate 3 rapid switches within 5 seconds
        for i in range(3):
            event = Event(
                timestamp=base_time + (i * 1.0),  # 1 second apart
                event_type="tab_switch",
                severity=SeverityLevel.MEDIUM
            )
            patterns = analyzer.add_event(event)
        
        # Should detect frequent switching pattern
        assert len(patterns) > 0
        assert any(p.pattern_type == PatternType.FREQUENT_SWITCHING for p in patterns)
        
        # Risk should increase
        assert analyzer.risk_score >= 20
    
    def test_slow_tab_switching_no_pattern(self):
        """Test slow tab switching doesn't trigger pattern."""
        analyzer = BehaviorAnalyzer("test_session")
        base_time = time.time()
        
        # Simulate 3 switches with large gaps (>5 seconds)
        for i in range(3):
            event = Event(
                timestamp=base_time + (i * 10.0),  # 10 seconds apart
                event_type="tab_switch",
                severity=SeverityLevel.MEDIUM
            )
            patterns = analyzer.add_event(event)
        
        # Counter resets between switches
        assert analyzer.consecutive_switches == 1


class TestPhoneCheatingPattern:
    """Test phone cheating detection pattern."""
    
    def test_phone_detected_triggers_pattern(self):
        """Test phone_detected event triggers high confidence pattern."""
        analyzer = BehaviorAnalyzer("test_session")
        
        event = Event(
            timestamp=time.time(),
            event_type="phone_detected",
            severity=SeverityLevel.HIGH
        )
        
        patterns = analyzer.add_event(event)
        
        assert len(patterns) > 0
        phone_patterns = [p for p in patterns if p.pattern_type == PatternType.PHONE_CHEATING]
        assert len(phone_patterns) > 0
        
        # Phone cheating should have high confidence
        assert phone_patterns[0].confidence >= 0.90
        assert phone_patterns[0].severity == SeverityLevel.HIGH
        
        # Risk should increase significantly
        assert analyzer.risk_score >= 30


class TestHeadTurnPattern:
    """Test head turn / reading off-screen pattern."""
    
    def test_multiple_head_turns_triggers_pattern(self):
        """Test multiple head turns suggest reading off-screen."""
        analyzer = BehaviorAnalyzer("test_session")
        base_time = time.time()
        
        # Simulate 5 head turns within a minute
        for i in range(5):
            event = Event(
                timestamp=base_time + (i * 10.0),
                event_type="head_turned",
                severity=SeverityLevel.MEDIUM
            )
            patterns = analyzer.add_event(event)
        
        # Should detect reading off-screen pattern
        assert len(patterns) > 0
        reading_patterns = [p for p in patterns if p.pattern_type == PatternType.READING_OFF_SCREEN]
        assert len(reading_patterns) > 0
        
        # Risk should increase
        assert analyzer.risk_score >= 15


class TestAbsenceFraudPattern:
    """Test absence fraud detection (interaction without face)."""
    
    def test_face_lost_with_input_triggers_pattern(self):
        """Test face_lost + input events trigger absence fraud pattern."""
        analyzer = BehaviorAnalyzer("test_session")
        base_time = time.time()
        
        # First lose face
        face_lost_event = Event(
            timestamp=base_time,
            event_type="face_lost",
            severity=SeverityLevel.MEDIUM
        )
        analyzer.add_event(face_lost_event)
        
        # Then simulate input activity
        input_event = Event(
            timestamp=base_time + 2.0,
            event_type="key_press",
            severity=SeverityLevel.LOW
        )
        patterns = analyzer.add_event(input_event)
        
        # Should detect absence fraud
        assert len(patterns) > 0
        fraud_patterns = [p for p in patterns if p.pattern_type == PatternType.ABSENCE_FRAUD]
        assert len(fraud_patterns) > 0
        
        # Risk should increase
        assert analyzer.risk_score >= 25


class TestDetectedPatternDataclass:
    """Test DetectedPattern dataclass."""
    
    def test_create_pattern(self):
        """Test creating a DetectedPattern instance."""
        pattern = DetectedPattern(
            pattern_type=PatternType.PHONE_CHEATING,
            confidence=0.95,
            severity=SeverityLevel.HIGH,
            start_time=time.time(),
            end_time=time.time(),
            description="Phone detected",
            related_events=[]
        )
        
        assert pattern.pattern_type == PatternType.PHONE_CHEATING
        assert pattern.confidence == 0.95
        assert pattern.severity == SeverityLevel.HIGH
        assert pattern.description == "Phone detected"
    
    def test_pattern_with_related_events(self):
        """Test pattern with related events list."""
        events = [
            Event(timestamp=time.time(), event_type="phone_detected", severity=SeverityLevel.HIGH)
        ]
        
        pattern = DetectedPattern(
            pattern_type=PatternType.PHONE_CHEATING,
            confidence=0.95,
            severity=SeverityLevel.HIGH,
            start_time=time.time(),
            end_time=time.time(),
            description="Phone detected",
            related_events=events
        )
        
        assert len(pattern.related_events) == 1
        assert pattern.related_events[0].event_type == "phone_detected"


class TestEventBufferManagement:
    """Test event buffer management and cleanup."""
    
    def test_event_buffer_stores_events(self):
        """Test that events are stored in buffer."""
        analyzer = BehaviorAnalyzer("test_session")
        
        # Add multiple events
        for i in range(10):
            event = Event(
                timestamp=time.time(),
                event_type=f"event_{i}",
                severity=SeverityLevel.LOW
            )
            analyzer.add_event(event)
        
        assert len(analyzer.event_buffer) == 10
    
    def test_event_buffer_max_size(self):
        """Test that buffer respects max size limit."""
        analyzer = BehaviorAnalyzer("test_session")
        
        # Add more events than buffer max (500)
        for i in range(600):
            event = Event(
                timestamp=time.time(),
                event_type=f"event_{i}",
                severity=SeverityLevel.LOW
            )
            analyzer.add_event(event)
        
        # Buffer should be capped at maxlen
        assert len(analyzer.event_buffer) == 500


class TestPatternTypeEnumeration:
    """Test PatternType enum values."""
    
    def test_all_pattern_types_exist(self):
        """Test all expected pattern types are defined."""
        assert PatternType.SINGLE_EVENT.value == "single_event"
        assert PatternType.FREQUENT_SWITCHING.value == "frequent_switching"
        assert PatternType.PHONE_CHEATING.value == "phone_cheating"
        assert PatternType.SECOND_PERSON.value == "second_person"
        assert PatternType.ABSENCE_FRAUD.value == "absence_fraud"
        assert PatternType.READING_OFF_SCREEN.value == "reading_off_screen"


class TestEdgeCases:
    """Test edge cases and error handling."""
    
    def test_empty_buffer_analysis(self):
        """Test analyzing patterns with empty buffer."""
        analyzer = BehaviorAnalyzer("test_session")
        
        patterns = analyzer.analyze_patterns()
        
        assert patterns == []
    
    def test_unknown_event_type(self):
        """Test handling unknown event types."""
        analyzer = BehaviorAnalyzer("test_session")
        
        event = Event(
            timestamp=time.time(),
            event_type="unknown_event_type",
            severity=SeverityLevel.LOW
        )
        
        # Should not crash, just won't trigger specific patterns
        patterns = analyzer.add_event(event)
        
        # Unknown events don't trigger pattern analysis
        assert patterns == []
    
    def test_concurrent_sessions_isolation(self):
        """Test that different sessions are isolated."""
        analyzer1 = BehaviorAnalyzer("session_1")
        analyzer2 = BehaviorAnalyzer("session_2")
        
        # Add events to first session
        event = Event(
            timestamp=time.time(),
            event_type="phone_detected",
            severity=SeverityLevel.HIGH
        )
        analyzer1.add_event(event)
        
        # Second session should be unaffected
        assert analyzer2.risk_score == 0.0
        assert len(analyzer2.event_buffer) == 0
        
        # First session should have increased risk
        assert analyzer1.risk_score > 0
