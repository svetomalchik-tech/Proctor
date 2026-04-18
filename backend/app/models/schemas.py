from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from enum import Enum


class ViolationType(str, Enum):
    """Типы нарушений"""
    EYE_AWAY = "eye_away"  # Отведение глаз
    HEAD_TURN = "head_turn"  # Поворот головы
    PHONE_USAGE = "phone_usage"  # Использование телефона
    MULTI_FACE = "multi_face"  # Несколько лиц в кадре
    TAB_SWITCH = "tab_switch"  # Переключение вкладки
    APP_CHANGE = "app_change"  # Смена приложения
    EXIT_FULLSCREEN = "exit_fullscreen"  # Выход из полноэкранного режима
    MESSENGER_USAGE = "messenger_usage"  # Использование мессенджера


class Violation(BaseModel):
    """Модель нарушения"""
    type: ViolationType
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    confidence: float = Field(ge=0.0, le=1.0)
    description: str
    frame_data: Optional[str] = None  # Base64 кадр (опционально)


class SessionStatus(str, Enum):
    """Статусы сессии"""
    PENDING = "pending"
    ACTIVE = "active"
    PAUSED = "paused"
    COMPLETED = "completed"
    VIOLATED = "violated"


class ProctorSession(BaseModel):
    """Модель сессии прокторинга"""
    session_id: str
    user_id: str
    exam_id: str
    status: SessionStatus = SessionStatus.PENDING
    started_at: Optional[datetime] = None
    ended_at: Optional[datetime] = None
    violations: List[Violation] = []
    violation_count: int = 0
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat() if v else None
        }


class VideoFrame(BaseModel):
    """Модель видеокадра с камеры"""
    session_id: str
    frame_data: str  # Base64 изображение
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    width: int
    height: int


class ScreenCapture(BaseModel):
    """Модель захвата экрана"""
    session_id: str
    image_data: str  # Base64 изображение
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    active_window: Optional[str] = None
    is_fullscreen: bool = True


class AnalysisResult(BaseModel):
    """Результат анализа кадра/скриншота"""
    session_id: str
    violations: List[Violation] = []
    metadata: dict = {}


class StartSessionRequest(BaseModel):
    """Запрос на начало сессии"""
    user_id: str
    exam_id: str
    settings: Optional[dict] = None


class EndSessionResponse(BaseModel):
    """Ответ по завершении сессии"""
    session_id: str
    status: SessionStatus
    total_violations: int
    violations_by_type: dict
    duration_seconds: float
