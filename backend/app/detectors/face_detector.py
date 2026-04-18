import cv2
import mediapipe as mp
import numpy as np
from typing import Optional, Tuple, Dict, Any
from datetime import datetime
import base64

from app.models.schemas import Violation, ViolationType
from config import settings


class FaceMeshDetector:
    """Детектор лица и анализа поведения с использованием MediaPipe Face Mesh"""
    
    def __init__(self):
        self.mp_face_mesh = mp.solutions.face_mesh
        self.mp_drawing = mp.solutions.drawing_utils
        self.mp_drawing_styles = mp.solutions.drawing_styles
        self.face_mesh = self.mp_face_mesh.FaceMesh(
            max_num_faces=2,
            refine_landmarks=True,
            min_detection_confidence=0.5,
            min_tracking_confidence=0.5
        )
        
        # Индексы ключевых точек для определения направления взгляда
        self.LEFT_EYE_INDICES = [33, 133, 160, 159, 158, 157, 173]
        self.RIGHT_EYE_INDICES = [362, 263, 385, 386, 387, 388, 466]
        self.NOSE_TIP = 1
        self.NOSE_BASE = 6
        
        # Состояние
        self.eye_away_start_time: Optional[datetime] = None
        self.last_head_pose: Optional[Tuple[float, float, float]] = None
        
    def analyze_frame(self, frame: np.ndarray) -> Dict[str, Any]:
        """
        Анализ кадра с камеры
        
        Args:
            frame: Кадр изображения (BGR формат)
            
        Returns:
            Словарь с результатами анализа и нарушениями
        """
        violations = []
        metadata = {
            "faces_detected": 0,
            "head_pose": None,
            "eye_direction": None,
            "phone_detected": False
        }
        
        # Конвертация в RGB для MediaPipe
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = self.face_mesh.process(rgb_frame)
        
        if not results.multi_face_landmarks:
            # Нет лиц в кадре - потенциальное нарушение
            if self.eye_away_start_time is None:
                self.eye_away_start_time = datetime.utcnow()
            else:
                elapsed = (datetime.utcnow() - self.eye_away_start_time).total_seconds()
                if elapsed > settings.EYE_AWAY_THRESHOLD_SEC:
                    violations.append(Violation(
                        type=ViolationType.EYE_AWAY,
                        confidence=1.0,
                        description=f"Лицо не обнаружено в течение {elapsed:.1f} сек"
                    ))
            return {"violations": violations, "metadata": metadata}
        
        # Лицо найдено - сбрасываем таймер
        self.eye_away_start_time = None
        metadata["faces_detected"] = len(results.multi_face_landmarks)
        
        # Детекция нескольких лиц
        if len(results.multi_face_landmarks) > 1 and settings.MULTI_FACE_DETECTION:
            violations.append(Violation(
                type=ViolationType.MULTI_FACE,
                confidence=0.9,
                description=f"Обнаружено {len(results.multi_face_landmarks)} лиц в кадре"
            ))
        
        # Анализ каждого лица
        for face_landmarks in results.multi_face_landmarks:
            # Определение позы головы
            head_pose = self._estimate_head_pose(face_landmarks, frame.shape)
            metadata["head_pose"] = head_pose
            
            if head_pose:
                # Проверка поворота головы
                yaw, pitch, roll = head_pose
                if abs(yaw) > settings.HEAD_TURN_THRESHOLD_DEG:
                    violations.append(Violation(
                        type=ViolationType.HEAD_TURN,
                        confidence=min(abs(yaw) / 90.0, 1.0),
                        description=f"Поворот головы: yaw={yaw:.1f}°, pitch={pitch:.1f}°, roll={roll:.1f}°"
                    ))
            
            # Определение направления взгляда
            eye_direction = self._estimate_eye_direction(face_landmarks)
            metadata["eye_direction"] = eye_direction
            
            # Детекция телефона (упрощённая)
            phone_detected = self._detect_phone_gesture(face_landmarks)
            metadata["phone_detected"] = phone_detected
            if phone_detected:
                violations.append(Violation(
                    type=ViolationType.PHONE_USAGE,
                    confidence=settings.PHONE_DETECTION_CONFIDENCE,
                    description="Обнаружено использование телефона"
                ))
        
        return {"violations": violations, "metadata": metadata}
    
    def _estimate_head_pose(self, landmarks, image_shape: Tuple) -> Optional[Tuple[float, float, float]]:
        """
        Оценка позы головы (yaw, pitch, roll)
        
        Returns:
            Кортеж углов (yaw, pitch, roll) в градусах
        """
        h, w = image_shape[:2]
        
        # Ключевые точки для оценки позы
        nose_tip = landmarks.landmark[self.NOSE_TIP]
        nose_base = landmarks.landmark[self.NOSE_BASE]
        left_eye_outer = landmarks.landmark[33]
        right_eye_outer = landmarks.landmark[362]
        chin = landmarks.landmark[152]
        
        # Векторы
        nose_vector = np.array([
            nose_tip.x - nose_base.x,
            nose_tip.y - nose_base.y,
            nose_tip.z - nose_base.z
        ])
        
        eye_vector = np.array([
            right_eye_outer.x - left_eye_outer.x,
            right_eye_outer.y - left_eye_outer.y,
            right_eye_outer.z - left_eye_outer.z
        ])
        
        # Вычисление углов (упрощённо)
        yaw = np.arctan2(nose_vector[0], nose_vector[2]) * 180 / np.pi
        pitch = np.arctan2(-nose_vector[1], np.sqrt(nose_vector[0]**2 + nose_vector[2]**2)) * 180 / np.pi
        roll = np.arctan2(eye_vector[1], eye_vector[0]) * 180 / np.pi
        
        return (yaw, pitch, roll)
    
    def _estimate_eye_direction(self, landmarks) -> Optional[str]:
        """
        Оценка направления взгляда
        
        Returns:
            Строка с направлением: 'center', 'left', 'right', 'up', 'down'
        """
        left_eye_center = np.mean([
            landmarks.landmark[i] for i in self.LEFT_EYE_INDICES
        ], axis=0)
        right_eye_center = np.mean([
            landmarks.landmark[i] for i in self.RIGHT_EYE_INDICES
        ], axis=0)
        
        nose_tip = landmarks.landmark[self.NOSE_TIP]
        
        # Позиция зрачков относительно носа
        left_x_rel = left_eye_center.x - nose_tip.x
        right_x_rel = right_eye_center.x - nose_tip.x
        
        avg_x = (left_x_rel + right_x_rel) / 2
        
        if abs(avg_x) < 0.02:
            return "center"
        elif avg_x < -0.02:
            return "left"
        else:
            return "right"
    
    def _detect_phone_gesture(self, landmarks) -> bool:
        """
        Детекция жеста использования телефона (рука у уха)
        Упрощённая реализация
        """
        # В полной версии нужно использовать детектор рук
        # Здесь заглушка для демонстрации
        return False
    
    def close(self):
        """Освобождение ресурсов"""
        self.face_mesh.close()


def encode_frame_to_base64(frame: np.ndarray) -> str:
    """Кодирование кадра в Base64"""
    _, buffer = cv2.imencode('.jpg', frame)
    return base64.b64encode(buffer).decode('utf-8')


def decode_frame_from_base64(base64_string: str) -> np.ndarray:
    """Декодирование кадра из Base64"""
    img_bytes = base64.b64decode(base64_string)
    return cv2.imdecode(np.frombuffer(img_bytes, dtype=np.uint8), cv2.IMREAD_COLOR)
