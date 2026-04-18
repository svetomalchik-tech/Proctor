package com.corporate.learning.proctoring;

import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.HttpEntity;
import org.springframework.http.HttpHeaders;
import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;
import org.springframework.stereotype.Service;
import org.springframework.web.client.RestTemplate;
import org.springframework.web.util.UriComponentsBuilder;

import java.net.URI;
import java.util.HashMap;
import java.util.Map;

/**
 * Клиент для интеграции с сервисом прокторинга
 * 
 * Пример использования в Spring Boot приложении:
 * 
 * ```java
 * @Autowired
 * private ProctoringClient proctoringClient;
 * 
 * public void startExam(String userId, String examId) {
 *     ProctoringDto.SessionResponse session = proctoringClient.startProctoring(userId, examId);
 *     // Сохраняем session_id и передаём на фронтенд для WebSocket подключения
 * }
 * 
 * public void finishExam(String sessionId) {
 *     ProctoringDto.EndSessionResponse result = proctoringClient.stopProctoring(sessionId);
 *     // Обрабатываем результат, проверяем risk_score
 * }
 * ```
 */
@Slf4j
@Service
public class ProctoringClient {

    private final RestTemplate restTemplate;
    private final String baseUrl;
    private final String apiKey;

    public ProctoringClient(
            @Value("${proctoring.base-url:http://localhost:8000/api/v1}") String baseUrl,
            @Value("${proctoring.api-key:}") String apiKey) {
        this.restTemplate = new RestTemplate();
        this.baseUrl = baseUrl;
        this.apiKey = apiKey;
    }

    /**
     * Начать сессию прокторинга
     * 
     * @param userId ID пользователя в корпоративной системе
     * @param examId ID экзамена/теста
     * @return SessionResponse с session_id и websocket_url
     */
    public ProctoringDto.SessionResponse startProctoring(String userId, String examId) {
        return startProctoring(userId, examId, null);
    }

    /**
     * Начать сессию прокторинга с настройками
     * 
     * @param userId ID пользователя
     * @param examId ID экзамена
     * @param settings Опциональные настройки сессии
     * @return SessionResponse
     */
    public ProctoringDto.SessionResponse startProctoring(
            String userId, 
            String examId, 
            ProctoringDto.SessionSettings settings) {
        
        log.info("Starting proctoring session for user={} exam={}", userId, examId);
        
        ProctoringDto.StartSessionRequest request = ProctoringDto.StartSessionRequest.builder()
                .userId(userId)
                .examId(examId)
                .settings(settings)
                .build();
        
        HttpHeaders headers = createHeaders();
        HttpEntity<ProctoringDto.StartSessionRequest> entity = new HttpEntity<>(request, headers);
        
        URI uri = UriComponentsBuilder.fromHttpUrl(baseUrl)
                .path("/proctoring/start")
                .build()
                .toUri();
        
        ResponseEntity<ProctoringDto.SessionResponse> response = restTemplate.postForEntity(
                uri, 
                entity, 
                ProctoringDto.SessionResponse.class
        );
        
        log.info("Proctoring session started: sessionId={}", response.getBody().getSessionId());
        return response.getBody();
    }

    /**
     * Завершить сессию прокторинга
     * 
     * @param sessionId ID сессии прокторинга
     * @return EndSessionResponse с результатами
     */
    public ProctoringDto.EndSessionResponse stopProctoring(String sessionId) {
        log.info("Stopping proctoring session: sessionId={}", sessionId);
        
        HttpHeaders headers = createHeaders();
        HttpEntity<Void> entity = new HttpEntity<>(headers);
        
        URI uri = UriComponentsBuilder.fromHttpUrl(baseUrl)
                .path("/proctoring/{sessionId}/stop")
                .build(sessionId);
        
        ResponseEntity<ProctoringDto.EndSessionResponse> response = restTemplate.exchange(
                uri,
                org.springframework.http.HttpMethod.POST,
                entity,
                ProctoringDto.EndSessionResponse.class
        );
        
        ProctoringDto.EndSessionResponse body = response.getBody();
        log.info("Proctoring session stopped: sessionId={}, riskScore={}, violations={}", 
                sessionId, body.getRiskScore(), body.getTotalViolations());
        
        return body;
    }

    /**
     * Получить полный отчёт по сессии
     * 
     * @param sessionId ID сессии
     * @param includeVideoUrls Включить URL для скачивания видео
     * @return SessionReport с детальными данными
     */
    public ProctoringDto.SessionReport getSessionReport(String sessionId, boolean includeVideoUrls) {
        log.info("Getting proctoring report: sessionId={}", sessionId);
        
        HttpHeaders headers = createHeaders();
        HttpEntity<Void> entity = new HttpEntity<>(headers);
        
        URI uri = UriComponentsBuilder.fromHttpUrl(baseUrl)
                .path("/proctoring/{sessionId}/report")
                .queryParam("include_video_urls", includeVideoUrls)
                .build(sessionId);
        
        ResponseEntity<ProctoringDto.SessionReport> response = restTemplate.exchange(
                uri,
                org.springframework.http.HttpMethod.GET,
                entity,
                ProctoringDto.SessionReport.class
        );
        
        return response.getBody();
    }

    /**
     * Получить оценку рисков
     * 
     * @param sessionId ID сессии
     * @return RiskAssessment с рекомендацией
     */
    public ProctoringDto.RiskAssessment getRiskAssessment(String sessionId) {
        log.info("Getting risk assessment: sessionId={}", sessionId);
        
        HttpHeaders headers = createHeaders();
        HttpEntity<Void> entity = new HttpEntity<>(headers);
        
        URI uri = UriComponentsBuilder.fromHttpUrl(baseUrl)
                .path("/proctoring/{sessionId}/risk-assessment")
                .build(sessionId);
        
        ResponseEntity<ProctoringDto.RiskAssessment> response = restTemplate.exchange(
                uri,
                org.springframework.http.HttpMethod.GET,
                entity,
                ProctoringDto.RiskAssessment.class
        );
        
        return response.getBody();
    }

    /**
     * Проверка здоровья сервиса прокторинга
     * 
     * @return true если сервис доступен
     */
    public boolean isHealthy() {
        try {
            URI uri = UriComponentsBuilder.fromHttpUrl(baseUrl)
                    .path("/health")
                    .build()
                    .toUri();
            
            ResponseEntity<Map> response = restTemplate.getForEntity(uri, Map.class);
            return "healthy".equals(response.getBody().get("status"));
        } catch (Exception e) {
            log.warn("Proctoring service health check failed", e);
            return false;
        }
    }

    /**
     * Создать заголовки для запроса
     */
    private HttpHeaders createHeaders() {
        HttpHeaders headers = new HttpHeaders();
        headers.setContentType(MediaType.APPLICATION_JSON);
        headers.setAccept(java.util.List.of(MediaType.APPLICATION_JSON));
        
        if (apiKey != null && !apiKey.isEmpty()) {
            headers.set("X-API-Key", apiKey);
        }
        
        // Если используется JWT от основного приложения
        // String jwtToken = SecurityContextHolder.getContext().getAuthentication().getCredentials().toString();
        // headers.set("Authorization", "Bearer " + jwtToken);
        
        return headers;
    }
}
