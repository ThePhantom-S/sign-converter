import { ConnectionState, CaptionEntry, GesturePrediction } from '../types';

const WS_RECONNECT_DELAY_MS = 3000;
const WS_MAX_RECONNECT = 5;
const HEARTBEAT_INTERVAL_MS = 5000;

class WebSocketClient {
  private socket: WebSocket | null = null;
  private baseUrl: string = '';
  private reconnectAttempts = 0;
  private heartbeatTimer: ReturnType<typeof setInterval> | null = null;
  private isConnecting = false;
  private isMockMode = false;
  private mockTimer: ReturnType<typeof setInterval> | null = null;

  // ── Public callbacks ──────────────────────────────────────────────────────
  public onCaptionCallback: ((c: CaptionEntry) => void) | null = null;
  public onGestureCallback: ((g: GesturePrediction) => void) | null = null;
  public onStatusChangeCallback: ((s: Partial<ConnectionState>) => void) | null = null;

  // ── Connect ───────────────────────────────────────────────────────────────
  public async connect(backendUrl: string): Promise<void> {
    if (this.socket?.readyState === WebSocket.OPEN || this.isConnecting) return;
    this.isConnecting = true;
    this.baseUrl = backendUrl;

    const wsUrl = backendUrl.replace(/^http/, 'ws') + '/api/v1/stream';
    this.notify({ isRetrying: false, error: null });

    try {
      this.socket = new WebSocket(wsUrl);

      this.socket.onopen = () => {
        this.isConnecting = false;
        this.isMockMode = false;
        this.reconnectAttempts = 0;
        console.log('[SignBridge WS] Connected to', wsUrl);
        this.notify({ isConnected: true, error: null, isRetrying: false, latencyMs: 0 });
        this.startHeartbeat();
      };

      this.socket.onmessage = (event) => {
        try {
          const msg = JSON.parse(event.data as string);
          this.handleMessage(msg);
        } catch (_) {
          // Binary or malformed — ignore
        }
      };

      this.socket.onerror = () => {
        console.warn('[SignBridge WS] Socket error');
      };

      this.socket.onclose = () => {
        this.stopHeartbeat();
        this.socket = null;
        this.scheduleReconnect();
      };
    } catch (err: any) {
      this.isConnecting = false;
      this.scheduleReconnect(err.message);
    }
  }

  // ── Message handler ───────────────────────────────────────────────────────
  private handleMessage(msg: Record<string, any>) {
    switch (msg.type) {
      case 'pong': {
        const latencyMs = Date.now() - (msg.timestamp ?? Date.now());
        this.notify({ latencyMs });
        break;
      }
      case 'caption': {
        if (this.onCaptionCallback && msg.payload) {
          this.onCaptionCallback(msg.payload as CaptionEntry);
        }
        break;
      }
      case 'gesture': {
        if (this.onGestureCallback && msg.payload) {
          this.onGestureCallback(msg.payload as GesturePrediction);
        }
        break;
      }
      case 'sentence': {
        // Gemini-built sentence — treat as a caption from gesture pipeline
        if (this.onCaptionCallback && msg.payload?.text) {
          this.onCaptionCallback({
            id: `sentence-${Date.now()}`,
            speaker: 'Sign Language',
            text: msg.payload.text,
            timestamp: Date.now(),
            isFinal: true,
          });
        }
        break;
      }
      case 'error': {
        console.warn('[SignBridge WS] Backend error:', msg.message);
        break;
      }
    }
  }

  // ── Send helpers ──────────────────────────────────────────────────────────
  public sendAudio(payload: { data: string; timestamp: number }) {
    this.sendJSON({ type: 'audio', payload, timestamp: payload.timestamp });
  }

  public sendVideoFrame(payload: { frame: string; timestamp: number }) {
    this.sendJSON({ type: 'video_frame', payload });
  }

  public sendJSON(data: object) {
    if (this.socket?.readyState === WebSocket.OPEN) {
      this.socket.send(JSON.stringify(data));
    }
  }

  // ── Heartbeat ─────────────────────────────────────────────────────────────
  private startHeartbeat() {
    this.heartbeatTimer = setInterval(() => {
      this.sendJSON({ type: 'ping', timestamp: Date.now() });
    }, HEARTBEAT_INTERVAL_MS);
  }

  private stopHeartbeat() {
    if (this.heartbeatTimer) {
      clearInterval(this.heartbeatTimer);
      this.heartbeatTimer = null;
    }
  }

  // ── Reconnection ──────────────────────────────────────────────────────────
  private scheduleReconnect(reason = 'disconnected') {
    this.isConnecting = false;
    if (this.reconnectAttempts < WS_MAX_RECONNECT) {
      this.reconnectAttempts++;
      this.notify({
        isConnected: false,
        isRetrying: true,
        error: `Backend ${reason} — reconnecting (${this.reconnectAttempts}/${WS_MAX_RECONNECT})…`,
      });
      setTimeout(() => this.connect(this.baseUrl), WS_RECONNECT_DELAY_MS);
    } else {
      this.notify({
        isConnected: false,
        isRetrying: false,
        error: 'Backend unreachable — demo mode active',
      });
      this.startMockMode();
    }
  }

  // ── Disconnect ────────────────────────────────────────────────────────────
  public disconnect() {
    this.stopHeartbeat();
    this.stopMockMode();
    if (this.socket) {
      this.socket.close();
      this.socket = null;
    }
    this.reconnectAttempts = 0;
    this.isConnecting = false;
    this.notify({ isConnected: false, latencyMs: 0, error: null, isRetrying: false });
  }

  // ── Status notify ─────────────────────────────────────────────────────────
  private notify(status: Partial<ConnectionState>) {
    this.onStatusChangeCallback?.(status);
  }

  // ── Mock mode ─────────────────────────────────────────────────────────────
  private startMockMode() {
    if (this.isMockMode) return;
    this.isMockMode = true;

    const MOCK_CAPTIONS = [
      'Hello! SignBridge Live is running in demo mode.',
      'Connect the FastAPI backend to enable live gesture recognition.',
      'The extension captures your webcam and sends frames to the backend.',
      'Recognized ASL gestures appear here in real time.',
      'Start the backend with: uv run uvicorn app.main:app --reload',
    ];

    let idx = 0;
    this.mockTimer = setInterval(() => {
      this.onCaptionCallback?.({
        id: `mock-${idx}`,
        speaker: 'SignBridge Demo',
        text: MOCK_CAPTIONS[idx % MOCK_CAPTIONS.length],
        timestamp: Date.now(),
        isFinal: true,
      });
      idx++;
    }, 8000);

    this.notify({ isConnected: true, latencyMs: 5, error: 'Demo mode (no backend)' });
  }

  private stopMockMode() {
    this.isMockMode = false;
    if (this.mockTimer) {
      clearInterval(this.mockTimer);
      this.mockTimer = null;
    }
  }

  public get isConnected(): boolean {
    return this.socket?.readyState === WebSocket.OPEN;
  }
}

export const wsClient = new WebSocketClient();
export default wsClient;
