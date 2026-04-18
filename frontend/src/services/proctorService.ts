import { useRef } from 'react';
import { useCamera } from '../hooks/useCamera';
import { useScreenCapture } from '../hooks/useScreenCapture';
import { useProctorWebSocket } from '../hooks/useProctorWebSocket';
import { Violation } from '../types';

interface ProctorSessionProps {
  userId: string;
  examId: string;
  onSessionStart?: (sessionId: string) => void;
  onSessionEnd?: (violations: Violation[]) => void;
  onViolation?: (violation: Violation) => void;
}

export function ProctorSession({
  userId,
  examId,
  onSessionStart,
  onSessionEnd,
  onViolation
}: ProctorSessionProps) {
  const videoRef = useRef<HTMLVideoElement>(null);
  const sessionIdRef = useRef<string | null>(null);

  // Обработка нарушений
  const handleViolation = (violation: Violation) => {
    console.warn('Violation detected:', violation);
    onViolation?.(violation);
    
    // Показываем предупреждение пользователю
    if (violation.confidence > 0.7) {
      alert(`Предупреждение: ${violation.description}`);
    }
  };

  // WebSocket хук
  const {
    isConnected,
    isStreaming,
    violations,
    startStreaming,
    stopStreaming,
    sendVideoFrame,
    sendScreenCapture
  } = useProctorWebSocket({
    sessionId: sessionIdRef.current,
    onViolation: handleViolation,
    onError: (error) => console.error('WS Error:', error)
  });

  // Камера хук
  const {
    isCameraOn,
    hasPermission: hasCameraPermission,
    error: cameraError,
    startCamera,
    stopCamera
  } = useCamera({
    videoRef,
    onFrame: sendVideoFrame,
    frameRate: 2
  });

  // Захват экрана хук
  const {
    isSharing,
    hasPermission: hasScreenPermission,
    error: screenError,
    startSharing,
    stopSharing,
    isFullscreen
  } = useScreenCapture({
    onCapture: sendScreenCapture,
    captureRate: 1
  });

  // Начало сессии
  const startSession = async () => {
    try {
      // Создаём сессию на сервере
      const response = await fetch('/api/v1/sessions/start', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ user_id: userId, exam_id: examId })
      });

      if (!response.ok) throw new Error('Failed to start session');
      
      const session = await response.json();
      sessionIdRef.current = session.session_id;
      
      // Запускаем камеру и захват экрана
      await startCamera();
      await startSharing();
      
      // Запрашиваем полный экран
      await document.documentElement.requestFullscreen().catch(console.warn);
      
      // Запускаем стриминг
      startStreaming();
      
      onSessionStart?.(session.session_id);
    } catch (error) {
      console.error('Failed to start session:', error);
    }
  };

  // Завершение сессии
  const endSession = async () => {
    try {
      stopStreaming();
      stopCamera();
      stopSharing();
      
      // Выход из полноэкранного режима
      if (document.fullscreenElement) {
        await document.exitFullscreen();
      }

      // Завершаем сессию на сервере
      if (sessionIdRef.current) {
        await fetch(`/api/v1/sessions/${sessionIdRef.current}/end`, {
          method: 'POST'
        });
      }

      onSessionEnd?.(violations);
    } catch (error) {
      console.error('Failed to end session:', error);
    }
  };

  return {
    videoRef,
    sessionId: sessionIdRef.current,
    isConnected,
    isStreaming,
    isCameraOn,
    isSharing,
    isFullscreen,
    hasCameraPermission,
    hasScreenPermission,
    cameraError,
    screenError,
    violations,
    startSession,
    endSession
  };
}
