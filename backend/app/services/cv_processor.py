"""
Computer Vision Module for Advanced Proctoring
Handles face detection, gaze tracking, and object detection using OpenCV/MediaPipe.
Designed for production performance with threading.
"""
import cv2
import numpy as np
import mediapipe as mp
from typing import Dict, List, Optional, Tuple
import time
from .behavior_analyzer import Event, SeverityLevel

class CVProcessor:
    """
    High-performance Computer Vision processor using MediaPipe.
    Detects faces, landmarks, gaze, and objects (phones).
    """
    
    def __init__(self):
        # Initialize MediaPipe Face Mesh
        self.mp_face_mesh = mp.solutions.face_mesh
        self.face_mesh = self.mp_face_mesh.FaceMesh(
            static_image_mode=False,
            max_num_faces=2,
            refine_landmarks=True,
            min_detection_confidence=0.5,
            min_tracking_confidence=0.5
        )
        
        # Initialize Face Detection for quick checks
        self.mp_face_detection = mp.solutions.face_detection
        self.face_detection = self.mp_face_detection.FaceDetection(
            model_selection=1, # Model 1 for short range
            min_detection_confidence=0.5
        )
        
        # Landmark indices for gaze estimation
        self.LEFT_EYE_INDICES = [33, 133, 160, 159, 158, 157, 173]
        self.RIGHT_EYE_INDICES = [362, 263, 385, 386, 387, 388, 466]
        self.NOSE_TIP = 1
        self.MOUTH_CENTER = 13
        
        # State
        self.last_phone_detected_time = 0
        self.phone_cooldown = 2.0 # Seconds to avoid spamming phone events

    def process_frame(self, frame: np.ndarray) -> List[Event]:
        """
        Process a single video frame and return detected events.
        Input: BGR image (from OpenCV)
        Output: List of Events
        """
        events = []
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        h, w, _ = frame.shape
        
        # 1. Face Detection & Count
        results_mesh = self.face_mesh.process(rgb_frame)
        
        if not results_mesh.multi_face_landmarks:
            # No face detected
            events.append(Event(
                timestamp=time.time(),
                event_type="face_lost",
                severity=SeverityLevel.MEDIUM,
                metadata={"reason": "no_face_detected"}
            ))
        else:
            face_count = len(results_mesh.multi_face_landmarks)
            
            # Multiple faces detection
            if face_count > 1:
                events.append(Event(
                    timestamp=time.time(),
                    event_type="multi_face",
                    severity=SeverityLevel.CRITICAL,
                    metadata={"count": face_count}
                ))
            else:
                # Single face logic
                events.append(Event(
                    timestamp=time.time(),
                    event_type="face_detected",
                    severity=SeverityLevel.LOW,
                    metadata={"count": 1}
                ))
                
                landmarks = results_mesh.multi_face_landmarks[0]
                
                # 2. Gaze & Head Pose Analysis
                gaze_event = self._analyze_gaze(landmarks, h, w)
                if gaze_event:
                    events.append(gaze_event)
                    
                head_event = self._analyze_head_pose(landmarks, h, w)
                if head_event:
                    events.append(head_event)

        # 3. Object Detection (Phone) - Simplified heuristic using color/shape
        # In production, use YOLO or SSD for better accuracy
        phone_event = self._detect_phone_heuristic(frame)
        if phone_event:
            events.append(phone_event)
            
        return events

    def _analyze_gaze(self, landmarks, h: int, w: int) -> Optional[Event]:
        """
        Analyze eye landmarks to determine if user is looking away.
        """
        # Get nose tip position (reference)
        nose = landmarks.landmark[self.NOSE_TIP]
        nose_x = nose.x * w
        
        # Get left and right eye centers roughly
        left_eye = landmarks.landmark[33] # Left corner of left eye
        right_eye = landmarks.landmark[362] # Right corner of right eye
        
        # Calculate eye centers relative to nose
        # This is a simplified vector calculation
        left_center_x = ((left_eye.x + landmarks.landmark[133].x) / 2) * w
        right_center_x = ((right_eye.x + landmarks.landmark[263].x) / 2) * w
        
        # If eyes are significantly offset from nose horizontally, user is looking sideways
        # Thresholds need calibration based on camera distance
        threshold = w * 0.15 
        
        looking_left = (left_center_x < nose_x - threshold) or (right_center_x < nose_x - threshold)
        looking_right = (left_center_x > nose_x + threshold) or (right_center_x > nose_x + threshold)
        
        # Check vertical gaze (looking down/up)
        nose_y = nose.y * h
        mouth_y = landmarks.landmark[self.MOUTH_CENTER].y * h
        # If distance between nose and mouth is small, head might be tilted down or looking down
        vertical_dist = abs(nose_y - mouth_y)
        looking_down = vertical_dist < (h * 0.1) # Heuristic
        
        if looking_left or looking_right:
            return Event(
                timestamp=time.time(),
                event_type="gaze_avoided",
                severity=SeverityLevel.MEDIUM,
                metadata={"direction": "horizontal"}
            )
        elif looking_down:
            return Event(
                timestamp=time.time(),
                event_type="gaze_down",
                severity=SeverityLevel.LOW,
                metadata={"direction": "vertical"}
            )
            
        return None

    def _analyze_head_pose(self, landmarks, h: int, w: int) -> Optional[Event]:
        """
        Estimate head rotation based on landmark asymmetry.
        """
        # Simple heuristic: Compare x-coordinates of symmetric points
        # Left ear: 234, Right ear: 454
        left_ear = landmarks.landmark[234].x
        right_ear = landmarks.landmark[454].x
        
        # If one ear is significantly more visible/closer to center than the other
        diff = abs(left_ear - right_ear)
        
        # Threshold for "turned head"
        if diff > 0.2: # 20% width difference
             return Event(
                timestamp=time.time(),
                event_type="head_turned",
                severity=SeverityLevel.MEDIUM,
                metadata={"asymmetry": diff}
            )
        return None

    def _detect_phone_heuristic(self, frame: np.ndarray) -> Optional[Event]:
        """
        Heuristic phone detection based on rectangular shapes and skin tone.
        NOTE: For production, replace with a trained YOLOv8-Nano model.
        """
        now = time.time()
        if now - self.last_phone_detected_time < self.phone_cooldown:
            return None
            
        # Convert to HSV for color segmentation
        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
        
        # Skin tone range (very approximate)
        lower_skin = np.array([0, 48, 0])
        upper_skin = np.array([20, 255, 255])
        mask = cv2.inRange(hsv, lower_skin, upper_skin)
        
        # Find contours
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        phone_like_found = False
        for cnt in contours:
            area = cv2.contourArea(cnt)
            if 5000 < area < 50000: # Filter by size
                x, y, w, h = cv2.boundingRect(cnt)
                aspect_ratio = float(w)/h
                # Phones are usually rectangular with aspect ratio ~0.5-0.6 or 1.5-2.0
                if 0.4 < aspect_ratio < 0.7 or 1.4 < aspect_ratio < 2.2:
                    # Check if it's near hands/face area (bottom part of frame usually)
                    if y > frame.shape[0] * 0.3: 
                        phone_like_found = True
                        break
        
        if phone_like_found:
            self.last_phone_detected_time = now
            return Event(
                timestamp=time.time(),
                event_type="phone_detected",
                severity=SeverityLevel.HIGH,
                metadata={"method": "heuristic_contour"}
            )
        return None

    def release(self):
        self.face_mesh.close()
        self.face_detection.close()
