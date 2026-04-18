from fastapi import APIRouter, WebSocket, WebSocketDisconnect, HTTPException, Depends
from typing import Dict, Optional
import asyncio
import json
import base64
from datetime import datetime
import uuid

from app.models.schemas import (
    ProctorSession, SessionStatus, Violation,
    StartSessionRequest, EndSessionResponse, AnalysisResult
)
from app.detectors.face_detector import FaceMeshDetector, decode_frame_from_base64
from app.detectors.screen_detector import ScreenAnalyzer
from config import settings


router = APIRouter()

# Хранилище активных сессий
active_sessions: Dict[str, ProctorSession] = {}

# Детекторы (singleton на процесс)
face_detector: Optional[FaceMeshDetector] = None
screen_analyzer: Optional[ScreenAnalyzer] = None


def get_face_detector() -> FaceMeshDetector:
    global face_detector
    if face_detector is None:
        face_detector = FaceMeshDetector()
    return face_detector


def get_screen_analyzer() -> ScreenAnalyzer:
    global screen_analyzer
    if screen_analyzer is None:
        screen_analyzer = ScreenAnalyzer()
    return screen_analyzer


@router.post("/sessions/start")
async def start_session(request: StartSessionRequest) -> ProctorSession:
    """Начало новой сессии прокторинга"""
    session_id = str(uuid.uuid4())
    
    session = ProctorSession(
        session_id=session_id,
        user_id=request.user_id,
        exam_id=request.exam_id,
        status=SessionStatus.PENDING,
        violations=[]
    )
    
    active_sessions[session_id] = session
    
    return session


@router.get("/sessions/{session_id}")
async def get_session(session_id: str) -> ProctorSession:
    """Получение информации о сессии"""
    if session_id not in active_sessions:
        raise HTTPException(status_code=404, detail="Сессия не найдена")
    
    return active_sessions[session_id]


@router.post("/sessions/{session_id}/end")
async def end_session(session_id: str) -> EndSessionResponse:
    """Завершение сессии"""
    if session_id not in active_sessions:
        raise HTTPException(status_code=404, detail="Сессия не найдена")
    
    session = active_sessions[session_id]
    session.status = SessionStatus.COMPLETED
    session.ended_at = datetime.utcnow()
    
    # Подсчёт нарушений по типам
    violations_by_type = {}
    for violation in session.violations:
        vtype = violation.type.value
        violations_by_type[vtype] = violations_by_type.get(vtype, 0) + 1
    
    duration = (session.ended_at - session.started_at).total_seconds() if session.started_at else 0
    
    response = EndSessionResponse(
        session_id=session_id,
        status=session.status,
        total_violations=len(session.violations),
        violations_by_type=violations_by_type,
        duration_seconds=duration
    )
    
    # Удаляем сессию из активных (или перемещаем в архив)
    del active_sessions[session_id]
    
    return response


@router.websocket("/ws/{session_id}")
async def websocket_endpoint(websocket: WebSocket, session_id: str):
    """
    WebSocket соединение для потоковой передачи видео и скринкаста
    
    Клиент отправляет:
    - Видеокадры с камеры (base64)
    - Скриншоты экрана (base64)
    - Метаданные (активное окно, fullscreen статус)
    
    Сервер возвращает:
    - Результаты анализа в реальном времени
    - Предупреждения о нарушениях
    """
    await websocket.accept()
    
    if session_id not in active_sessions:
        await websocket.close(code=4004, reason="Сессия не найдена")
        return
    
    session = active_sessions[session_id]
    
    # Обновляем статус сессии
    session.status = SessionStatus.ACTIVE
    if not session.started_at:
        session.started_at = datetime.utcnow()
    
    face_det = get_face_detector()
    screen_an = get_screen_analyzer()
    
    try:
        while True:
            # Получаем данные от клиента
            message = await websocket.receive_text()
            data = json.loads(message)
            
            msg_type = data.get("type")
            
            if msg_type == "video_frame":
                # Анализ видео с камеры
                frame_data = data.get("frame")
                if frame_data:
                    # Декодируем кадр
                    frame = decode_frame_from_base64(frame_data)
                    
                    # Анализируем кадр
                    result = face_det.analyze_frame(frame)
                    
                    # Добавляем нарушения в сессию
                    for violation in result["violations"]:
                        session.violations.append(violation)
                    
                    # Отправляем результат клиенту
                    await websocket.send_json({
                        "type": "video_analysis",
                        "violations": [v.dict() for v in result["violations"]],
                        "metadata": result["metadata"]
                    })
            
            elif msg_type == "screen_capture":
                # Анализ скриншота
                image_data = data.get("image")
                active_window = data.get("active_window")
                is_fullscreen = data.get("is_fullscreen", True)
                
                if image_data:
                    result = screen_an.analyze_screen(
                        image_data=image_data,
                        active_window=active_window,
                        is_fullscreen=is_fullscreen
                    )
                    
                    # Добавляем нарушения в сессию
                    for violation in result["violations"]:
                        session.violations.append(violation)
                    
                    # Отправляем результат клиенту
                    await websocket.send_json({
                        "type": "screen_analysis",
                        "violations": [v.dict() for v in result["violations"]],
                        "metadata": result["metadata"]
                    })
            
            elif msg_type == "heartbeat":
                # Ответ на heartbeat
                await websocket.send_json({
                    "type": "heartbeat",
                    "timestamp": datetime.utcnow().isoformat(),
                    "session_status": session.status.value
                })
            
            elif msg_type == "violation_warning":
                # Клиент получил предупреждение о нарушении
                violation_id = data.get("violation_id")
                # Логирование или дополнительная обработка
                
    except WebSocketDisconnect:
        # Клиент отключился
        session.status = SessionStatus.COMPLETED
        session.ended_at = datetime.utcnow()
        
    except Exception as e:
        # Обработка ошибок
        await websocket.send_json({
            "type": "error",
            "message": str(e)
        })
        session.status = SessionStatus.VIOLATED


@router.get("/sessions/{session_id}/violations")
async def get_session_violations(session_id: str):
    """Получение списка нарушений сессии"""
    if session_id not in active_sessions:
        # Попробуем найти в завершенных (в реальной системе - в БД)
        raise HTTPException(status_code=404, detail="Сессия не найдена")
    
    session = active_sessions[session_id]
    return {
        "session_id": session_id,
        "violations": [v.dict() for v in session.violations],
        "total_count": len(session.violations)
    }


@router.on_event("shutdown")
async def shutdown_event():
    """Очистка ресурсов при завершении работы"""
    global face_detector, screen_analyzer
    if face_detector:
        face_detector.close()
    if screen_analyzer:
        screen_analyzer.reset()
