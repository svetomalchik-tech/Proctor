import { useState, useEffect, useCallback, useRef } from 'react';
import { WSMessage, WSResponse, Violation } from '../types';

interface UseProctorWebSocketOptions {
  sessionId: string | null;
  onViolation?: (violation: Violation) => void;
  onError?: (error: string) => void;
  onStatusChange?: (status: string) => void;
}

interface UseProctorWebSocketReturn {
  isConnected: boolean;
  isStreaming: boolean;
  violations: Violation[];
  startStreaming: () => void;
  stopStreaming: () => void;
  sendVideoFrame: (frameData: string) => void;
  sendScreenCapture: (imageData: string, activeWindow?: string, isFullscreen?: boolean) => void;
}

export function useProctorWebSocket({
  sessionId,
  onViolation,
  onError,
  onStatusChange
}: UseProctorWebSocketOptions): UseProctorWebSocketReturn {
  const [isConnected, setIsConnected] = useState(false);
  const [isStreaming, setIsStreaming] = useState(false);
  const [violations, setViolations] = useState<Violation[]>([]);
  
  const wsRef = useRef<WebSocket | null>(null);
  const heartbeatIntervalRef = useRef<NodeJS.Timeout | null>(null);

  const connect = useCallback(() => {
    if (!sessionId || wsRef.current) return;

    const wsUrl = `ws://localhost:8000/api/v1/ws/${sessionId}`;
    const ws = new WebSocket(wsUrl);

    ws.onopen = () => {
      console.log('WebSocket connected');
      setIsConnected(true);
      
      // Запускаем heartbeat
      heartbeatIntervalRef.current = setInterval(() => {
        if (ws.readyState === WebSocket.OPEN) {
          ws.send(JSON.stringify({ type: 'heartbeat' }));
        }
      }, 30000);
    };

    ws.onmessage = (event) => {
      const response: WSResponse = JSON.parse(event.data);
      
      switch (response.type) {
        case 'video_analysis':
        case 'screen_analysis':
          if (response.violations) {
            setViolations(prev => [...prev, ...response.violations]);
            response.violations.forEach(v => onViolation?.(v));
          }
          break;
          
        case 'heartbeat':
          if (response.session_status && onStatusChange) {
            onStatusChange(response.session_status);
          }
          break;
          
        case 'error':
          onError?.(response.message || 'Unknown error');
          break;
      }
    };

    ws.onclose = () => {
      console.log('WebSocket disconnected');
      setIsConnected(false);
      setIsStreaming(false);
      
      if (heartbeatIntervalRef.current) {
        clearInterval(heartbeatIntervalRef.current);
      }
    };

    ws.onerror = (error) => {
      console.error('WebSocket error:', error);
      onError?.('Connection error');
    };

    wsRef.current = ws;
  }, [sessionId, onViolation, onError, onStatusChange]);

  const disconnect = useCallback(() => {
    if (heartbeatIntervalRef.current) {
      clearInterval(heartbeatIntervalRef.current);
      heartbeatIntervalRef.current = null;
    }
    
    if (wsRef.current) {
      wsRef.current.close();
      wsRef.current = null;
    }
    
    setIsConnected(false);
    setIsStreaming(false);
  }, []);

  const startStreaming = useCallback(() => {
    if (!wsRef.current || !isConnected) {
      connect();
    }
    setIsStreaming(true);
  }, [isConnected, connect]);

  const stopStreaming = useCallback(() => {
    setIsStreaming(false);
  }, []);

  const sendVideoFrame = useCallback((frameData: string) => {
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN && isStreaming) {
      const message: WSMessage = {
        type: 'video_frame',
        frame: frameData
      };
      wsRef.current.send(JSON.stringify(message));
    }
  }, [isStreaming]);

  const sendScreenCapture = useCallback((
    imageData: string,
    activeWindow?: string,
    isFullscreen?: boolean
  ) => {
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN && isStreaming) {
      const message: WSMessage = {
        type: 'screen_capture',
        image: imageData,
        active_window: activeWindow,
        is_fullscreen: isFullscreen
      };
      wsRef.current.send(JSON.stringify(message));
    }
  }, [isStreaming]);

  useEffect(() => {
    if (sessionId) {
      connect();
    }
    
    return () => {
      disconnect();
    };
  }, [sessionId, connect, disconnect]);

  return {
    isConnected,
    isStreaming,
    violations,
    startStreaming,
    stopStreaming,
    sendVideoFrame,
    sendScreenCapture
  };
}
