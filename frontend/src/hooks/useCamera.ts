import { useState, useEffect, useRef, useCallback } from 'react';

interface UseCameraOptions {
  videoRef: React.RefObject<HTMLVideoElement>;
  onFrame?: (frameData: string) => void;
  frameRate?: number;
}

interface UseCameraReturn {
  isCameraOn: boolean;
  hasPermission: boolean;
  error: string | null;
  startCamera: () => Promise<void>;
  stopCamera: () => void;
  captureFrame: () => string | null;
}

export function useCamera({
  videoRef,
  onFrame,
  frameRate = 2
}: UseCameraOptions): UseCameraReturn {
  const [isCameraOn, setIsCameraOn] = useState(false);
  const [hasPermission, setHasPermission] = useState(false);
  const [error, setError] = useState<string | null>(null);
  
  const streamRef = useRef<MediaStream | null>(null);
  const frameIntervalRef = useRef<NodeJS.Timeout | null>(null);
  const canvasRef = useRef<HTMLCanvasElement | null>(null);

  const captureFrame = useCallback((): string | null => {
    if (!videoRef.current || !isCameraOn) return null;

    const video = videoRef.current;
    
    if (!canvasRef.current) {
      canvasRef.current = document.createElement('canvas');
    }
    
    const canvas = canvasRef.current;
    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;
    
    const ctx = canvas.getContext('2d');
    if (!ctx) return null;
    
    ctx.drawImage(video, 0, 0, canvas.width, canvas.height);
    return canvas.toDataURL('image/jpeg', 0.8);
  }, [videoRef, isCameraOn]);

  const startCamera = async () => {
    try {
      setError(null);
      
      const stream = await navigator.mediaDevices.getUserMedia({
        video: {
          width: { ideal: 1280 },
          height: { ideal: 720 },
          facingMode: 'user'
        },
        audio: false
      });

      if (videoRef.current) {
        videoRef.current.srcObject = stream;
        await new Promise((resolve) => {
          videoRef.current!.onloadedmetadata = resolve;
        });
      }

      streamRef.current = stream;
      setIsCameraOn(true);
      setHasPermission(true);

      // Запускаем периодическую отправку кадров
      if (onFrame) {
        frameIntervalRef.current = setInterval(() => {
          const frameData = captureFrame();
          if (frameData) {
            onFrame(frameData);
          }
        }, 1000 / frameRate);
      }
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to access camera';
      setError(errorMessage);
      setHasPermission(false);
      console.error('Camera error:', err);
    }
  };

  const stopCamera = useCallback(() => {
    if (frameIntervalRef.current) {
      clearInterval(frameIntervalRef.current);
      frameIntervalRef.current = null;
    }

    if (streamRef.current) {
      streamRef.current.getTracks().forEach(track => track.stop());
      streamRef.current = null;
    }

    if (videoRef.current) {
      videoRef.current.srcObject = null;
    }

    setIsCameraOn(false);
  }, [videoRef]);

  useEffect(() => {
    return () => {
      stopCamera();
    };
  }, [stopCamera]);

  return {
    isCameraOn,
    hasPermission,
    error,
    startCamera,
    stopCamera,
    captureFrame
  };
}
