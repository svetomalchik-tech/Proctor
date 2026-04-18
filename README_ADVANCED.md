# Advanced Anti-Cheating Proctoring System

Production-ready online proctoring system with **Coursera/ProctorU-level anti-cheating capabilities**. Designed for integration with corporate Java/Spring Boot learning platforms.

## 🎯 Core Features

### Advanced Behavior Analysis (Pattern Recognition)
- **Phone Cheating Detection**: Combines gaze analysis + object detection
- **Second Person/Consultant Detection**: Multi-face tracking with voice correlation
- **Off-Screen Reading Pattern**: Repetitive head movement analysis
- **Absence Fraud**: Detects keyboard/mouse activity when user is away from camera
- **Frequent Tab Switching**: Rapid switching pattern recognition (>3 switches/min)

### Computer Vision Capabilities
- Face detection & tracking (MediaPipe Face Mesh)
- Gaze estimation (eye landmark analysis)
- Head pose estimation (asymmetry detection)
- Phone/object detection (heuristic + ML-ready)
- Multi-person detection

### Screen Monitoring
- Tab switching detection
- Window focus/blur tracking
- Fullscreen exit detection
- Clipboard monitoring
- Developer tools detection
- Suspicious application detection (Telegram, WhatsApp, etc.)

### Risk Assessment Engine
- Real-time risk scoring (0-100)
- Severity levels: LOW, MEDIUM, HIGH, CRITICAL
- Pattern-based confidence scoring
- Automatic termination recommendations

## 🏗️ Architecture

```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│   React Client  │────▶│  FastAPI Backend │────▶│   PostgreSQL    │
│ (WebRTC + Screen)│ WS  │ (Session Manager)│     │   (Metadata)    │
└─────────────────┘     └──────────────────┘     └─────────────────┘
                               │
                               ▼
                        ┌──────────────────┐
                        │  CV Processor    │
                        │  (MediaPipe)     │
                        └──────────────────┘
                               │
                               ▼
                        ┌──────────────────┐
                        │ Behavior Analyzer│
                        │ (Pattern Detect) │
                        └──────────────────┘
                               │
                               ▼
                        ┌──────────────────┐
                        │    MinIO (S3)    │
                        │  (Video Storage) │
                        └──────────────────┘
```

## 📁 Project Structure

```
/workspace
├── backend/
│   ├── app/
│   │   ├── api/              # REST API endpoints
│   │   ├── services/         # Business logic
│   │   │   ├── behavior_analyzer.py   # Pattern recognition engine
│   │   │   ├── cv_processor.py        # Computer vision (MediaPipe)
│   │   │   ├── screen_analyzer.py     # Screen activity monitor
│   │   │   └── session_manager.py     # WebSocket orchestrator
│   │   ├── models/           # Pydantic models
│   │   ├── storage/          # Database & S3 clients
│   │   ├── main.py           # FastAPI application
│   │   └── config.py         # Configuration
│   ├── requirements.txt
│   └── Dockerfile
├── admin-panel/
│   ├── src/                  # React admin UI
│   └── Dockerfile
├── integration-examples/
│   └── java-spring/          # Spring Boot client example
├── docker/
│   └── docker-compose.yml    # Full stack deployment
├── docs/
│   └── ARCHITECTURE.md       # Detailed architecture
└── openapi/
    └── proctoring-api.yaml   # OpenAPI 3.0 specification
```

## 🚀 Quick Start

### Using Docker Compose (Recommended)

```bash
cd /workspace/docker
docker-compose up -d
```

Services will be available at:
- **Backend API**: http://localhost:8000
- **Admin Panel**: http://localhost:3000
- **MinIO Console**: http://localhost:9001 (minioadmin/minioadmin)
- **PostgreSQL**: localhost:5432

### Manual Backend Setup

```bash
cd /workspace/backend
pip install -r requirements.txt
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

## 🔌 API Endpoints

### REST API

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/proctoring/start` | Start proctoring session |
| POST | `/api/v1/proctoring/{id}/stop` | Stop session |
| GET | `/api/v1/proctoring/{id}/report` | Get session report |
| GET | `/api/v1/proctoring/{id}/risk-assessment` | Real-time risk score |
| GET | `/api/v1/sessions/{id}/status` | Session status |
| POST | `/api/v1/sessions/{id}/terminate` | Force terminate |

### WebSocket

```
WS /ws/{session_id}?user_id={user_id}
```

**Message Types:**
- `video_frame`: Base64 encoded video frame
- `screen_event`: Screen activity event
- `heartbeat`: Ping for risk assessment
- `consent_given`: User consent confirmation

**Server Responses:**
- `alert`: High-confidence cheating pattern detected
- `heartbeat_ack`: Risk assessment update
- `system_message`: Info/warning messages

## 📊 Detection Patterns

### Pattern Types & Severity

| Pattern | Trigger Conditions | Severity | Confidence |
|---------|-------------------|----------|------------|
| **PHONE_CHEATING** | Phone detected in frame + gaze down | HIGH | 0.95 |
| **SECOND_PERSON** | Multiple faces detected | CRITICAL | 0.90 |
| **ABSENCE_FRAUD** | Face lost + input activity | HIGH | 0.85 |
| **FREQUENT_SWITCHING** | >3 tab switches in 1 min | MEDIUM | 0.80 |
| **READING_OFF_SCREEN** | >4 head turns in 1 min | MEDIUM | 0.75 |
| **GAZE_AVOIDANCE** | Looking away >5 seconds | MEDIUM | 0.70 |

### Risk Score Calculation

```
Risk Score = Σ(Event Severity × Pattern Confidence)

0-20:   LOW      → Monitor
21-50:  MEDIUM   → Flag for review
51-80:  HIGH     → Warn user
81-100: CRITICAL → Recommend termination
```

## 💻 Frontend Integration Example

```javascript
// Connect to WebSocket
const ws = new WebSocket(`ws://localhost:8000/ws/${sessionId}?user_id=${userId}`);

// Send video frames (30fps)
setInterval(() => {
  videoElement.captureStream().requestFrame();
  const base64Frame = canvas.toDataURL('image/jpeg', 0.8);
  ws.send(JSON.stringify({
    type: 'video_frame',
    frame: base64Frame
  }));
}, 1000/30);

// Listen for alerts
ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  if (data.type === 'alert') {
    console.warn('Cheating pattern detected:', data.data);
    // Show warning to user or notify admin
  }
};
```

## ☕ Java/Spring Boot Integration

See `integration-examples/java-spring/` for complete example.

```java
@Autowired
private ProctoringClient proctoringClient;

// Start proctoring before exam
@PostMapping("/exam/start")
public ResponseEntity<?> startExam(@RequestBody ExamRequest request) {
    ProctoringSession session = proctoringClient.startProctoring(
        request.getUserId(), 
        request.getExamId()
    );
    
    // Return session ID to frontend
    return ResponseEntity.ok(session.getSessionId());
}

// Get report after exam
@GetMapping("/exam/{id}/report")
public ProctoringReport getExamReport(@PathVariable Long id) {
    return proctoringClient.getSessionReport(id.toString());
}
```

## 🔒 Security & Privacy

- **User Consent**: Required before recording starts
- **JWT Authentication**: All API endpoints protected
- **Data Encryption**: AES-256 for stored videos
- **GDPR Compliance**: Auto-deletion after retention period
- **RBAC**: Role-based access to recordings
- **Secure Transmission**: WSS (WebSocket Secure) in production

## ⚙️ Configuration

Key environment variables (`backend/.env`):

```bash
DATABASE_URL=postgresql://postgres:password@localhost:5432/proctoring
MINIO_ENDPOINT=localhost:9000
MINIO_ACCESS_KEY=minioadmin
MINIO_SECRET_KEY=minioadmin
JWT_SECRET=your-secret-key
VIDEO_RETENTION_DAYS=30
MAX_RISK_SCORE=100
```

## 🧪 Testing

```bash
# Run unit tests
pytest backend/app/tests

# Test CV processor
python backend/app/tests/test_cv_processor.py

# Load test WebSocket
websocket-client ws://localhost:8000/ws/test-session
```

## 📈 Scalability

- **Horizontal Scaling**: Stateless backend, Redis for session state
- **Video Processing**: Offload to separate worker queue (Celery/RQ)
- **Storage**: S3-compatible object storage (MinIO/AWS S3)
- **Database**: PostgreSQL with read replicas
- **CDN**: For admin panel static assets

## 🛠️ Tech Stack

| Component | Technology |
|-----------|------------|
| Backend | Python 3.9+, FastAPI, Uvicorn |
| CV Engine | MediaPipe, OpenCV, NumPy |
| Frontend | React 18, TypeScript, WebRTC |
| Database | PostgreSQL 14 |
| Cache | Redis 7 |
| Storage | MinIO (S3-compatible) |
| Messaging | WebSocket |
| Container | Docker, Docker Compose |

## 📝 License

Proprietary - For corporate use only.

## 👥 Support

For integration support, contact the development team.
