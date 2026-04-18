import re
from typing import Optional, Dict, Any, List
from datetime import datetime

from app.models.schemas import Violation, ViolationType
from config import settings


class ScreenAnalyzer:
    """Анализатор захвата экрана для детекции нарушений"""
    
    # Паттерны для детекции мессенджеров и запрещённых приложений
    MESSENGER_PATTERNS = [
        r'telegram', r'whatsapp', r'skype', r'slack', r'discord',
        r'viber', r'wechat', r'signal', r'threema', r'messenger'
    ]
    
    BROWSER_PATTERNS = [
        r'chrome', r'firefox', r'safari', r'edge', r'opera', r'brave'
    ]
    
    def __init__(self):
        self.last_active_window: Optional[str] = None
        self.last_tab_detected: Optional[str] = None
        self.fullscreen_violations: int = 0
        
    def analyze_screen(self, 
                       image_data: str,
                       active_window: Optional[str] = None,
                       is_fullscreen: bool = True) -> Dict[str, Any]:
        """
        Анализ скриншота и активности окон
        
        Args:
            image_data: Base64 изображение скриншота
            active_window: Название активного окна/приложения
            is_fullscreen: Флаг полноэкранного режима
            
        Returns:
            Словарь с результатами анализа и нарушениями
        """
        violations = []
        metadata = {
            "active_window": active_window,
            "is_fullscreen": is_fullscreen,
            "messenger_detected": False,
            "tab_switched": False
        }
        
        # Проверка полноэкранного режима
        if not is_fullscreen and settings.FULLSCREEN_REQUIRED:
            violations.append(Violation(
                type=ViolationType.EXIT_FULLSCREEN,
                confidence=1.0,
                description="Пользователь вышел из полноэкранного режима"
            ))
            self.fullscreen_violations += 1
        
        # Проверка активного окна/приложения
        if active_window:
            # Детекция переключения вкладок/приложений
            if self.last_active_window and active_window != self.last_active_window:
                if settings.TAB_SWITCH_DETECTION:
                    # Проверка на браузер - переключение вкладок
                    if self._is_browser_window(active_window):
                        violations.append(Violation(
                            type=ViolationType.TAB_SWITCH,
                            confidence=0.7,
                            description=f"Переключение вкладки браузера: {active_window}"
                        ))
                        metadata["tab_switched"] = True
                    else:
                        # Переключение на другое приложение
                        violations.append(Violation(
                            type=ViolationType.APP_CHANGE,
                            confidence=0.8,
                            description=f"Переключение на другое приложение: {active_window}"
                        ))
            
            # Детекция мессенджеров
            if self._is_messenger(active_window):
                violations.append(Violation(
                    type=ViolationType.MESSENGER_USAGE,
                    confidence=0.9,
                    description=f"Обнаружен мессенджер: {active_window}"
                ))
                metadata["messenger_detected"] = True
            
            # Проверка на разрешённые приложения
            if settings.ALLOWED_APPS and not self._is_allowed_app(active_window):
                violations.append(Violation(
                    type=ViolationType.APP_CHANGE,
                    confidence=0.75,
                    description=f"Использование неразрешённого приложения: {active_window}"
                ))
            
            self.last_active_window = active_window
        
        # Анализ изображения (OCR для детекции текста)
        # В полной версии здесь будет OCR анализ содержимого экрана
        ocr_violations = self._analyze_screen_content(image_data)
        violations.extend(ocr_violations)
        
        return {"violations": violations, "metadata": metadata}
    
    def _is_browser_window(self, window_name: str) -> bool:
        """Проверка является ли окно браузером"""
        window_lower = window_name.lower()
        return any(re.search(pattern, window_lower) for pattern in self.BROWSER_PATTERNS)
    
    def _is_messenger(self, window_name: str) -> bool:
        """Проверка является ли окно мессенджером"""
        window_lower = window_name.lower()
        return any(re.search(pattern, window_lower) for pattern in self.MESSENGER_PATTERNS)
    
    def _is_allowed_app(self, window_name: str) -> bool:
        """Проверка входит ли приложение в список разрешённых"""
        window_lower = window_name.lower()
        return any(allowed.lower() in window_lower for allowed in settings.ALLOWED_APPS)
    
    def _analyze_screen_content(self, image_data: str) -> List[Violation]:
        """
        Анализ содержимого экрана через OCR
        В полной версии используется Tesseract или аналогичный OCR движок
        """
        # Заглушка для будущей реализации OCR
        # Здесь можно детектировать:
        # - Поисковые запросы
        # - Текст с ответами на вопросы
        # - Запрещённые материалы
        
        violations = []
        
        # Пример: если бы мы распознали текст с поисковым запросом
        # if self._contains_search_query(text):
        #     violations.append(Violation(...))
        
        return violations
    
    def reset(self):
        """Сброс состояния анализатора"""
        self.last_active_window = None
        self.last_tab_detected = None
        self.fullscreen_violations = 0
