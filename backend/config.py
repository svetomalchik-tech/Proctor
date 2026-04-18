from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Настройки приложения"""
    
    # Сервер
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    
    # WebSocket
    WS_HEARTBEAT_INTERVAL: int = 30
    
    # Детекция нарушений - видео с камеры
    EYE_AWAY_THRESHOLD_SEC: float = 3.0  # Порог отведения глаз (сек)
    HEAD_TURN_THRESHOLD_DEG: float = 30.0  # Порог поворота головы (градусы)
    PHONE_DETECTION_CONFIDENCE: float = 0.7  # Порог детекции телефона
    MULTI_FACE_DETECTION: bool = True  # Детекция нескольких лиц
    
    # Детекция нарушений - скринкаст
    TAB_SWITCH_DETECTION: bool = True  # Детекция переключения вкладок
    FULLSCREEN_REQUIRED: bool = True  # Требование полноэкранного режима
    ALLOWED_APPS: list[str] = []  # Список разрешённых приложений
    
    # Хранение данных
    STORAGE_PATH: str = "./storage"
    VIDEO_RECORDING: bool = False  # Запись видео сессии
    
    class Config:
        env_file = ".env"


settings = Settings()
