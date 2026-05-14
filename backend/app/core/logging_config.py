"""
Logging Configuration Module
Centralized logging setup for the proctoring system.
"""
import logging
import sys
from pathlib import Path
import config

settings = config.Settings()


def setup_logging() -> logging.Logger:
    """
    Настройка логирования для всего приложения.
    
    Returns:
        Настроенный logger для корневого модуля
    """
    # Создаем директорию для логов
    log_dir = Path(settings.STORAGE_PATH) / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    
    # Конфигурация root logger
    logging.basicConfig(
        level=getattr(logging, settings.LOG_LEVEL.upper()),
        format=settings.LOG_FORMAT,
        handlers=[
            # Вывод в консоль
            logging.StreamHandler(sys.stdout),
            # Вывод в файл
            logging.FileHandler(log_dir / "app.log", encoding='utf-8'),
        ]
    )
    
    # Получаем logger для приложения
    logger = logging.getLogger("proctoring")
    logger.setLevel(getattr(logging, settings.LOG_LEVEL.upper()))
    
    # Подавляем излишне подробные логи от библиотек
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("mediapipe").setLevel(logging.WARNING)
    logging.getLogger("cv2").setLevel(logging.WARNING)
    
    logger.info("Logging initialized with level: %s", settings.LOG_LEVEL)
    
    return logger


def get_logger(name: str) -> logging.Logger:
    """
    Получить logger для конкретного модуля.
    
    Args:
        name: Имя модуля (обычно __name__)
        
    Returns:
        Logger instance
    """
    return logging.getLogger(f"proctoring.{name}")


# Глобальный logger для приложения
logger = setup_logging()
