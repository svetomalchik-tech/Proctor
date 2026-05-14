"""
Unit Tests for Screen Activity Analyzer Module
Tests screen event processing, severity calculation, and risk factors.
"""
import pytest
import time
from app.services.screen_analyzer import (
    ScreenActivityAnalyzer, ScreenEvent, ScreenEventType
)


class TestScreenEventType:
    """Test ScreenEventType enum values."""
    
    def test_all_event_types_exist(self):
        """Test all expected screen event types are defined."""
        assert ScreenEventType.TAB_SWITCH.value == "tab_switch"
        assert ScreenEventType.WINDOW_BLUR.value == "window_blur"
        assert ScreenEventType.FULLSCREEN_EXIT.value == "fullscreen_exit"
        assert ScreenEventType.CLIPBOARD_COPY.value == "clipboard_copy"
        assert ScreenEventType.PRINT_SCREEN.value == "print_screen"
        assert ScreenEventType.DEVTOOLS_OPEN.value == "devtools_open"
        assert ScreenEventType.MULTI_MONITOR.value == "multi_monitor"
        assert ScreenEventType.SUSPICIOUS_APP.value == "suspicious_app"


class TestScreenEventDataclass:
    """Test ScreenEvent dataclass creation and properties."""
    
    def test_create_screen_event(self):
        """Test creating a basic screen event."""
        event = ScreenEvent(
            timestamp=1234567890.0,
            event_type=ScreenEventType.TAB_SWITCH,
            details={"url": "https://google.com"},
            severity_score=5
        )
        
        assert event.timestamp == 1234567890.0
        assert event.event_type == ScreenEventType.TAB_SWITCH
        assert event.details["url"] == "https://google.com"
        assert event.severity_score == 5
    
    def test_screen_event_empty_details(self):
        """Test creating screen event with empty details."""
        event = ScreenEvent(
            timestamp=time.time(),
            event_type=ScreenEventType.WINDOW_BLUR,
            details={},
            severity_score=3
        )
        
        assert event.details == {}
        assert event.severity_score == 3


class TestScreenAnalyzerInitialization:
    """Test ScreenActivityAnalyzer initialization."""
    
    def test_init_default_values(self):
        """Test analyzer initializes with correct defaults."""
        analyzer = ScreenActivityAnalyzer("test_session_123")
        
        assert analyzer.session_id == "test_session_123"
        assert len(analyzer.events) == 0
        assert analyzer.tab_switch_count == 0
        assert analyzer.last_tab_switch_time == 0
        assert analyzer.focus_lost_start is None
        assert analyzer.fullscreen_state is True
    
    def test_init_allowed_apps(self):
        """Test allowed apps list is configured."""
        analyzer = ScreenActivityAnalyzer("test_session")
        
        assert "chrome" in analyzer.allowed_apps
        assert "firefox" in analyzer.allowed_apps
        assert "edge" in analyzer.allowed_apps
    
    def test_init_blocked_keywords(self):
        """Test blocked keywords list is configured."""
        analyzer = ScreenActivityAnalyzer("test_session")
        
        assert "telegram" in analyzer.blocked_keywords
        assert "whatsapp" in analyzer.blocked_keywords
        assert "discord" in analyzer.blocked_keywords


class TestScreenEventProcessing:
    """Test screen event processing functionality."""
    
    def test_process_tab_switch_event(self):
        """Test processing tab switch event."""
        analyzer = ScreenActivityAnalyzer("test_session")
        
        event_data = {
            "type": "tab_switch",
            "details": {"from_url": "exam.com", "to_url": "google.com"}
        }
        
        events = analyzer.process_event(event_data)
        
        assert len(events) == 1
        assert events[0].event_type == ScreenEventType.TAB_SWITCH
        assert analyzer.tab_switch_count == 1
    
    def test_process_window_blur_event(self):
        """Test processing window blur event."""
        analyzer = ScreenActivityAnalyzer("test_session")
        
        event_data = {
            "type": "window_blur",
            "details": {"reason": "user_switched_app"}
        }
        
        events = analyzer.process_event(event_data)
        
        assert len(events) == 1
        assert events[0].event_type == ScreenEventType.WINDOW_BLUR
        assert analyzer.focus_lost_start is not None
    
    def test_process_fullscreen_exit_event(self):
        """Test processing fullscreen exit event."""
        analyzer = ScreenActivityAnalyzer("test_session")
        
        event_data = {
            "type": "fullscreen_exit",
            "details": {}
        }
        
        events = analyzer.process_event(event_data)
        
        assert len(events) == 1
        assert events[0].event_type == ScreenEventType.FULLSCREEN_EXIT
        assert analyzer.fullscreen_state is False
    
    def test_process_unknown_event_type(self):
        """Test processing unknown event type returns empty list."""
        analyzer = ScreenActivityAnalyzer("test_session")
        
        event_data = {
            "type": "unknown_event",
            "details": {}
        }
        
        events = analyzer.process_event(event_data)
        
        assert events == []
        assert len(analyzer.events) == 0
    
    def test_process_multiple_events(self):
        """Test processing multiple events accumulates correctly."""
        analyzer = ScreenActivityAnalyzer("test_session")
        
        for i in range(5):
            event_data = {
                "type": "tab_switch",
                "details": {"count": i}
            }
            analyzer.process_event(event_data)
        
        assert len(analyzer.events) == 5
        assert analyzer.tab_switch_count >= 1


class TestSeverityCalculation:
    """Test severity score calculation."""
    
    def test_base_severity_tab_switch(self):
        """Test base severity for tab switch."""
        analyzer = ScreenActivityAnalyzer("test_session")
        
        event_data = {
            "type": "tab_switch",
            "details": {}
        }
        
        events = analyzer.process_event(event_data)
        
        # Base score for tab_switch is 3
        assert events[0].severity_score >= 3
    
    def test_base_severity_devtools_open(self):
        """Test high severity for devtools open."""
        analyzer = ScreenActivityAnalyzer("test_session")
        
        event_data = {
            "type": "devtools_open",
            "details": {}
        }
        
        events = analyzer.process_event(event_data)
        
        # DevTools should have high severity (9)
        assert events[0].severity_score >= 8
    
    def test_base_severity_print_screen(self):
        """Test high severity for print screen."""
        analyzer = ScreenActivityAnalyzer("test_session")
        
        event_data = {
            "type": "print_screen",
            "details": {}
        }
        
        events = analyzer.process_event(event_data)
        
        # Print screen should have high severity (8)
        assert events[0].severity_score >= 7
    
    def test_rapid_tab_switching_increases_severity(self):
        """Test rapid tab switching increases severity."""
        analyzer = ScreenActivityAnalyzer("test_session")
        
        # First tab switch
        event_data1 = {"type": "tab_switch", "details": {}}
        events1 = analyzer.process_event(event_data1)
        first_severity = events1[0].severity_score
        
        # Immediate second tab switch (within 2 seconds)
        event_data2 = {"type": "tab_switch", "details": {}}
        events2 = analyzer.process_event(event_data2)
        second_severity = events2[0].severity_score
        
        # Second should be higher due to rapid switching
        assert second_severity >= first_severity
    
    def test_suspicious_app_max_severity(self):
        """Test suspicious app with blocked keyword gets max severity."""
        analyzer = ScreenActivityAnalyzer("test_session")
        
        event_data = {
            "type": "suspicious_app",
            "details": {"app_name": "Telegram Desktop"}
        }
        
        events = analyzer.process_event(event_data)
        
        # Telegram should trigger max severity (10)
        assert events[0].severity_score == 10


class TestRiskFactors:
    """Test risk factors calculation."""
    
    def test_initial_risk_factors(self):
        """Test initial risk factors are zero or low."""
        analyzer = ScreenActivityAnalyzer("test_session")
        
        risk_factors = analyzer.get_risk_factors()
        
        assert risk_factors["tab_switch_rate_per_min"] == 0.0
        assert risk_factors["total_blur_events"] == 0
        assert risk_factors["fullscreen_violations"] == 0
        assert risk_factors["suspicious_apps_detected"] == 0
        assert risk_factors["high_severity_count"] == 0
    
    def test_risk_factors_after_tab_switches(self):
        """Test risk factors update after tab switches."""
        analyzer = ScreenActivityAnalyzer("test_session")
        
        # Add several tab switches
        for _ in range(5):
            event_data = {"type": "tab_switch", "details": {}}
            analyzer.process_event(event_data)
        
        risk_factors = analyzer.get_risk_factors()
        
        assert risk_factors["tab_switch_rate_per_min"] > 0
        assert "warning" in risk_factors  # Should warn about excessive switching
    
    def test_risk_factors_after_blur_events(self):
        """Test risk factors count blur events."""
        analyzer = ScreenActivityAnalyzer("test_session")
        
        # Add blur events
        for _ in range(3):
            event_data = {"type": "window_blur", "details": {}}
            analyzer.process_event(event_data)
        
        risk_factors = analyzer.get_risk_factors()
        
        assert risk_factors["total_blur_events"] == 3
    
    def test_risk_factors_after_fullscreen_violations(self):
        """Test risk factors count fullscreen violations."""
        analyzer = ScreenActivityAnalyzer("test_session")
        
        # Add fullscreen exit events
        for _ in range(2):
            event_data = {"type": "fullscreen_exit", "details": {}}
            analyzer.process_event(event_data)
        
        risk_factors = analyzer.get_risk_factors()
        
        assert risk_factors["fullscreen_violations"] == 2
    
    def test_risk_factors_high_severity_count(self):
        """Test risk factors count high severity events."""
        analyzer = ScreenActivityAnalyzer("test_session")
        
        # Add high severity events (devtools = 9)
        for _ in range(3):
            event_data = {"type": "devtools_open", "details": {}}
            analyzer.process_event(event_data)
        
        risk_factors = analyzer.get_risk_factors()
        
        assert risk_factors["high_severity_count"] == 3
    
    def test_risk_factors_suspicious_apps_warning(self):
        """Test warning appears for suspicious apps."""
        analyzer = ScreenActivityAnalyzer("test_session")
        
        event_data = {
            "type": "suspicious_app",
            "details": {"app_name": "WhatsApp"}
        }
        analyzer.process_event(event_data)
        
        risk_factors = analyzer.get_risk_factors()
        
        assert risk_factors["suspicious_apps_detected"] == 1
        assert "warning" in risk_factors


class TestAllowedApps:
    """Test allowed/blocked application checking."""
    
    def test_allowed_browser_apps(self):
        """Test common browsers are allowed."""
        analyzer = ScreenActivityAnalyzer("test_session")
        
        assert analyzer.is_allowed_app("Chrome") is True
        assert analyzer.is_allowed_app("Firefox") is True
        assert analyzer.is_allowed_app("Edge") is True
        assert analyzer.is_allowed_app("Safari") is True
    
    def test_blocked_messaging_apps(self):
        """Test messaging apps are blocked."""
        analyzer = ScreenActivityAnalyzer("test_session")
        
        assert analyzer.is_allowed_app("Telegram") is False
        assert analyzer.is_allowed_app("WhatsApp") is False
        assert analyzer.is_allowed_app("Discord") is False
    
    def test_blocked_productivity_apps(self):
        """Test productivity apps with collaboration features are blocked."""
        analyzer = ScreenActivityAnalyzer("test_session")
        
        assert analyzer.is_allowed_app("Notion") is False
        assert analyzer.is_allowed_app("Google Docs") is False
    
    def test_case_insensitive_check(self):
        """Test app name check is case insensitive."""
        analyzer = ScreenActivityAnalyzer("test_session")
        
        assert analyzer.is_allowed_app("TELEGRAM") is False
        assert analyzer.is_allowed_app("telegram") is False
        assert analyzer.is_allowed_app("TeLeGrAm") is False
    
    def test_partial_match_blocking(self):
        """Test partial keyword matching works."""
        analyzer = ScreenActivityAnalyzer("test_session")
        
        assert analyzer.is_allowed_app("Telegram Desktop") is False
        assert analyzer.is_allowed_app("WhatsApp Web") is False
        assert analyzer.is_allowed_app("Discord Canary") is False


class TestSessionIsolation:
    """Test that different sessions are isolated."""
    
    def test_multiple_sessions_isolated(self):
        """Test events in one session don't affect another."""
        analyzer1 = ScreenActivityAnalyzer("session_1")
        analyzer2 = ScreenActivityAnalyzer("session_2")
        
        # Add events to session 1
        for _ in range(5):
            event_data = {"type": "tab_switch", "details": {}}
            analyzer1.process_event(event_data)
        
        # Session 2 should be unaffected
        assert len(analyzer2.events) == 0
        assert analyzer2.tab_switch_count == 0
        
        # Session 1 should have events
        assert len(analyzer1.events) == 5
        assert analyzer1.tab_switch_count > 0


class TestEdgeCases:
    """Test edge cases and error handling."""
    
    def test_empty_details_dict(self):
        """Test processing event with empty details."""
        analyzer = ScreenActivityAnalyzer("test_session")
        
        event_data = {
            "type": "tab_switch",
            "details": {}
        }
        
        events = analyzer.process_event(event_data)
        
        assert len(events) == 1
        assert events[0].details == {}
    
    def test_missing_details_key(self):
        """Test processing event without details key."""
        analyzer = ScreenActivityAnalyzer("test_session")
        
        event_data = {
            "type": "tab_switch"
        }
        
        events = analyzer.process_event(event_data)
        
        assert len(events) == 1
        assert events[0].details == {}
    
    def test_many_events_accumulation(self):
        """Test handling many events without issues."""
        analyzer = ScreenActivityAnalyzer("test_session")
        
        # Process 100 events
        for i in range(100):
            event_data = {
                "type": "tab_switch" if i % 2 == 0 else "window_blur",
                "details": {"index": i}
            }
            analyzer.process_event(event_data)
        
        assert len(analyzer.events) == 100
        
        # Should still calculate risk factors correctly
        risk_factors = analyzer.get_risk_factors()
        assert "tab_switch_rate_per_min" in risk_factors
