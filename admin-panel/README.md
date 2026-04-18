# Система прокторинга - Админ Панель

## Структура проекта

```
admin-panel/
├── src/
│   ├── components/
│   │   ├── SessionList.tsx       # Список сессий с фильтрацией
│   │   ├── SessionDetail.tsx     # Детали сессии
│   │   ├── VideoPlayer.tsx       # Видеоплеер с таймлайном
│   │   ├── ViolationTimeline.tsx # Таймлайн нарушений
│   │   ├── RiskIndicator.tsx     # Индикатор риска
│   │   └── Dashboard.tsx         # Главная панель статистики
│   ├── services/
│   │   └── api.ts                # API клиент
│   ├── types/
│   │   └── index.ts              # TypeScript типы
│   ├── hooks/
│   │   └── useSessions.ts        # Хук для работы с сессиями
│   ├── App.tsx
│   └── main.tsx
├── public/
├── package.json
├── tsconfig.json
├── vite.config.ts
└── Dockerfile
```

## Функционал админ панели

### 1. Dashboard (Главная панель)
- Статистика за день/неделю/месяц
- Количество активных сессий
- График нарушений по типам
- Средний риск cheating

### 2. Список сессий
- Таблица со всеми сессиями
- Фильтры:
  - По статусу (active, completed, violated)
  - По экзамену
  - По пользователю
  - По диапазону дат
  - По минимальному риску
- Сортировка по всем колонкам
- Пагинация

### 3. Детали сессии
- Основная информация (пользователь, экзамен, длительность)
- Видео плеер с возможностью:
  - Просмотра записи камеры
  - Просмотра записи экрана
  - Режим picture-in-picture
- Таймлайн с отметками нарушений
- Клик на нарушение → переход к моменту в видео
- Список всех нарушений с деталями

### 4. Отчёт по сессии
- Оценка риска (0-100)
- Рекомендация (approve / manual_review / reject)
- Детальный разбор факторов риска
- Экспорт в PDF

## API Endpoints для админки

```typescript
// GET /api/v1/admin/sessions
// Получение списка сессий с фильтрацией
interface SessionsQuery {
  status?: 'pending' | 'active' | 'completed' | 'violated';
  exam_id?: string;
  user_id?: string;
  date_from?: string;
  date_to?: string;
  min_risk_score?: number;
  page?: number;
  page_size?: number;
}

// GET /api/v1/admin/sessions/:sessionId
// Детали сессии

// GET /api/v1/admin/sessions/:sessionId/report
// Полный отчёт

// GET /api/v1/admin/sessions/:sessionId/video?type=camera|screen
// Видео сессии

// POST /api/v1/admin/sessions/:sessionId/review
// Отправка ревью (для ручного просмотра)
interface ReviewRequest {
  reviewer_id: string;
  decision: 'approve' | 'reject' | 'needs_review';
  comments?: string;
}
```

## Компоненты

### SessionList.tsx
```tsx
import { useState } from 'react';
import { useSessions } from '../hooks/useSessions';
import { SessionTable } from './SessionTable';
import { SessionFilters } from './SessionFilters';

export function SessionList() {
  const [filters, setFilters] = useState<SessionFilters>({});
  const { sessions, loading, pagination } = useSessions(filters);

  return (
    <div className="session-list">
      <SessionFilters filters={filters} onChange={setFilters} />
      <SessionTable 
        sessions={sessions} 
        loading={loading}
        pagination={pagination}
      />
    </div>
  );
}
```

### VideoPlayer.tsx
```tsx
import { useRef, useEffect } from 'react';
import { ViolationTimeline } from './ViolationTimeline';

interface VideoPlayerProps {
  cameraUrl: string;
  screenUrl: string;
  violations: Violation[];
  onTimeChange: (time: number) => void;
}

export function VideoPlayer({ 
  cameraUrl, 
  screenUrl, 
  violations,
  onTimeChange 
}: VideoPlayerProps) {
  const videoRef = useRef<HTMLVideoElement>(null);
  const [isPiP, setIsPiP] = useState(false);

  const togglePiP = async () => {
    if (document.pictureInPictureElement) {
      await document.exitPictureInPicture();
    } else if (videoRef.current) {
      await videoRef.current.requestPictureInPicture();
      setIsPiP(true);
    }
  };

  return (
    <div className="video-player">
      <div className="video-container">
        <video ref={videoRef} src={cameraUrl} controls />
        <video src={screenUrl} controls className={isPiP ? 'pip' : ''} />
      </div>
      <ViolationTimeline 
        violations={violations}
        onSeek={(time) => {
          if (videoRef.current) {
            videoRef.current.currentTime = time;
          }
          onTimeChange(time);
        }}
      />
    </div>
  );
}
```

### RiskIndicator.tsx
```tsx
interface RiskIndicatorProps {
  score: number; // 0-100
}

export function RiskIndicator({ score }: RiskIndicatorProps) {
  const getRiskLevel = (score: number) => {
    if (score >= 75) return { level: 'critical', color: '#dc3545' };
    if (score >= 50) return { level: 'high', color: '#fd7e14' };
    if (score >= 25) return { level: 'medium', color: '#ffc107' };
    return { level: 'low', color: '#28a745' };
  };

  const { level, color } = getRiskLevel(score);

  return (
    <div className="risk-indicator" style={{ borderColor: color }}>
      <div className="risk-score" style={{ color }}>{score}</div>
      <div className="risk-level">{level.toUpperCase()}</div>
    </div>
  );
}
```

## Запуск в development

```bash
cd admin-panel
npm install
npm run dev
```

## Build для production

```bash
npm run build
```

## Docker

```bash
docker build -t proctoring-admin .
docker run -p 3000:80 proctoring-admin
```
