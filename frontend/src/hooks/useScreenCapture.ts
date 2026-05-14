import { useState, useEffect, useCallback, useRef } from 'react';

interface UseScreenCaptureOptions {
  onCapture?: (imageData: string, activeWindow: string, isFullscreen: boolean) => void;
  captureRate?: number;
}

interface UseScreenCaptureReturn {
  isSharing: boolean;
  hasPermission: boolean;
  error: string | null;
  startSharing: () => Promise<void>;
  stopSharing: () => void;
  isFullscreen: boolean;
}

export function useScreenCapture({
  onCapture,
  captureRate = 1
}: UseScreenCaptureOptions): UseScreenCaptureReturn {
  const [isSharing, setIsSharing] = useState(false);
  const [hasPermission, setHasPermission] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [isFullscreen, setIsFullscreen] = useState(false);
  
  const streamRef = useRef<MediaStream | null>(null);
  const captureIntervalRef = useRef<NodeJS.Timeout | null>(null);
  const videoElementRef = useRef<HTMLVideoElement | null>(null);
  const canvasRef = useRef<HTMLCanvasElement | null>(null);

  // Отслеживание полноэкранного режима
  useEffect(() => {
    const handleFullscreenChange = () => {
      setIsFullscreen(!!document.fullscreenElement);
    };

    document.addEventListener('fullscreenchange', handleFullscreenChange);
    return () => {
      document.removeEventListener('fullscreenchange', handleFullscreenChange);
    };
  }, []);

  // Отслеживание потери фокуса окна
  useEffect(() => {
    const handleVisibilityChange = () => {
      if (document.hidden && isSharing) {
        // Пользователь переключился на другую вкладку
        console.warn('User switched to another tab');
      }
    };

    document.addEventListener('visibilitychange', handleVisibilityChange);
    return () => {
      document.removeEventListener('visibilitychange', handleVisibilityChange);
    };
  }, [isSharing]);

  const captureFrame = useCallback(() => {
    if (!videoElementRef.current) return;

    const video = videoElementRef.current;
    
    if (!canvasRef.current) {
      canvasRef.current = document.createElement('canvas');
    }
    
    const canvas = canvasRef.current;
    canvas.width = video.videoWidth || window.screen.width;
    canvas.height = video.videoHeight || window.screen.height;
    
    const ctx = canvas.getContext('2d');
    if (!ctx) return;
    
    ctx.drawImage(video, 0, 0, canvas.width, canvas.height);
    const imageData = canvas.toDataURL('image/jpeg', 0.85);
    
    // Определяем активное окно (упрощённо - название вкладки)
    const activeWindow = document.title;
    
    if (onCapture) {
      onCapture(imageData, activeWindow, isFullscreen);
    }
  }, [onCapture, isFullscreen]);

  const startSharing = async () => {
    try {
      setError(null);
      
      // Запрашиваем доступ к захвату экрана
      const stream = await navigator.mediaDevices.getDisplayMedia({
        video: {
          width: { ideal: 1920 },
          height: { ideal: 1080 },
          frameRate: { ideal: 5 }
        },
        audio: false
      });

      // Создаём скрытый видеоэлемент для обработки потока
      if (!videoElementRef.current) {
        videoElementRef.current = document.createElement('video');
      }
      
      const video = videoElementRef.current;
      video.srcObject = stream;
      video.muted = true;
      video.playsInline = true;
      
      await new Promise((resolve) => {
        video.onloadedmetadata = () => {
          video.play().then(resolve).catch(console.error);
        };
      });

      streamRef.current = stream;
      setIsSharing(true);
      setHasPermission(true);

      // Обработка остановки шеринга пользователем
      stream.getVideoTracks()[0].addEventListener('ended', () => {
        stopSharing();
      });

      // Запускаем периодический захват кадров
      if (onCapture) {
        captureIntervalRef.current = setInterval(() => {
          captureFrame();
        }, 1000 / captureRate);
      }
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to share screen';
      setError(errorMessage);
      setHasPermission(false);
      console.error('Screen share error:', err);
    }
  };

  const stopSharing = useCallback(() => {
    if (captureIntervalRef.current) {
      clearInterval(captureIntervalRef.current);
      captureIntervalRef.current = null;
    }

    if (streamRef.current) {
      streamRef.current.getTracks().forEach(track => track.stop());
      streamRef.current = null;
    }

    if (videoElementRef.current) {
      videoElementRef.current.srcObject = null;
    }

    setIsSharing(false);
  }, []);

  useEffect(() => {
    return () => {
      stopSharing();
    };
  }, [stopSharing]);

  return {
    isSharing,
    hasPermission,
    error,
    startSharing,
    stopSharing,
    isFullscreen
  };
}
