package com.corporate.learning.proctoring;

import lombok.Data;
import lombok.Builder;
import lombok.NoArgsConstructor;
import lombok.AllArgsConstructor;
import com.fasterxml.jackson.annotation.JsonProperty;
import com.fasterxml.jackson.annotation.JsonFormat;
import java.time.Instant;
import java.util.List;
import java.util.Map;

/**
 * DTO классы для интеграции с сервисом прокторинга
 */
public class ProctoringDto {

    @Data
    @Builder
    @NoArgsConstructor
    @AllArgsConstructor
    public static class StartSessionRequest {
        @JsonProperty("user_id")
        private String userId;
        
        @JsonProperty("exam_id")
        private String examId;
        
        @JsonProperty("settings")
        private SessionSettings settings;
    }

    @Data
    @Builder
    @NoArgsConstructor
    @AllArgsConstructor
    public static class SessionSettings {
        @JsonProperty("duration_minutes")
        private Integer durationMinutes;
        
        @JsonProperty("allowed_apps")
        private List<String> allowedApps;
        
        @JsonProperty("require_fullscreen")
        @Builder.Default
        private Boolean requireFullscreen = true;
        
        @JsonProperty("detection_sensitivity")
        @Builder.Default
        private String detectionSensitivity = "medium";
    }

    @Data
    @NoArgsConstructor
    @AllArgsConstructor
    public static class SessionResponse {
        @JsonProperty("session_id")
        private String sessionId;
        
        @JsonProperty("user_id")
        private String userId;
        
        @JsonProperty("exam_id")
        private String examId;
        
        private String status;
        
        @JsonProperty("started_at")
        @JsonFormat(pattern = "yyyy-MM-dd'T'HH:mm:ss.SSSX", timezone = "UTC")
        private Instant startedAt;
        
        @JsonProperty("websocket_url")
        private String websocketUrl;
        
        @JsonProperty("consent_required")
        private Boolean consentRequired;
    }

    @Data
    @NoArgsConstructor
    @AllArgsConstructor
    public static class EndSessionResponse {
        @JsonProperty("session_id")
        private String sessionId;
        
        private String status;
        
        @JsonProperty("total_duration_sec")
        private Double totalDurationSec;
        
        @JsonProperty("total_violations")
        private Integer totalViolations;
        
        @JsonProperty("violations_by_type")
        private Map<String, Integer> violationsByType;
        
        @JsonProperty("risk_score")
        private Integer riskScore;
        
        @JsonProperty("report_available")
        private Boolean reportAvailable;
    }

    @Data
    @NoArgsConstructor
    @AllArgsConstructor
    public static class SessionReport {
        @JsonProperty("session_id")
        private String sessionId;
        
        @JsonProperty("user_id")
        private String userId;
        
        @JsonProperty("exam_id")
        private String examId;
        
        private String status;
        
        @JsonProperty("started_at")
        @JsonFormat(pattern = "yyyy-MM-dd'T'HH:mm:ss.SSSX", timezone = "UTC")
        private Instant startedAt;
        
        @JsonProperty("ended_at")
        @JsonFormat(pattern = "yyyy-MM-dd'T'HH:mm:ss.SSSX", timezone = "UTC")
        private Instant endedAt;
        
        @JsonProperty("duration_sec")
        private Double durationSec;
        
        @JsonProperty("risk_score")
        private Integer riskScore;
        
        @JsonProperty("risk_level")
        private String riskLevel;
        
        private ReportSummary summary;
        private List<ViolationEvent> violations;
        private List<TimelineEvent> timeline;
        
        @JsonProperty("video_urls")
        private VideoUrls videoUrls;
    }

    @Data
    @NoArgsConstructor
    @AllArgsConstructor
    public static class ReportSummary {
        @JsonProperty("total_violations")
        private Integer totalViolations;
        
        @JsonProperty("violations_by_severity")
        private Map<String, Integer> violationsBySeverity;
        
        @JsonProperty("violations_by_type")
        private Map<String, Integer> violationsByType;
    }

    @Data
    @NoArgsConstructor
    @AllArgsConstructor
    public static class ViolationEvent {
        @JsonProperty("event_id")
        private String eventId;
        
        @JsonProperty("session_id")
        private String sessionId;
        
        private Instant timestamp;
        private String type;
        private String severity;
        private Double confidence;
        private String description;
        private Map<String, Object> metadata;
        
        @JsonProperty("frame_snapshot_url")
        private String frameSnapshotUrl;
    }

    @Data
    @NoArgsConstructor
    @AllArgsConstructor
    public static class TimelineEvent {
        private Instant timestamp;
        
        @JsonProperty("event_type")
        private String eventType;
        
        private String description;
        private String severity;
    }

    @Data
    @NoArgsConstructor
    @AllArgsConstructor
    public static class VideoUrls {
        @JsonProperty("camera_recording")
        private String cameraRecording;
        
        @JsonProperty("screen_recording")
        private String screenRecording;
    }

    @Data
    @NoArgsConstructor
    @AllArgsConstructor
    public static class RiskAssessment {
        @JsonProperty("session_id")
        private String sessionId;
        
        @JsonProperty("risk_score")
        private Integer riskScore;
        
        @JsonProperty("risk_level")
        private String riskLevel;
        
        private List<RiskFactor> factors;
        private String recommendation;
        private String details;
    }

    @Data
    @NoArgsConstructor
    @AllArgsConstructor
    public static class RiskFactor {
        private String name;
        private Double weight;
        private Double score;
        private Double contribution;
    }

    @Data
    @NoArgsConstructor
    @AllArgsConstructor
    public static class ErrorResponse {
        @JsonProperty("error_code")
        private String errorCode;
        
        private String message;
        private List<FieldError> details;
    }

    @Data
    @NoArgsConstructor
    @AllArgsConstructor
    public static class FieldError {
        private String field;
        private String message;
    }

    @Data
    @NoArgsConstructor
    @AllArgsConstructor
    public static class WebhookPayload {
        @JsonProperty("event_type")
        private String eventType;
        
        private Instant timestamp;
        private WebhookData data;
        private String signature;
    }

    @Data
    @NoArgsConstructor
    @AllArgsConstructor
    public static class WebhookData {
        @JsonProperty("session_id")
        private String sessionId;
        
        @JsonProperty("user_id")
        private String userId;
        
        @JsonProperty("exam_id")
        private String examId;
        
        @JsonProperty("risk_score")
        private Integer riskScore;
        
        @JsonProperty("violation_count")
        private Integer violationCount;
    }
}
