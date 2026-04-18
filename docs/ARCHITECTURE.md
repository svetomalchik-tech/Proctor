# Система прокторинга для корпоративного обучения

## 1. Архитектура системы

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         CORPORATE LEARNING PLATFORM                      │
│                        (Java Spring Boot Application)                    │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐    │
│  │Auth Service │  │Test Delivery│  │User Management│  │Report Viewer│    │
│  └─────────────┘  └─────────────┘  └─────────────┘  └─────────────┘    │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    │ REST API + JWT
                                    │ Webhooks
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                      PROCTORING MICROSERVICE                             │
│                         (Python FastAPI / Node.js)                       │
│  ┌─────────────────────────────────────────────────────────────────┐    │
│  │                     API Gateway Layer                            │    │
│  │  POST /api/v1/proctoring/start    - Начать сессию               │    │
│  │  POST /api/v1/proctoring/stop     - Завершить сессию            │    │
│  │  GET  /api/v1/proctoring/report   - Получить отчёт              │    │
│  │  WS   /ws/{session_id}            - WebSocket для стриминга     │    │
│  └─────────────────────────────────────────────────────────────────┘    │
│                                   │                                      │
│  ┌────────────────────────────────┼─────────────────────────────────┐    │
│  │                    Real-time Processing Layer                     │    │
│  │  ┌──────────────────┐  ┌──────────────────┐  ┌────────────────┐  │    │
│  │  │ Video Processor  │  │ Screen Processor │  │ Event Aggregator│  │    │
│  │  │ (WebRTC/MediaPipe)│ │ (Screen Capture) │  │ (Rule Engine)   │  │    │
│  │  └──────────────────┘  └──────────────────┘  └────────────────┘  │    │
│  └───────────────────────────────────────────────────────────────────┘    │
│                                   │                                      │
│  ┌────────────────────────────────┼─────────────────────────────────┐    │
│  │                   Detection Services Layer                        │    │
│  │  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌────────────┐  │    │
│  │  │Face Detector│ │Gaze Tracker │ │Phone Detect │ │Multi-face  │  │    │
│  │  │(MediaPipe)  │ │(OpenCV)     │ │(ML Model)   │ │Detector    │  │    │
│  │  └─────────────┘ └─────────────┘ └─────────────┘ └────────────┘  │    │
│  │  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌────────────┐  │    │
│  │  │Tab Switch   │ │App Detector │ │OCR Analyzer │ │Audio Detect│  │    │
│  │  │Detector     │ │(Window API) │ │(Tesseract)  │ │(Optional)  │  │    │
│  │  └─────────────┘ └─────────────┘ └─────────────┘ └────────────┘  │    │
│  └───────────────────────────────────────────────────────────────────┘    │
│                                   │                                      │
│  ┌────────────────────────────────┼─────────────────────────────────┐    │
│  │                      Storage Layer                                │    │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────────┐   │    │
│  │  │ PostgreSQL  │  │   Redis     │  │      S3 Compatible      │   │    │
│  │  │ (Metadata)  │  │  (Cache)    │  │ (Video/Screen Records)  │   │    │
│  │  └─────────────┘  └─────────────┘  └─────────────────────────┘   │    │
│  └───────────────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    │ HTTPS
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                          ADMIN PANEL (React SPA)                         │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐    │
│  │Session List │  │Video Player │  │Event Timeline│  │Reports Dashboard│ │
│  └─────────────┘  └─────────────┘  └─────────────┘  └─────────────┘    │
└─────────────────────────────────────────────────────────────────────────┘
```

## 2. Компоненты системы

### 2.1 Frontend (React + TypeScript)
- **WebRTC модуль** - захват видео с веб-камеры
- **Screen Capture API** - захват экрана пользователя
- **Event Tracking** - отслеживание событий браузера (blur/focus, visibility)
- **WebSocket Client** - потоковая передача данных на сервер

### 2.2 Backend (FastAPI)
- **REST API** - управление сессиями, отчёты
- **WebSocket Server** - обработка видеопотоков в реальном времени
- **Detection Engine** - система правил для обнаружения нарушений
- **Recording Service** - запись и хранение видео

### 2.3 Детекторы нарушений
#### Видеоанализ (Camera):
- Отсутствие лица в кадре
- Несколько лиц в кадре
- Отведение взгляда (eye tracking)
- Повороты головы (head pose estimation)
- Использование телефона (hand gesture detection)
- Посторонние движения

#### Анализ экрана (Screen):
- Переключение вкладок (visibility API)
- Потеря фокуса окна (blur event)
- Выход из полноэкранного режима
- Использование запрещённых приложений
- OCR анализ содержимого экрана

### 2.4 Хранение данных
- **PostgreSQL** - метаданные сессий, события, нарушения
- **S3-compatible storage** - видео записи, скриншоты
- **Redis** - кэширование активных сессий, real-time статусы

## 3. Поток данных

```
1. START SESSION
   Java App → POST /api/v1/proctoring/start (JWT) → Proctoring Service
   Proctoring Service → Create Session → Return session_id
   
2. CLIENT INITIALIZATION
   Browser → Request Camera/Screen Permissions
   Browser → Connect WebSocket ws://{host}/ws/{session_id}
   Browser → Start Streaming (video frames + screen captures)
   
3. REAL-TIME PROCESSING
   WebSocket → Video Frame → Face Detector → Events
   WebSocket → Screen Capture → Screen Analyzer → Events
   Events → Rule Engine → Severity Score → Store Violation
   
4. END SESSION
   Browser → POST /api/v1/proctoring/stop/{session_id}
   Proctoring Service → Generate Report → Store in DB
   Proctoring Service → Webhook → Java App (async)
   
5. REVIEW
   Admin Panel → GET /api/v1/proctoring/report/{session_id}
   Admin Panel → Load Video from S3 + Events Timeline
```

## 4. Модель данных

### Session
```json
{
  "session_id": "uuid",
  "user_id": "string",
  "exam_id": "string",
  "status": "pending|active|paused|completed|violated",
  "started_at": "datetime",
  "ended_at": "datetime",
  "total_duration_sec": number,
  "risk_score": number (0-100),
  "violation_count": number
}
```

### Violation Event
```json
{
  "event_id": "uuid",
  "session_id": "uuid",
  "timestamp": "datetime",
  "type": "face_absent|multi_face|gaze_avoided|head_turned|phone_detected|tab_switched|app_changed|fullscreen_exited",
  "severity": "low|medium|high|critical",
  "confidence": number (0-1),
  "description": "string",
  "frame_snapshot_url": "string (S3)",
  "metadata": {}
}
```

## 5. Интеграция с Java (Spring Boot)

### Конфигурация клиента
```yaml
proctoring:
  base-url: https://proctoring.corporate.local
  api-key: ${PROCTORING_API_KEY}
  jwt-secret: ${JWT_SECRET}
  webhook-url: https://corp-platform.local/api/webhooks/proctoring
```

### SDK методы
- `startProctoring(sessionId, userId, examId)` - начать сессию
- `stopProctoring(sessionId)` - завершить сессию
- `getSessionReport(sessionId)` - получить отчёт
- `getRiskAssessment(sessionId)` - оценка рисков

## 6. Безопасность и приватность

- **JWT Authentication** - все API запросы аутентифицированы
- **User Consent** - явное согласие на запись перед началом
- **Data Encryption** - шифрование видео при хранении
- **GDPR Compliance** - автоматическое удаление данных через N дней
- **Access Control** - роли для просмотра записей (admin, reviewer, instructor)

## 7. Масштабирование

- **Horizontal Scaling** - несколько инстансов прокторинг сервиса
- **Load Balancer** - распределение WebSocket соединений
- **Redis Pub/Sub** - координация между инстансами
- **Kubernetes** - оркестрация контейнеров
- **Auto-scaling** - по количеству активных сессий

## 8. Docker развёртывание

```bash
# Build images
docker-compose build

# Start services
docker-compose up -d

# Services:
# - proctoring-backend (FastAPI + OpenCV)
# - proctoring-admin (React SPA + Nginx)
# - postgres (Metadata DB)
# - redis (Cache & Sessions)
# - minio (S3-compatible storage)
```

## 9. Мониторинг и логи

- **Prometheus** - метрики (активные сессии, нарушения, latency)
- **Grafana** - дашборды
- **ELK Stack** - централизованное логирование
- **Alerts** - уведомления о критических нарушениях
