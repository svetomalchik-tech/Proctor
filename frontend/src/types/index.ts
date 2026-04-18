export type ViolationType = 
  | 'eye_away'
  | 'head_turn'
  | 'phone_usage'
  | 'multi_face'
  | 'tab_switch'
  | 'app_change'
  | 'exit_fullscreen'
  | 'messenger_usage';

export interface Violation {
  type: ViolationType;
  timestamp: string;
  confidence: number;
  description: string;
  frame_data?: string;
}

export interface SessionStatus {
  session_id: string;
  user_id: string;
  exam_id: string;
  status: 'pending' | 'active' | 'paused' | 'completed' | 'violated';
  started_at?: string;
  ended_at?: string;
  violations: Violation[];
  violation_count: number;
}

export interface ProctorSettings {
  eyeAwayThresholdSec: number;
  headTurnThresholdDeg: number;
  phoneDetectionConfidence: number;
  multiFaceDetection: boolean;
  tabSwitchDetection: boolean;
  fullscreenRequired: boolean;
  allowedApps: string[];
}

export interface WSMessage {
  type: 'video_frame' | 'screen_capture' | 'heartbeat' | 'violation_warning';
  frame?: string;
  image?: string;
  active_window?: string;
  is_fullscreen?: boolean;
  violation_id?: string;
}

export interface WSResponse {
  type: 'video_analysis' | 'screen_analysis' | 'heartbeat' | 'error';
  violations?: Violation[];
  metadata?: Record<string, unknown>;
  timestamp?: string;
  session_status?: string;
  message?: string;
}
