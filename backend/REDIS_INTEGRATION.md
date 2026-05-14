# Redis Integration Guide

## Обзор

Система прокторинга теперь поддерживает Redis для распределённого хранения сессий и данных. Это позволяет:
- Масштабировать приложение на несколько серверов
- Сохранять данные сессий при перезапуске
- Получать статистику по активным сессиям в реальном времени
- Автоматически очищать устаревшие данные

## Установка Redis

### Docker (рекомендуется)
```bash
docker run -d --name redis -p 6379:6379 redis:latest
```

### Ubuntu/Debian
```bash
sudo apt-get update
sudo apt-get install redis-server
sudo systemctl start redis
```

### macOS (Homebrew)
```bash
brew install redis
brew services start redis
```

## Конфигурация

### Переменные окружения

Добавьте в `.env` файл:

```env
# Redis connection
PROCTOR_REDIS_URL=redis://localhost:6379/0

# Optional: Redis authentication
PROCTOR_REDIS_PASSWORD=your_password

# Optional: Redis cluster (future)
# PROCTOR_REDIS_URL=redis://node1:6379,redis://node2:6379,redis://node3:6379
```

### Настройки в config.py

```python
class Settings(BaseSettings):
    # Redis (для хранения сессий в production)
    REDIS_URL: Optional[str] = None  # "redis://localhost:6379/0"
    
    class Config:
        env_file = ".env"
        env_prefix = "PROCTOR_"
```

## Архитектура

### Ключи Redis

Система использует следующие ключи:

| Ключ | Тип | Описание | TTL |
|------|-----|----------|-----|
| `proctor:session:{session_id}` | Hash | Метаданные сессии | 1 час |
| `proctor:session:{session_id}:report` | String | Финальный отчёт | 24 часа |
| `proctor:events:{session_id}` | List | События сессии (последние 1000) | - |
| `proctor:active_sessions` | Set | IDs активных сессий | - |

### Структура данных

**Session Metadata (Hash):**
```json
{
  "session_id": "sess_123",
  "user_id": "user_456",
  "start_time": 1234567890.123,
  "is_active": true,
  "video_frames_count": 150,
  "end_time": 1234567990.456
}
```

**Events (List):**
```json
[
  {
    "timestamp": 1234567890.123,
    "type": "FACE_AWAY",
    "severity": "MEDIUM",
    "source": "cv"
  },
  {
    "timestamp": 1234567891.456,
    "type": "TAB_SWITCH",
    "severity": 5,
    "source": "screen",
    "details": {"previous_url": "..."}
  }
]
```

## API

### Health Check

```bash
curl http://localhost:8000/health
```

Ответ:
```json
{
  "status": "healthy",
  "active_sessions": 5,
  "redis_status": "connected",
  "timestamp": 1234567890.123
}
```

### Session Status

```bash
curl http://localhost:8000/api/v1/sessions/{session_id}/status
```

### Terminate Session

```bash
curl -X POST http://localhost:8000/api/v1/sessions/{session_id}/terminate
```

## Управление сессиями

### Python API

```python
from app.services.session_manager import (
    create_session,
    get_session,
    remove_session,
    get_active_session_ids,
    get_session_count
)
from app.core.redis_client import redis_client

# Создание сессии
session = await create_session(session_id, user_id, websocket)

# Получение сессии (проверяет кэш и Redis)
session = await get_session(session_id)

# Удаление сессии (очищает память и Redis)
await remove_session(session_id)

# Получить все активные сессии
active_ids = await get_active_session_ids()

# Получить количество активных сессий
count = await get_session_count()

# Проверка статуса Redis
if redis_client.is_connected:
    print("Redis connected")
else:
    print("Running in fallback mode")
```

## Fallback режим

Если Redis недоступен, система автоматически переключается на in-memory хранение:

```python
# В main.py startup
redis_connected = await init_redis()
if redis_connected:
    logger.info("Redis storage enabled")
else:
    logger.warning("Redis not available, using in-memory storage only")
```

**Важно:** В fallback режиме:
- Данные теряются при перезапуске сервера
- Невозможно масштабирование на несколько серверов
- Рекомендуется только для разработки/тестирования

## Мониторинг

### Проверка подключения

```bash
redis-cli ping
# Ответ: PONG
```

### Просмотр ключей

```bash
# Все ключи прокторинга
redis-cli KEYS "proctor:*"

# Активные сессии
redis-cli SMEMBERS proctor:active_sessions

# Длина списка событий
redis-cli LLEN proctor:events:{session_id}
```

### Статистика

```bash
# Информация о сервере
redis-cli INFO

# Использование памяти
redis-cli INFO memory

# Количество подключений
redis-cli CLIENT LIST | wc -l
```

## Production рекомендации

### 1. Redis Cluster

Для высокой доступности используйте кластер:

```env
PROCTOR_REDIS_URL=redis://node1:6379,redis://node2:6379,redis://node3:6379
```

### 2. Sentinel

Для автоматического failover:

```env
PROCTOR_REDIS_URL=redis://sentinel1:26379,redis://sentinel2:26379,redis://sentinel3:26379?master_id=mymaster
```

### 3. Persistence

Включите AOF для сохранения данных:

```conf
# redis.conf
appendonly yes
appendfsync everysec
```

### 4. Memory Limit

Ограничьте использование памяти:

```conf
maxmemory 2gb
maxmemory-policy allkeys-lru
```

### 5. Security

```conf
# redis.conf
requirepass your_strong_password
bind 127.0.0.1
protected-mode yes
```

### 6. Monitoring

Используйте Redis Insights или Prometheus + Grafana:

```yaml
# docker-compose.yml
redis-exporter:
  image: oliver006/redis_exporter
  ports:
    - "9121:9121"
  environment:
    REDIS_ADDR: redis://redis:6379
```

## Тестирование

### Запуск тестов

```bash
cd backend
python -m pytest tests/test_redis_client.py -v
```

### Локальное тестирование

```python
# test_redis_local.py
import asyncio
from app.core.redis_client import redis_client, init_redis, close_redis

async def test():
    # Подключение
    connected = await init_redis()
    print(f"Connected: {connected}")
    
    # Запись данных
    await redis_client.set("test_key", {"data": "value"})
    
    # Чтение данных
    data = await redis_client.get("test_key")
    print(f"Data: {data}")
    
    # Очистка
    await redis_client.delete("test_key")
    
    # Отключение
    await close_redis()

asyncio.run(test())
```

## Troubleshooting

### Ошибка подключения

```
Failed to connect to Redis: Connection refused
```

**Решение:**
1. Проверьте, запущен ли Redis: `redis-cli ping`
2. Проверьте порт: `netstat -tlnp | grep 6379`
3. Проверьте firewall: `sudo ufw status`

### Таймауты

```
Redis operation timeout
```

**Решение:**
1. Увеличьте таймауты в настройках подключения
2. Проверьте нагрузку на Redis: `redis-cli INFO stats`
3. Оптимизируйте запросы (используйте pipeline)

### Нехватка памяти

```
OOM command not allowed when used memory > 'maxmemory'
```

**Решение:**
1. Увеличьте maxmemory в redis.conf
2. Настройте политику eviction: `maxmemory-policy allkeys-lru`
3. Очистите старые ключи вручную

## Миграция с in-memory

### Шаг 1: Установка Redis

```bash
docker run -d --name redis -p 6379:6379 redis:latest
```

### Шаг 2: Конфигурация

Добавьте в `.env`:
```env
PROCTOR_REDIS_URL=redis://localhost:6379/0
```

### Шаг 3: Перезапуск приложения

```bash
cd backend
python -m uvicorn app.main:app --reload
```

В логах должно появиться:
```
INFO - Successfully connected to Redis at redis://localhost:6379/0
INFO - Redis storage enabled for session persistence
```

### Шаг 4: Проверка

```bash
curl http://localhost:8000/health
```

Ответ должен содержать:
```json
{
  "redis_status": "connected"
}
```

## Заключение

Интеграция с Redis обеспечивает:
- ✅ Распределённое хранение сессий
- ✅ Масштабируемость на несколько серверов
- ✅ Сохранение данных при рестарте
- ✅ Автоматическую очистку устаревших данных
- ✅ Fallback режим для разработки

Для вопросов и проблем обращайтесь к документации или открывайте issue в репозитории.
