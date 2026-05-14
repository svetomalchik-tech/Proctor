from pydantic_settings import BaseSettings
from typing import List, Optional
import secrets


class Settings(BaseSettings):
    """Настройки приложения"""
    
    # Сервер
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    
    # Безопасность
    SECRET_KEY: str = secrets.token_urlsafe(32)  # Генерация случайного ключа
    ALLOWED_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://localhost:8080",
        "https://yourdomain.com"
    ]
    CORS_ALLOW_CREDENTIALS: bool = True
    
    # Rate Limiting
    RATE_LIMIT_PER_MINUTE: int = 60
    RATE_LIMIT_ENABLED: bool = True
    
    # WebSocket
    WS_HEARTBEAT_INTERVAL: int = 30
    WS_MAX_MESSAGE_SIZE: int = 10 * 1024 * 1024  # 10MB
    
    # Детекция нарушений - видео с камеры
    EYE_AWAY_THRESHOLD_SEC: float = 3.0  # Порог отведения глаз (сек)
    HEAD_TURN_THRESHOLD_DEG: float = 30.0  # Порог поворота головы (градусы)
    PHONE_DETECTION_CONFIDENCE: float = 0.7  # Порог детекции телефона
    MULTI_FACE_DETECTION: bool = True  # Детекция нескольких лиц
    
    # Детекция нарушений - скринкаст
    TAB_SWITCH_DETECTION: bool = True  # Детекция переключения вкладок
    FULLSCREEN_REQUIRED: bool = True  # Требование полноэкранного режима
    ALLOWED_APPS: List[str] = []  # Список разрешённых приложений
    
    # Хранение данных
    STORAGE_PATH: str = "./storage"
    VIDEO_RECORDING: bool = False  # Запись видео сессии
    
    # Логирование
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    
    # Redis (для хранения сессий в production)
    REDIS_URL: Optional[str] = None  # "redis://localhost:6379/0"
    
    class Config:
        env_file = ".env"
        env_prefix = "PROCTOR_"


settings = Settings()
