export interface AppSettings {
  language: string;
  theme: 'light' | 'dark' | 'system';
  captionSize: 'small' | 'medium' | 'large' | 'huge';
  captionPosition: 'top' | 'bottom';
  voice: string;
  avatar: string;
  speechSpeed: number;
  transparency: number; // 0 to 100
  backendUrl: string;
  apiKey: string;
  recognitionMode: 'speech-api' | 'backend-ai';
  micEnabled: boolean;
  camEnabled: boolean;
  gestureEnabled: boolean;
  gestureConfidenceThreshold: number;
}

export type MeetingStatus = 'IDLE' | 'DETECTED' | 'CONNECTING' | 'ACTIVE' | 'ENDED';

export interface MeetingSession {
  id: string;
  title: string;
  status: MeetingStatus;
  startTime?: number;
  endTime?: number;
  participantCount: number;
}

export interface CaptionEntry {
  id: string;
  speaker: string;
  text: string;
  timestamp: number;
  isFinal: boolean;
}

export interface GesturePrediction {
  label: string;
  confidence: number;
  timestamp: number;
}

export interface ConnectionState {
  isConnected: boolean;
  latencyMs: number;
  error: string | null;
  isRetrying: boolean;
}

// Chrome Extension message passing types
export type MessageAction =
  | 'GET_SETTINGS'
  | 'UPDATE_SETTINGS'
  | 'GET_MEETING_STATE'
  | 'MEETING_STARTED'
  | 'MEETING_ENDED'
  | 'AUDIO_DATA'
  | 'VIDEO_FRAME'
  | 'NEW_CAPTION'
  | 'NEW_GESTURE'
  | 'BACKEND_STATUS_CHANGE'
  | 'TOGGLE_MIC'
  | 'TOGGLE_CAM'
  | 'TOGGLE_ACCESSIBILITY';

export interface ExtensionMessage<T = any> {
  action: MessageAction;
  payload?: T;
}
