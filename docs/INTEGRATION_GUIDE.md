# Инструкция по интеграции системы прокторинга с корпоративной платформой тестирования

Это руководство описывает пошаговый процесс интеграции системы прокторинга с существующей корпоративной платформой тестирования, написанной на **Java (Spring Boot)** для backend и **JavaScript/TypeScript (React)** для frontend.

---

## 📋 Оглавление

1. [Обзор архитектуры интеграции](#обзор-архитектуры-интеграции)
2. [Backend интеграция (Java/Spring Boot)](#backend-интеграция-javaspring-boot)
3. [Frontend интеграция (JavaScript/React)](#frontend-интеграция-javascriptreact)
4. [Настройка безопасности](#настройка-безопасности)
5. [Тестирование интеграции](#тестирование-интеграции)
6. [Production checklist](#production-checklist)
7. [Troubleshooting](#troubleshooting)

---

## Обзор архитектуры интеграции

```
┌─────────────────────────────────────────────────────────────────┐
│           CORPORATE TESTING PLATFORM                            │
│  ┌───────────────────┐         ┌───────────────────────┐       │
│  │   Spring Boot     │  REST   │    React Frontend     │       │
│  │   Backend         │◄───────►│    (Testing UI)       │       │
│  │                   │         │                       │       │
│  │  - ExamService    │         │  - TestTakerView      │       │
│  │  - UserService    │         │  - ProctoringModule   │       │
│  │  - AuthService    │         │  - Camera/Screen API  │       │
│  └─────────┬─────────┘         └───────────┬───────────┘       │
│            │                               │                    │
│            │ REST API                      │ WebSocket          │
│            │ + JWT                         │ + WebRTC           │
└────────────┼───────────────────────────────┼────────────────────┘
             │                               │
             ▼                               ▼
┌─────────────────────────────────────────────────────────────────┐
│              PROCTORING MICROSERVICE                            │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  FastAPI Backend                                        │   │
│  │  - Session Management                                   │   │
│  │  - Real-time Analysis (CV + Screen)                     │   │
│  │  - Violation Detection                                  │   │
│  │  - Risk Scoring                                         │   │
│  └─────────────────────────────────────────────────────────┘   │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  Storage Layer                                          │   │
│  │  - PostgreSQL (sessions, violations)                    │   │
│  │  - Redis (real-time cache)                              │   │
│  │  - MinIO/S3 (video recordings)                          │   │
│  └─────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
```

### Поток данных при проведении экзамена

1. **Инициация экзамена**: Пользователь начинает тест в корпоративной системе
2. **Создание сессии**: Spring Boot вызывает `POST /api/v1/proctoring/start`
3. **Подключение к WebSocket**: React frontend подключается к `ws://.../ws/{session_id}`
4. **Стриминг**: Камера и экран отправляются в реальном времени
5. **Анализ**: Proctoring service детектирует нарушения
6. **Завершение**: Spring Boot получает отчёт и оценку рисков
7. **Решение**: Система принимает решение (approve/review/reject)

---

## Backend интеграция (Java/Spring Boot)

### Шаг 1: Добавление зависимостей

Добавьте в `pom.xml` вашего Spring Boot проекта:

```xml
<dependencies>
    <!-- Existing dependencies -->
    
    <!-- HTTP Client for Proctoring API -->
    <dependency>
        <groupId>org.springframework.boot</groupId>
        <artifactId>spring-boot-starter-web</artifactId>
    </dependency>
    
    <!-- Lombok (optional but recommended) -->
    <dependency>
        <groupId>org.projectlombok</groupId>
        <artifactId>lombok</artifactId>
        <optional>true</optional>
    </dependency>
    
    <!-- Jackson for JSON processing -->
    <dependency>
        <groupId>com.fasterxml.jackson.core</groupId>
        <artifactId>jackson-databind</artifactId>
    </dependency>
    
    <!-- WebClient for reactive calls (optional) -->
    <dependency>
        <groupId>org.springframework.boot</groupId>
        <artifactId>spring-boot-starter-webflux</artifactId>
    </dependency>
</dependencies>
```

### Шаг 2: Конфигурация подключения

Добавьте в `application.yml` или `application.properties`:

```yaml
# application.yml
proctoring:
  # URL сервиса прокторинга
  base-url: ${PROCTORING_BASE_URL:http://localhost:8000/api/v1}
  
  # API ключ для аутентификации (если используется)
  api-key: ${PROCTORING_API_KEY:your-secret-api-key}
  
  # Таймауты соединений
  connection-timeout-ms: 5000
  read-timeout-ms: 30000
  write-timeout-ms: 30000
  
  # Настройки retry политики
  retry:
    max-attempts: 3
    delay-ms: 1000
    backoff-multiplier: 2.0
  
  # Пороги для принятия решений
  risk-thresholds:
    auto-reject: 75      # Риск >= 75% -> автоматический отказ
    needs-review: 50     # Риск >= 50% -> требует проверки
    auto-approve: 25     # Риск < 25% -> автоматическое одобрение

# Logging для отладки
logging:
  level:
    com.corporate.learning.proctoring: DEBUG
    org.springframework.web.client: DEBUG
```

### Шаг 3: Копирование DTO классов

Скопируйте файлы из `integration-examples/java-spring/` в ваш проект:

```bash
# Из директории проекта прокторинга
cp integration-examples/java-spring/ProctoringDto.java \
   your-spring-project/src/main/java/com/corporate/learning/proctoring/

cp integration-examples/java-spring/ProctoringClient.java \
   your-spring-project/src/main/java/com/corporate/learning/proctoring/
```

Или создайте файлы вручную, скопировав содержимое из примеров.

**Структура пакетов:**
```
your-spring-project/
└── src/main/java/
    └── com/corporate/learning/
        └── proctoring/
            ├── ProctoringDto.java
            ├── ProctoringClient.java
            └── ProctoringConfig.java (создать)
```

### Шаг 4: Создание конфигурационного класса

Создайте `ProctoringConfig.java`:

```java
package com.corporate.learning.proctoring;

import org.springframework.beans.factory.annotation.Value;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.http.client.ClientHttpRequestFactory;
import org.springframework.http.client.SimpleClientHttpRequestFactory;
import org.springframework.web.client.RestTemplate;

@Configuration
public class ProctoringConfig {

    @Value("${proctoring.connection-timeout-ms:5000}")
    private int connectionTimeout;

    @Value("${proctoring.read-timeout-ms:30000}")
    private int readTimeout;

    @Bean
    public RestTemplate proctoringRestTemplate() {
        ClientHttpRequestFactory factory = new SimpleClientHttpRequestFactory();
        factory.setConnectTimeout(connectionTimeout);
        factory.setReadTimeout(readTimeout);
        
        return new RestTemplate(factory);
    }
}
```

### Шаг 5: Интеграция с сервисом экзаменов

Модифицируйте ваш существующий `ExamService`:

```java
package com.corporate.learning.exam;

import com.corporate.learning.proctoring.ProctoringClient;
import com.corporate.learning.proctoring.ProctoringDto;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.time.Instant;
import java.util.Optional;

@Slf4j
@Service
@RequiredArgsConstructor
public class ExamService {

    private final ProctoringClient proctoringClient;
    private final ExamRepository examRepository;
    private final ExamSessionRepository sessionRepository;

    /**
     * Начало экзамена с прокторингом
     */
    @Transactional
    public ExamSession startExamWithProctoring(String userId, String examId) {
        log.info("Starting exam with proctoring: userId={}, examId={}", userId, examId);
        
        // 1. Создаём сессию экзамена в БД
        ExamSession examSession = ExamSession.builder()
                .userId(userId)
                .examId(examId)
                .startTime(Instant.now())
                .status(ExamStatus.IN_PROGRESS)
                .build();
        examSession = examRepository.save(examSession);
        
        try {
            // 2. Запускаем сессию прокторинга
            ProctoringDto.SessionSettings settings = ProctoringDto.SessionSettings.builder()
                    .durationMinutes(60)
                    .requireFullscreen(true)
                    .detectionSensitivity("medium")
                    .build();
            
            ProctoringDto.SessionResponse proctoringSession = 
                proctoringClient.startProctoring(userId, examId, settings);
            
            // 3. Сохраняем ID сессии прокторинга
            examSession.setProctoringSessionId(proctoringSession.getSessionId());
            examSession.setWebsocketUrl(proctoringSession.getWebsocketUrl());
            examSession = examRepository.save(examSession);
            
            log.info("Proctoring session started: sessionId={}", 
                    proctoringSession.getSessionId());
            
            return examSession;
            
        } catch (Exception e) {
            log.error("Failed to start proctoring session", e);
            examSession.setStatus(ExamStatus.ERROR);
            examRepository.save(examSession);
            throw new ExamProctoringException("Failed to initialize proctoring", e);
        }
    }

    /**
     * Завершение экзамена с оценкой прокторинга
     */
    @Transactional
    public ExamResult completeExamWithProctoring(String sessionId) {
        log.info("Completing exam with proctoring analysis: sessionId={}", sessionId);
        
        ExamSession examSession = examRepository.findBySessionId(sessionId)
                .orElseThrow(() -> new ExamNotFoundException(sessionId));
        
        String proctoringSessionId = examSession.getProctoringSessionId();
        if (proctoringSessionId == null) {
            throw new IllegalStateException("No proctoring session found");
        }
        
        try {
            // 1. Завершаем сессию прокторинга
            ProctoringDto.EndSessionResponse proctoringResult = 
                proctoringClient.stopProctoring(proctoringSessionId);
            
            // 2. Получаем детальную оценку рисков
            ProctoringDto.RiskAssessment riskAssessment = 
                proctoringClient.getRiskAssessment(proctoringSessionId);
            
            // 3. Сохраняем результаты в БД
            examSession.setEndTime(Instant.now());
            examSession.setProctoringRiskScore(riskAssessment.getRiskScore());
            examSession.setProctoringRiskLevel(riskAssessment.getRiskLevel());
            examSession.setTotalViolations(proctoringResult.getTotalViolations());
            
            // 4. Принимаем решение на основе порогов
            ExamDecision decision = makeDecisionBasedOnRisk(riskAssessment);
            examSession.setDecision(decision);
            
            // 5. Обновляем статус
            switch (decision) {
                case AUTO_APPROVE:
                    examSession.setStatus(ExamStatus.COMPLETED_APPROVED);
                    break;
                case NEEDS_REVIEW:
                    examSession.setStatus(ExamStatus.PENDING_REVIEW);
                    break;
                case AUTO_REJECT:
                    examSession.setStatus(ExamStatus.COMPLETED_REJECTED);
                    break;
            }
            
            examRepository.save(examSession);
            
            log.info("Exam completed: sessionId={}, decision={}, riskScore={}", 
                    sessionId, decision, riskAssessment.getRiskScore());
            
            return ExamResult.builder()
                    .sessionId(sessionId)
                    .decision(decision)
                    .riskScore(riskAssessment.getRiskScore())
                    .violations(proctoringResult.getTotalViolations())
                    .requiresReview(decision == ExamDecision.NEEDS_REVIEW)
                    .build();
                    
        } catch (Exception e) {
            log.error("Failed to complete exam with proctoring", e);
            examSession.setStatus(ExamStatus.ERROR);
            examRepository.save(examSession);
            throw new ExamProctoringException("Failed to process proctoring results", e);
        }
    }

    /**
     * Принятие решения на основе оценки рисков
     */
    private ExamDecision makeDecisionBasedOnRisk(ProctoringDto.RiskAssessment assessment) {
        int riskScore = assessment.getRiskScore();
        
        if (riskScore >= 75) {
            return ExamDecision.AUTO_REJECT;
        } else if (riskScore >= 50) {
            return ExamDecision.NEEDS_REVIEW;
        } else if (riskScore >= 25) {
            return ExamDecision.AUTO_APPROVE_WITH_NOTES;
        } else {
            return ExamDecision.AUTO_APPROVE;
        }
    }

    /**
     * Получить детальный отчёт для ручной проверки
     */
    public ProctoringDto.SessionReport getProctoringReport(String sessionId) {
        ExamSession examSession = examRepository.findBySessionId(sessionId)
                .orElseThrow(() -> new ExamNotFoundException(sessionId));
        
        String proctoringSessionId = examSession.getProctoringSessionId();
        return proctoringClient.getSessionReport(proctoringSessionId, true);
    }
}
```

### Шаг 6: Создание REST контроллера для frontend

```java
package com.corporate.learning.api;

import com.corporate.learning.exam.ExamService;
import com.corporate.learning.exam.ExamSession;
import com.corporate.learning.exam.ExamResult;
import com.corporate.learning.proctoring.ProctoringDto;
import lombok.RequiredArgsConstructor;
import org.springframework.http.ResponseEntity;
import org.springframework.security.core.annotation.AuthenticationPrincipal;
import org.springframework.security.core.userdetails.UserDetails;
import org.springframework.web.bind.annotation.*;

@RestController
@RequestMapping("/api/exams")
@RequiredArgsConstructor
public class ExamController {

    private final ExamService examService;

    /**
     * Начать экзамен (вызывается frontend при клике "Start Exam")
     */
    @PostMapping("/{examId}/start")
    public ResponseEntity<ExamStartResponse> startExam(
            @PathVariable String examId,
            @AuthenticationPrincipal UserDetails userDetails) {
        
        String userId = userDetails.getUsername();
        ExamSession session = examService.startExamWithProctoring(userId, examId);
        
        return ResponseEntity.ok(ExamStartResponse.builder()
                .sessionId(session.getSessionId())
                .examId(examId)
                .proctoringSessionId(session.getProctoringSessionId())
                .websocketUrl(session.getWebsocketUrl())
                .durationMinutes(60)
                .build());
    }

    /**
     * Завершить экзамен
     */
    @PostMapping("/{sessionId}/complete")
    public ResponseEntity<ExamResult> completeExam(@PathVariable String sessionId) {
        ExamResult result = examService.completeExamWithProctoring(sessionId);
        return ResponseEntity.ok(result);
    }

    /**
     * Получить отчёт прокторинга (для админ панели)
     */
    @GetMapping("/{sessionId}/proctoring-report")
    public ResponseEntity<ProctoringDto.SessionReport> getProctoringReport(
            @PathVariable String sessionId) {
        
        ProctoringDto.SessionReport report = examService.getProctoringReport(sessionId);
        return ResponseEntity.ok(report);
    }

    // DTO для ответа
    @Data
    @Builder
    @NoArgsConstructor
    @AllArgsConstructor
    public static class ExamStartResponse {
        private String sessionId;
        private String examId;
        private String proctoringSessionId;
        private String websocketUrl;
        private Integer durationMinutes;
    }
}
```

### Шаг 7: Обработка вебхуков (опционально)

Создайте контроллер для получения уведомлений от прокторинг сервиса:

```java
package com.corporate.learning.api;

import com.corporate.learning.proctoring.ProctoringDto;
import com.corporate.learning.exam.ExamNotificationService;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

@Slf4j
@RestController
@RequestMapping("/api/webhooks/proctoring")
@RequiredArgsConstructor
public class ProctoringWebhookController {

    private final ExamNotificationService notificationService;

    /**
     * Endpoint для получения вебхуков от сервиса прокторинга
     */
    @PostMapping("/notifications")
    public ResponseEntity<Void> handleProctoringNotification(
            @RequestBody ProctoringDto.WebhookPayload payload,
            @RequestHeader("X-Signature") String signature) {
        
        log.info("Received proctoring webhook: eventType={}, sessionId={}", 
                payload.getEventType(), payload.getData().getSessionId());
        
        // Верификация подписи (рекомендуется для production)
        if (!verifySignature(payload, signature)) {
            log.warn("Invalid webhook signature");
            return ResponseEntity.badRequest().build();
        }
        
        // Обработка события
        notificationService.handleProctoringEvent(payload);
        
        return ResponseEntity.ok().build();
    }

    private boolean verifySignature(ProctoringDto.WebhookPayload payload, String signature) {
        // TODO: Реализовать верификацию HMAC подписи
        // Используйте секретный ключ для проверки подлинности вебхука
        return true; // заглушка для примера
    }
}
```

---

## Frontend интеграция (JavaScript/React)

### Шаг 1: Установка зависимостей

В вашем React проекте выполните:

```bash
npm install websocket axios
# или
yarn add websocket axios
```

### Шаг 2: Создание сервиса прокторинга

Создайте файл `src/services/proctoringIntegration.ts`:

```typescript
// src/services/proctoringIntegration.ts
import axios, { AxiosInstance } from 'axios';

export interface ProctoringSession {
  sessionId: string;
  examId: string;
  proctoringSessionId: string;
  websocketUrl: string;
  durationMinutes: number;
}

export interface Violation {
  eventId: string;
  timestamp: string;
  type: string;
  severity: 'low' | 'medium' | 'high' | 'critical';
  confidence: number;
  description: string;
}

class ProctoringIntegrationService {
  private api: AxiosInstance;

  constructor(baseUrl: string = '/api') {
    this.api = axios.create({
      baseURL: baseUrl,
      headers: {
        'Content-Type': 'application/json',
      },
    });

    // Добавляем JWT токен к запросам
    this.api.interceptors.request.use((config) => {
      const token = localStorage.getItem('auth_token');
      if (token) {
        config.headers.Authorization = `Bearer ${token}`;
      }
      return config;
    });
  }

  /**
   * Начать экзамен с прокторингом
   */
  async startExam(examId: string): Promise<ProctoringSession> {
    try {
      const response = await this.api.post<ProctoringSession>(
        `/exams/${examId}/start`
      );
      return response.data;
    } catch (error) {
      console.error('Failed to start exam with proctoring:', error);
      throw new Error('Не удалось начать экзамен. Проверьте подключение к камере.');
    }
  }

  /**
   * Завершить экзамен
   */
  async completeExam(sessionId: string): Promise<{
    decision: 'AUTO_APPROVE' | 'NEEDS_REVIEW' | 'AUTO_REJECT';
    riskScore: number;
    violations: number;
    requiresReview: boolean;
  }> {
    try {
      const response = await this.api.post(`/exams/${sessionId}/complete`);
      return response.data;
    } catch (error) {
      console.error('Failed to complete exam:', error);
      throw error;
    }
  }

  /**
   * Получить отчёт прокторинга
   */
  async getProctoringReport(sessionId: string) {
    try {
      const response = await this.api.get(`/exams/${sessionId}/proctoring-report`);
      return response.data;
    } catch (error) {
      console.error('Failed to get proctoring report:', error);
      throw error;
    }
  }
}

export const proctoringIntegration = new ProctoringIntegrationService();
```

### Шаг 3: Создание хука для управления сессией

Создайте `src/hooks/useExamSession.ts`:

```typescript
// src/hooks/useExamSession.ts
import { useState, useCallback, useRef, useEffect } from 'react';
import { proctoringIntegration, ProctoringSession, Violation } from '../services/proctoringIntegration';

interface UseExamSessionOptions {
  onViolation?: (violation: Violation) => void;
  onWarning?: (message: string) => void;
  onError?: (error: Error) => void;
  onSessionComplete?: (result: any) => void;
}

export function useExamSession(options: UseExamSessionOptions = {}) {
  const [session, setSession] = useState<ProctoringSession | null>(null);
  const [isRunning, setIsRunning] = useState(false);
  const [violations, setViolations] = useState<Violation[]>([]);
  const [warningCount, setWarningCount] = useState(0);
  const wsRef = useRef<WebSocket | null>(null);

  // Подключение к WebSocket
  const connectToWebSocket = useCallback((websocketUrl: string) => {
    return new Promise<void>((resolve, reject) => {
      const ws = new WebSocket(websocketUrl);

      ws.onopen = () => {
        console.log('Connected to proctoring WebSocket');
        resolve();
      };

      ws.onerror = (error) => {
        console.error('WebSocket error:', error);
        reject(error);
      };

      ws.onclose = () => {
        console.log('WebSocket connection closed');
      };

      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          
          if (data.type === 'video_analysis' && data.violations) {
            const newViolations: Violation[] = data.violations;
            setViolations(prev => [...prev, ...newViolations]);
            
            newViolations.forEach(violation => {
              options.onViolation?.(violation);
              
              // Показываем предупреждение для серьёзных нарушений
              if (violation.severity === 'high' || violation.severity === 'critical') {
                setWarningCount(prev => prev + 1);
                options.onWarning?.(`Нарушение: ${violation.description}`);
              }
            });
          }
        } catch (error) {
          console.error('Error processing WebSocket message:', error);
        }
      };

      wsRef.current = ws;
    });
  }, [options]);

  // Начало экзамена
  const startExam = useCallback(async (examId: string) => {
    try {
      // 1. Создаём сессию через API
      const proctoringSession = await proctoringIntegration.startExam(examId);
      setSession(proctoringSession);

      // 2. Подключаемся к WebSocket
      await connectToWebSocket(proctoringSession.websocketUrl);

      // 3. Запрашиваем доступ к камере и экрану
      const cameraStream = await navigator.mediaDevices.getUserMedia({
        video: {
          width: { ideal: 1280 },
          height: { ideal: 720 },
          facingMode: 'user'
        }
      });

      const displayStream = await navigator.mediaDevices.getDisplayMedia({
        video: {
          width: { ideal: 1920 },
          height: { ideal: 1080 }
        }
      });

      // 4. Начинаем стриминг через WebSocket
      if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
        // Отправка видео с камеры (2 FPS)
        setInterval(() => {
          const videoElement = document.createElement('video');
          videoElement.srcObject = cameraStream;
          // ... код для отправки кадров
        }, 500);

        // Отправка скринкастов (1 FPS)
        setInterval(() => {
          // ... код для отправки скриншотов экрана
        }, 1000);
      }

      setIsRunning(true);
      return proctoringSession;
    } catch (error) {
      options.onError?.(error as Error);
      throw error;
    }
  }, [connectToWebSocket, options]);

  // Завершение экзамена
  const completeExam = useCallback(async () => {
    if (!session) {
      throw new Error('No active session');
    }

    try {
      // 1. Закрываем WebSocket
      if (wsRef.current) {
        wsRef.current.close();
        wsRef.current = null;
      }

      // 2. Завершаем сессию на сервере
      const result = await proctoringIntegration.completeExam(session.sessionId);
      
      // 3. Очищаем состояние
      setIsRunning(false);
      setSession(null);
      
      options.onSessionComplete?.(result);
      return result;
    } catch (error) {
      options.onError?.(error as Error);
      throw error;
    }
  }, [session, options]);

  // Очистка при размонтировании
  useEffect(() => {
    return () => {
      if (wsRef.current) {
        wsRef.current.close();
      }
    };
  }, []);

  return {
    session,
    isRunning,
    violations,
    warningCount,
    startExam,
    completeExam,
  };
}
```

### Шаг 4: Интеграция с компонентом теста

Модифицируйте ваш компонент прохождения теста:

```typescript
// src/components/TestTaker/TestTakerView.tsx
import React, { useState, useEffect } from 'react';
import { useExamSession } from '../../hooks/useExamSession';
import { ProctoringWarningModal } from './ProctoringWarningModal';
import { ViolationTimeline } from './ViolationTimeline';

interface TestTakerViewProps {
  examId: string;
  onComplete: (result: any) => void;
}

export const TestTakerView: React.FC<TestTakerViewProps> = ({ examId, onComplete }) => {
  const [showWarning, setShowWarning] = useState(false);
  const [warningMessage, setWarningMessage] = useState('');

  const {
    session,
    isRunning,
    violations,
    warningCount,
    startExam,
    completeExam,
  } = useExamSession({
    onViolation: (violation) => {
      console.log('Violation detected:', violation);
    },
    onWarning: (message) => {
      setWarningMessage(message);
      setShowWarning(true);
      // Автоматически скрывать предупреждение через 5 секунд
      setTimeout(() => setShowWarning(false), 5000);
    },
    onError: (error) => {
      console.error('Proctoring error:', error);
      alert('Ошибка прокторинга: ' + error.message);
    },
    onSessionComplete: (result) => {
      onComplete(result);
    },
  });

  // Начало экзамена при монтировании компонента
  useEffect(() => {
    const initializeExam = async () => {
      try {
        await startExam(examId);
      } catch (error) {
        console.error('Failed to initialize exam:', error);
      }
    };

    initializeExam();

    // Предупреждение о переключении вкладок
    const handleVisibilityChange = () => {
      if (document.hidden && isRunning) {
        setWarningMessage('Вы переключились с вкладки экзамена!');
        setShowWarning(true);
        setTimeout(() => setShowWarning(false), 5000);
      }
    };

    document.addEventListener('visibilitychange', handleVisibilityChange);

    return () => {
      document.removeEventListener('visibilitychange', handleVisibilityChange);
    };
  }, [examId, startExam, isRunning]);

  // Обработчик завершения теста
  const handleTestComplete = async (testAnswers: any) => {
    try {
      const result = await completeExam();
      onComplete({
        answers: testAnswers,
        proctoringResult: result,
      });
    } catch (error) {
      console.error('Failed to complete exam:', error);
    }
  };

  return (
    <div className="test-taker-container">
      {/* Модальное окно предупреждения */}
      {showWarning && (
        <ProctoringWarningModal message={warningMessage} />
      )}

      {/* Индикатор нарушений */}
      {violations.length > 0 && (
        <div className="violations-indicator">
          <span>⚠️ Нарушений: {violations.length}</span>
        </div>
      )}

      {/* Основной контент теста */}
      <div className="test-content">
        {/* Ваш существующий компонент теста */}
        <TestQuestions onComplete={handleTestComplete} />
      </div>

      {/* Таймлайн нарушений (опционально, можно показывать после теста) */}
      {violations.length > 0 && (
        <ViolationTimeline violations={violations} />
      )}
    </div>
  );
};
```

### Шаг 5: Компонент предупреждения

Создайте `src/components/TestTaker/ProctoringWarningModal.tsx`:

```typescript
// src/components/TestTaker/ProctoringWarningModal.tsx
import React from 'react';
import './ProctoringWarningModal.css';

interface ProctoringWarningModalProps {
  message: string;
}

export const ProctoringWarningModal: React.FC<ProctoringWarningModalProps> = ({ message }) => {
  return (
    <div className="proctoring-warning-overlay">
      <div className="proctoring-warning-modal">
        <div className="warning-icon">⚠️</div>
        <h3>Внимание!</h3>
        <p>{message}</p>
        <div className="warning-progress-bar">
          <div className="progress-fill"></div>
        </div>
      </div>
    </div>
  );
};
```

```css
/* src/components/TestTaker/ProctoringWarningModal.css */
.proctoring-warning-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.7);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 9999;
  animation: fadeIn 0.3s ease;
}

.proctoring-warning-modal {
  background: white;
  padding: 2rem;
  border-radius: 12px;
  text-align: center;
  max-width: 400px;
  box-shadow: 0 10px 40px rgba(0, 0, 0, 0.3);
  animation: slideIn 0.3s ease;
}

.warning-icon {
  font-size: 3rem;
  margin-bottom: 1rem;
}

.proctoring-warning-modal h3 {
  color: #d32f2f;
  margin-bottom: 0.5rem;
}

.proctoring-warning-modal p {
  color: #333;
  margin-bottom: 1.5rem;
}

.warning-progress-bar {
  width: 100%;
  height: 4px;
  background: #e0e0e0;
  border-radius: 2px;
  overflow: hidden;
}

.progress-fill {
  height: 100%;
  background: #d32f2f;
  animation: shrink 5s linear forwards;
}

@keyframes fadeIn {
  from { opacity: 0; }
  to { opacity: 1; }
}

@keyframes slideIn {
  from {
    transform: translateY(-20px);
    opacity: 0;
  }
  to {
    transform: translateY(0);
    opacity: 1;
  }
}

@keyframes shrink {
  from { width: 100%; }
  to { width: 0%; }
}
```

---

## Настройка безопасности

### JWT Authentication

Убедитесь, что все API вызовы к прокторинг сервису аутентифицированы:

```java
// В Spring Security конфигурации
@Configuration
@EnableWebSecurity
public class SecurityConfig {

    @Bean
    public SecurityFilterChain filterChain(HttpSecurity http) throws Exception {
        http
            .authorizeHttpRequests(auth -> auth
                .requestMatchers("/api/exams/**").authenticated()
                .requestMatchers("/api/webhooks/**").permitAll() // вебхуки без auth
                .anyRequest().authenticated()
            )
            .oauth2ResourceServer(oauth2 -> oauth2.jwt(Customizer.withDefaults()));
        
        return http.build();
    }
}
```

### HTTPS и CORS

Настройте CORS для разрешения запросов только с доверенных доменов:

```java
@Configuration
public class CorsConfig {

    @Bean
    public CorsConfigurationSource corsConfigurationSource() {
        CorsConfiguration configuration = new CorsConfiguration();
        configuration.setAllowedOrigins(List.of(
            "https://learning.corporate.local",
            "https://exams.corporate.local"
        ));
        configuration.setAllowedMethods(List.of("GET", "POST", "PUT", "DELETE", "OPTIONS"));
        configuration.setAllowedHeaders(List.of("*"));
        configuration.setAllowCredentials(true);
        configuration.setMaxAge(3600L);

        UrlBasedCorsConfigurationSource source = new UrlBasedCorsConfigurationSource();
        source.registerCorsConfiguration("/api/**", configuration);
        return source;
    }
}
```

### Шифрование видео

Для production рекомендуется включить шифрование видеопотока:

```yaml
# В конфиге прокторинг сервиса
proctoring:
  encryption:
    enabled: true
    algorithm: AES-256-GCM
    key-rotation-days: 30
```

---

## Тестирование интеграции

### Unit тесты для Java сервиса

```java
// src/test/java/com/corporate/learning/exam/ExamServiceTest.java
@SpringBootTest
@AutoConfigureMockMvc
class ExamServiceTest {

    @Autowired
    private ExamService examService;

    @MockBean
    private ProctoringClient proctoringClient;

    @Test
    void shouldCompleteExamWithLowRisk() {
        // Arrange
        String sessionId = "test-session-123";
        ProctoringDto.EndSessionResponse endResponse = new ProctoringDto.EndSessionResponse();
        endResponse.setRiskScore(15);
        endResponse.setTotalViolations(2);
        
        ProctoringDto.RiskAssessment riskAssessment = new ProctoringDto.RiskAssessment();
        riskAssessment.setRiskScore(15);
        riskAssessment.setRiskLevel("low");
        riskAssessment.setRecommendation("APPROVE");

        when(proctoringClient.stopProctoring(any())).thenReturn(endResponse);
        when(proctoringClient.getRiskAssessment(any())).thenReturn(riskAssessment);

        // Act
        ExamResult result = examService.completeExamWithProctoring(sessionId);

        // Assert
        assertEquals(ExamDecision.AUTO_APPROVE, result.getDecision());
        assertFalse(result.isRequiresReview());
    }

    @Test
    void shouldFlagExamForReviewWithMediumRisk() {
        // Arrange
        String sessionId = "test-session-456";
        ProctoringDto.EndSessionResponse endResponse = new ProctoringDto.EndSessionResponse();
        endResponse.setRiskScore(65);
        endResponse.setTotalViolations(8);
        
        ProctoringDto.RiskAssessment riskAssessment = new ProctoringDto.RiskAssessment();
        riskAssessment.setRiskScore(65);
        riskAssessment.setRiskLevel("medium");
        riskAssessment.setRecommendation("REVIEW");

        when(proctoringClient.stopProctoring(any())).thenReturn(endResponse);
        when(proctoringClient.getRiskAssessment(any())).thenReturn(riskAssessment);

        // Act
        ExamResult result = examService.completeExamWithProctoring(sessionId);

        // Assert
        assertEquals(ExamDecision.NEEDS_REVIEW, result.getDecision());
        assertTrue(result.isRequiresReview());
    }
}
```

### Integration тесты

```java
// src/test/java/com/corporate/learning/api/ExamControllerIntegrationTest.java
@SpringBootTest(webEnvironment = SpringBootTest.WebEnvironment.RANDOM_PORT)
@AutoConfigureMockMvc
@Testcontainers
class ExamControllerIntegrationTest {

    @Container
    static PostgreSQLContainer<?> postgres = new PostgreSQLContainer<>("postgres:15-alpine");

    @Autowired
    private MockMvc mockMvc;

    @WithMockUser(username = "test-user")
    @Test
    void shouldStartExamWithProctoring() throws Exception {
        mockMvc.perform(post("/api/exams/{examId}/start", "exam-java-101")
                .contentType(MediaType.APPLICATION_JSON))
            .andExpect(status().isOk())
            .andExpect(jsonPath("$.sessionId").exists())
            .andExpect(jsonPath("$.proctoringSessionId").exists())
            .andExpect(jsonPath("$.websocketUrl").exists());
    }
}
```

### E2E тесты для frontend

```typescript
// cypress/e2e/exam-proctoring.cy.ts
describe('Exam Proctoring Integration', () => {
  beforeEach(() => {
    cy.login('test-user', 'password');
  });

  it('should start exam with proctoring and detect violations', () => {
    // Переход к экзамену
    cy.visit('/exams/java-certification/start');

    // Разрешаем доступ к камере (mock)
    cy.stub(navigator.mediaDevices, 'getUserMedia').resolves(mockCameraStream);
    cy.stub(navigator.mediaDevices, 'getDisplayMedia').resolves(mockDisplayStream);

    // Проверяем начало сессии
    cy.contains('Экзамен начат').should('be.visible');
    cy.get('[data-testid="camera-preview"]').should('be.visible');

    // Симуляция нарушения (переключение вкладки)
    cy.document().then((doc) => {
      Object.defineProperty(doc, 'hidden', { value: true, writable: true });
      doc.dispatchEvent(new Event('visibilitychange'));
    });

    // Проверяем появление предупреждения
    cy.get('.proctoring-warning-modal')
      .should('be.visible')
      .contains('Вы переключились с вкладки экзамена!');

    // Завершение экзамена
    cy.get('[data-testid="submit-exam"]').click();
    
    // Проверяем результат
    cy.contains('Экзамен завершён').should('be.visible');
    cy.contains('Требуется проверка').should('be.visible'); // из-за нарушения
  });
});
```

---

## Production Checklist

### Backend

- [ ] Настроить HTTPS для всех endpoint'ов
- [ ] Включить rate limiting для API
- [ ] Настроить логирование (ELK Stack или аналог)
- [ ] Настроить мониторинг (Prometheus + Grafana)
- [ ] Включить circuit breaker для вызовов прокторинг сервиса
- [ ] Настроить backup базы данных
- [ ] Провести load testing (минимум 100 concurrent sessions)
- [ ] Настроить auto-scaling для backend сервисов
- [ ] Включить audit logging для всех действий с экзаменами
- [ ] Настроить alerts для критических ошибок

### Frontend

- [ ] Обрабатывать отсутствие камеры/микрофона у пользователя
- [ ] Показывать понятные сообщения об ошибках
- [ ] Реализовать fallback для старых браузеров
- [ ] Оптимизировать производительность (lazy loading, code splitting)
- [ ] Протестировать на разных устройствах и браузерах
- [ ] Включить Sentry или аналогичный сервис для отслеживания ошибок
- [ ] Реализовать offline detection и graceful degradation

### Безопасность

- [ ] Провести security audit кода
- [ ] Включить Content Security Policy (CSP)
- [ ] Настроить secure cookies (HttpOnly, Secure, SameSite)
- [ ] Включить HSTS
- [ ] Провести penetration testing
- [ ] Настроить WAF (Web Application Firewall)
- [ ] Включить DDoS protection
- [ ] Реализовать GDPR compliance (удаление данных по запросу)

### Документация

- [ ] Документировать API для frontend разработчиков
- [ ] Создать runbook для ops команды
- [ ] Написать guide для экзаменаторов (как проверять suspicious exams)
- [ ] Создать FAQ для пользователей

---

## Troubleshooting

### Проблема: Камера не работает в Firefox

**Решение:**
```typescript
// Добавить обработку специфичных ошибок
try {
  const stream = await navigator.mediaDevices.getUserMedia({ video: true });
} catch (error) {
  if (error.name === 'NotAllowedError') {
    showUserMessage('Пожалуйста, разрешите доступ к камере в настройках браузера');
  } else if (error.name === 'NotFoundError') {
    showUserMessage('Камера не найдена. Подключите камеру и попробуйте снова');
  } else if (error.name === 'NotReadableError') {
    showUserMessage('Камера занята другим приложением');
  }
}
```

### Проблема: WebSocket соединение обрывается

**Решение:**
```typescript
// Реализовать reconnection logic
class WebSocketManager {
  private reconnectAttempts = 0;
  private maxReconnectAttempts = 5;
  private reconnectDelay = 1000;

  connect(url: string) {
    this.ws = new WebSocket(url);
    
    this.ws.onclose = () => {
      if (this.reconnectAttempts < this.maxReconnectAttempts) {
        setTimeout(() => {
          this.reconnectAttempts++;
          this.connect(url);
        }, this.reconnectDelay * this.reconnectAttempts);
      }
    };
  }
}
```

### Проблема: Высокая нагрузка на сервер при большом количестве сессий

**Решение:**
1. Уменьшить FPS отправки кадров (с 2 до 1)
2. Использовать сжатие JPEG с меньшим качеством (quality: 0.6)
3. Включить горизонтальное масштабирование прокторинг сервиса
4. Использовать Redis для координации между инстансами
5. Рассмотреть возможность обработки видео на edge (в браузере)

### Проблема: Ложные срабатывания детекции телефона

**Решение:**
```python
# В конфиге прокторинг сервиса настроить пороги
detection:
  phone:
    min_confidence: 0.85  # Увеличить порог уверенности
    min_duration_sec: 2.0  # Игнорировать кратковременные обнаружения
    cooldown_sec: 30  # Не детектировать повторно в течение 30 сек
```

---

## Дополнительные ресурсы

- [OpenAPI спецификация](../openapi/proctoring-api.yaml)
- [Примеры кода Java](../integration-examples/java-spring/)
- [Архитектура системы](../docs/ARCHITECTURE.md)
- [Admin Panel документация](../admin-panel/README.md)

## Контакты поддержки

- Email: proctoring-support@corporate.local
- Slack: #proctoring-integration
- Documentation: https://docs.corporate.local/proctoring
