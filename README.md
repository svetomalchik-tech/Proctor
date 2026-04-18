# Система прокторинга для корпоративного обучения

Production-ready микросервис прокторинга для интеграции с корпоративными системами обучения на Java/Spring Boot.

## 📋 Оглавление

- [Возможности](#возможности)
- [Архитектура](#архитектура)
- [Быстрый старт](#быстрый-старт)
- [API Документация](#api-документация)
- [Интеграция с Java](#интеграция-с-java-spring-boot)
- [Админ Панель](#админ-панель)
- [Конфигурация](#конфигурация)
- [Развёртывание](#развёртывание)

---

## Возможности

### Анализ видео с камеры
- ✅ **Детекция лица** - отсутствие лица в кадре
- ✅ **Несколько лиц** - обнаружение более одного человека
- ✅ **Отведение взгляда** - eye tracking с порогом >3 сек
- ✅ **Повороты головы** - head pose estimation (yaw, pitch, roll)
- ✅ **Использование телефона** - детекция жестов руки у уха
- ✅ **Посторонние движения** - аномальная активность

### Анализ захвата экрана
- ✅ **Переключение вкладок** - visibility API detection
- ✅ **Потеря фокуса** - window blur events
- ✅ **Выход из fullscreen** - fullscreen mode monitoring
- ✅ **Запрещённые приложения** - whitelist/blacklist
- ✅ **Мессенджеры** - Telegram, WhatsApp, Slack и др.
- ✅ **OCR анализ** - распознавание текста на экране (опционально)

### Система нарушений
| Тип нарушения | Severity | Описание |
|--------------|----------|----------|
| `face_absent` | medium | Лицо не обнаружено в кадре |
| `multi_face` | high | Несколько лиц в кадре |
| `gaze_avoided` | low-medium | Отведение взгляда >3 сек |
| `head_turned` | medium | Поворот головы >30° |
| `phone_detected` | high | Использование телефона |
| `tab_switched` | low-medium | Переключение вкладки |
| `app_changed` | medium | Смена приложения |
| `fullscreen_exited` | medium | Выход из полноэкранного режима |
| `messenger_detected` | high | Использование мессенджера |

---

## Архитектура

```
┌─────────────────────────────────────────────────────────────┐
│           CORPORATE LEARNING PLATFORM (Java)                │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐      │
│  │   Auth   │ │   Test   │ │   User   │ │  Report  │      │
│  │ Service  │ │ Delivery │ │  Mgmt    │ │  Viewer  │      │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘      │
└─────────────────────────────────────────────────────────────┘
                            │ REST API + JWT
                            │ Webhooks
                            ▼
┌─────────────────────────────────────────────────────────────┐
│              PROCTORING MICROSERVICE                        │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  FastAPI Backend (Python)                            │  │
│  │  - REST API: /api/v1/proctoring/*                    │  │
│  │  - WebSocket: /ws/{session_id}                       │  │
│  └──────────────────────────────────────────────────────┘  │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  Detection Services                                  │  │
│  │  - Face Detector (MediaPipe)                         │  │
│  │  - Screen Analyzer                                   │  │
│  │  - Rule Engine                                       │  │
│  └──────────────────────────────────────────────────────┘  │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  Storage                                             │  │
│  │  - PostgreSQL (metadata)                             │  │
│  │  - Redis (cache/sessions)                            │  │
│  │  - MinIO/S3 (video recordings)                       │  │
│  └──────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
                            │ HTTPS
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                  ADMIN PANEL (React SPA)                    │
│  - Dashboard со статистикой                                 │
│  - Список сессий с фильтрацией                              │
│  - Видео плеер с таймлайном нарушений                       │
│  - Отчёты и экспорт                                         │
└─────────────────────────────────────────────────────────────┘
```

---

## Быстрый старт

### Вариант 1: Docker Compose (рекомендуется)

```bash
# Клонировать репозиторий
cd /workspace

# Запустить все сервисы
docker-compose -f docker/docker-compose.yml up -d

# Проверить статус
docker-compose -f docker/docker-compose.yml ps

# Просмотр логов
docker-compose -f docker/docker-compose.yml logs -f proctoring-backend
```

**Доступные сервисы:**
- Backend API: http://localhost:8000
- Admin Panel: http://localhost:3000
- MinIO Console: http://localhost:9001 (admin/admin_secret)
- PostgreSQL: localhost:5432

### Вариант 2: Локальная разработка

#### Backend
```bash
cd backend

# Создать виртуальное окружение
python -m venv venv
source venv/bin/activate  # Linux/Mac
# или venv\Scripts\activate  # Windows

# Установить зависимости
pip install -r requirements.txt

# Запустить сервер
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

#### Frontend (клиент прокторинга)
```bash
cd frontend

# Установить зависимости
npm install

# Запустить dev сервер
npm run dev
```

#### Admin Panel
```bash
cd admin-panel

# Установить зависимости
npm install

# Запустить dev сервер
npm run dev
```

---

## API Документация

### Основные endpoint'ы

#### Начать сессию
```http
POST /api/v1/proctoring/start
Content-Type: application/json
Authorization: Bearer <jwt_token>

{
  "user_id": "emp-12345",
  "exam_id": "exam-java-certification-2024",
  "settings": {
    "duration_minutes": 60,
    "require_fullscreen": true,
    "detection_sensitivity": "medium"
  }
}
```

**Ответ:**
```json
{
  "session_id": "550e8400-e29b-41d4-a716-446655440000",
  "user_id": "emp-12345",
  "exam_id": "exam-java-certification-2024",
  "status": "pending",
  "websocket_url": "ws://localhost:8000/ws/550e8400-e29b-41d4-a716-446655440000",
  "consent_required": true
}
```

#### Завершить сессию
```http
POST /api/v1/proctoring/{session_id}/stop
Authorization: Bearer <jwt_token>
```

#### Получить отчёт
```http
GET /api/v1/proctoring/{session_id}/report?include_video_urls=true
Authorization: Bearer <jwt_token>
```

#### Получить оценку рисков
```http
GET /api/v1/proctoring/{session_id}/risk-assessment
Authorization: Bearer <jwt_token>
```

### WebSocket протокол

**Подключение:**
```javascript
const ws = new WebSocket(`ws://localhost:8000/ws/${sessionId}`);
```

**Отправка кадров:**
```javascript
// Видео с камеры
ws.send(JSON.stringify({
  type: 'video_frame',
  frame: 'data:image/jpeg;base64,...'
}));

// Скринкаст
ws.send(JSON.stringify({
  type: 'screen_capture',
  image: 'data:image/jpeg;base64,...',
  active_window: 'Chrome',
  is_fullscreen: true
}));
```

**Получение событий:**
```javascript
ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  
  if (data.type === 'video_analysis') {
    console.log('Нарушения:', data.violations);
  }
};
```

Полная спецификация API доступна в [`openapi/proctoring-api.yaml`](openapi/proctoring-api.yaml).

---

## Интеграция с Java (Spring Boot) и JavaScript (React)

### Полная инструкция по интеграции

📖 **Подробное руководство по интеграции** доступно в документе [`docs/INTEGRATION_GUIDE.md`](docs/INTEGRATION_GUIDE.md)

Руководство включает:
- ✅ Пошаговую инструкцию для backend (Java/Spring Boot)
- ✅ Пошаговую инструкцию для frontend (JavaScript/React/TypeScript)
- ✅ Примеры кода для всех компонентов
- ✅ Настройку безопасности (JWT, CORS, HTTPS)
- ✅ Unit, Integration и E2E тесты
- ✅ Production checklist
- ✅ Troubleshooting распространённых проблем

### 1. Добавить зависимости

```xml
<!-- pom.xml -->
<dependency>
    <groupId>org.springframework.boot</groupId>
    <artifactId>spring-boot-starter-web</artifactId>
</dependency>
<dependency>
    <groupId>org.projectlombok</groupId>
    <artifactId>lombok</artifactId>
    <optional>true</optional>
</dependency>
```

### 2. Конфигурация

```yaml
# application.yml
proctoring:
  base-url: ${PROCTORING_BASE_URL:http://localhost:8000/api/v1}
  api-key: ${PROCTORING_API_KEY:your-secret-api-key}
  risk-thresholds:
    auto-reject: 75
    needs-review: 50
    auto-approve: 25
```

### 3. Использование в сервисе экзаменов

```java
@Service
public class ExamService {
    
    @Autowired
    private ProctoringClient proctoringClient;
    
    public ExamResult completeExam(String userId, String examId, String sessionId) {
        // Завершить сессию прокторинга
        ProctoringDto.EndSessionResponse result = proctoringClient.stopProctoring(sessionId);
        
        // Получить оценку рисков
        ProctoringDto.RiskAssessment risk = proctoringClient.getRiskAssessment(sessionId);
        
        // Принять решение на основе risk_score
        if (risk.getRiskScore() >= 75) {
            return ExamResult.REJECTED;
        } else if (risk.getRiskScore() >= 50) {
            return ExamResult.NEEDS_REVIEW;
        }
        
        return ExamResult.APPROVED;
    }
}
```

Примеры кода доступны в [`integration-examples/java-spring/`](integration-examples/java-spring/).

Полная документация: [`docs/INTEGRATION_GUIDE.md`](docs/INTEGRATION_GUIDE.md)

---

## Админ Панель

### Функционал

1. **Dashboard** - статистика и метрики
2. **Список сессий** - фильтрация, сортировка, пагинация
3. **Детали сессии** - видео, таймлайн нарушений, отчёт
4. **Экспорт** - PDF, CSV

### Запуск

```bash
cd admin-panel
npm install
npm run dev
```

Документация админ панели: [`admin-panel/README.md`](admin-panel/README.md)

---

## Конфигурация

### Переменные окружения (Backend)

| Переменная | Описание | По умолчанию |
|-----------|----------|--------------|
| `DATABASE_URL` | PostgreSQL connection string | - |
| `REDIS_URL` | Redis connection URL | redis://localhost:6379 |
| `S3_ENDPOINT` | MinIO/S3 endpoint | http://localhost:9000 |
| `S3_ACCESS_KEY` | S3 access key | proctoring_admin |
| `S3_SECRET_KEY` | S3 secret key | proctoring_minio_secret |
| `JWT_SECRET` | JWT signing key | - |
| `EYE_AWAY_THRESHOLD_SEC` | Порог отведения глаз (сек) | 3.0 |
| `HEAD_TURN_THRESHOLD_DEG` | Порог поворота головы (градусы) | 30.0 |
| `FULLSCREEN_REQUIRED` | Требовать полный экран | true |

### Настройка детекции

```python
# config.py
class Settings(BaseSettings):
    # Видеоанализ
    EYE_AWAY_THRESHOLD_SEC: float = 3.0
    HEAD_TURN_THRESHOLD_DEG: float = 30.0
    PHONE_DETECTION_CONFIDENCE: float = 0.7
    MULTI_FACE_DETECTION: bool = True
    
    # Анализ экрана
    TAB_SWITCH_DETECTION: bool = True
    FULLSCREEN_REQUIRED: bool = True
    ALLOWED_APPS: list[str] = ["Chrome", "Firefox", "IntelliJ IDEA"]
```

---

## Развёртывание

### Production Checklist

- [ ] Изменить JWT_SECRET на случайную строку
- [ ] Настроить HTTPS (TLS сертификаты)
- [ ] Настроить CORS для домена продакшена
- [ ] Включить rate limiting
- [ ] Настроить мониторинг (Prometheus/Grafana)
- [ ] Настроить логирование (ELK Stack)
- [ ] Настроить backup базы данных
- [ ] Настроить auto-scaling

### Kubernetes

```yaml
# k8s/deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: proctoring-backend
spec:
  replicas: 3
  selector:
    matchLabels:
      app: proctoring-backend
  template:
    spec:
      containers:
      - name: backend
        image: proctoring-backend:latest
        ports:
        - containerPort: 8000
        env:
        - name: DATABASE_URL
          valueFrom:
            secretKeyRef:
              name: proctoring-secrets
              key: database-url
```

### Масштабирование

- **Горизонтальное**: несколько инстансов backend за load balancer
- **WebSocket**: sticky sessions для сохранения соединений
- **Redis**: для координации между инстансами
- **Database**: connection pooling, read replicas

---

## Безопасность и приватность

- ✅ **JWT Authentication** - все API запросы аутентифицированы
- ✅ **User Consent** - явное согласие на запись перед началом сессии
- ✅ **Data Encryption** - шифрование видео при хранении (AES-256)
- ✅ **GDPR Compliance** - автоматическое удаление данных через N дней
- ✅ **Access Control** - RBAC для просмотра записей
- ✅ **Audit Logs** - логирование всех действий администраторов

---

## Лицензия

MIT License - см. [LICENSE](LICENSE)

---

## Контакты

- Email: proctoring@corporate.local
- Документация: `/docs`
- OpenAPI Spec: `/openapi/proctoring-api.yaml`