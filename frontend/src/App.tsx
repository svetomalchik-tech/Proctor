import { useState, useRef } from 'react';
import { ProctorSession } from './services/proctorService';
import { Violation } from './types';
import './App.css';

function App() {
  const [userId] = useState('user-123');
  const [examId] = useState('exam-456');
  const [sessionActive, setSessionActive] = useState(false);
  const [violations, setViolations] = useState<Violation[]>([]);

  const videoRef = useRef<HTMLVideoElement>(null);

  const {
    sessionId,
    isConnected,
    isStreaming,
    isCameraOn,
    isSharing,
    isFullscreen,
    cameraError,
    screenError,
    startSession,
    endSession
  } = ProctorSession({
    userId,
    examId,
    onSessionStart: (id) => {
      console.log('Session started:', id);
      setSessionActive(true);
    },
    onSessionEnd: (v) => {
      console.log('Session ended. Violations:', v.length);
      setSessionActive(false);
      setViolations(v);
    },
    onViolation: (v) => {
      setViolations(prev => [...prev, v]);
    }
  });

  return (
    <div className="App">
      <header className="App-header">
        <h1>Система прокторинга</h1>
        <p>Корпоративное обучение</p>
      </header>

      <main className="App-main">
        {!sessionActive ? (
          <div className="start-screen">
            <h2>Готовы начать экзамен?</h2>
            <p>Для начала тестирования необходимо:</p>
            <ul>
              <li>Разрешить доступ к камере</li>
              <li>Разрешить захват экрана</li>
              <li>Включить полноэкранный режим</li>
            </ul>
            
            {cameraError && (
              <div className="error">Ошибка камеры: {cameraError}</div>
            )}
            {screenError && (
              <div className="error">Ошибка экрана: {screenError}</div>
            )}

            <button 
              className="start-button"
              onClick={startSession}
              disabled={isStreaming}
            >
              {isStreaming ? 'Запуск...' : 'Начать тестирование'}
            </button>
          </div>
        ) : (
          <div className="proctor-screen">
            <div className="status-bar">
              <span className={`status ${isConnected ? 'connected' : 'disconnected'}`}>
                {isConnected ? 'Подключено' : 'Отключено'}
              </span>
              <span className={`status ${isFullscreen ? 'fullscreen' : ''}`}>
                {isFullscreen ? 'Полный экран' : 'Не полный экран'}
              </span>
              <span>Нарушений: {violations.length}</span>
            </div>

            <div className="video-container">
              <video 
                ref={videoRef}
                autoPlay 
                playsInline
                muted
                className="camera-feed"
              />
              <div className="video-label">Ваша камера</div>
            </div>

            <div className="violations-log">
              <h3>Журнал нарушений</h3>
              {violations.length === 0 ? (
                <p>Нарушений не зафиксировано</p>
              ) : (
                <ul>
                  {violations.slice(-10).map((v, i) => (
                    <li key={i} className={`violation type-${v.type}`}>
                      <strong>{new Date(v.timestamp).toLocaleTimeString()}</strong>
                      {' - '}
                      {v.description}
                    </li>
                  ))}
                </ul>
              )}
            </div>

            <button 
              className="end-button"
              onClick={endSession}
            >
              Завершить тестирование
            </button>
          </div>
        )}

        {sessionActive && violations.length > 0 && (
          <div className="violations-summary">
            <h3>Статистика нарушений</h3>
            <div className="stats">
              {Object.entries(
                violations.reduce((acc, v) => {
                  acc[v.type] = (acc[v.type] || 0) + 1;
                  return acc;
                }, {} as Record<string, number>)
              ).map(([type, count]) => (
                <div key={type} className="stat-item">
                  <span className="stat-type">{type}</span>
                  <span className="stat-count">{count}</span>
                </div>
              ))}
            </div>
          </div>
        )}
      </main>
    </div>
  );
}

export default App;
