import React, { useEffect, useRef, useState, useCallback } from 'react';
import { CaptionEntry, GesturePrediction, ConnectionState } from '../types';

// ── Types ─────────────────────────────────────────────────────────────────────
interface OverlayState {
  captions: CaptionEntry[];
  gesture: GesturePrediction | null;
  connection: ConnectionState;
  settings: {
    captionSize: 'small' | 'medium' | 'large' | 'huge';
    transparency: number;
    gestureEnabled: boolean;
  };
}

const SIZE_MAP = {
  small: '13px',
  medium: '15px',
  large: '18px',
  huge: '22px',
} as const;

const MAX_CAPTIONS = 3;
const GESTURE_DISPLAY_MS = 3000;

// ── Overlay Container ─────────────────────────────────────────────────────────
const OverlayContainer: React.FC = () => {
  const [state, setState] = useState<OverlayState>({
    captions: [],
    gesture: null,
    connection: { isConnected: false, latencyMs: 0, error: null, isRetrying: false },
    settings: { captionSize: 'medium', transparency: 85, gestureEnabled: true },
  });
  const [isExpanded, setIsExpanded] = useState(true);
  const [isDragging, setIsDragging] = useState(false);
  const [pos, setPos] = useState({ x: 16, y: 16 });
  const dragOffset = useRef({ x: 0, y: 0 });
  const gestureTimer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const speechSynthRef = useRef<SpeechSynthesisUtterance | null>(null);
  const panelRef = useRef<HTMLDivElement>(null);

  // ── Load settings from storage ─────────────────────────────────────────────
  useEffect(() => {
    chrome.storage.local.get(['captionSize', 'transparency', 'gestureEnabled'], (data) => {
      setState(prev => ({
        ...prev,
        settings: {
          captionSize: (data.captionSize as any) || 'medium',
          transparency: typeof data.transparency === 'number' ? data.transparency : 85,
          gestureEnabled: data.gestureEnabled !== false,
        },
      }));
    });
  }, []);

  // ── Listen for messages via shadow DOM custom events ───────────────────────
  useEffect(() => {
    const hostShadow = panelRef.current?.getRootNode() as ShadowRoot | null;
    if (!hostShadow) return;

    const handleMessage = (e: Event) => {
      const { action, payload } = (e as CustomEvent).detail;

      switch (action) {
        case 'NEW_CAPTION': {
          const caption = payload as CaptionEntry;
          setState(prev => {
            const deduped = prev.captions.filter(c => c.id !== caption.id);
            const next = [...deduped, caption].slice(-MAX_CAPTIONS);
            return { ...prev, captions: next };
          });
          // Speak final captions
          if (caption.isFinal && 'speechSynthesis' in window) {
            window.speechSynthesis.cancel();
            const utt = new SpeechSynthesisUtterance(caption.text);
            utt.rate = 0.95;
            speechSynthRef.current = utt;
            window.speechSynthesis.speak(utt);
          }
          break;
        }

        case 'NEW_GESTURE': {
          const gesture = payload as GesturePrediction;
          setState(prev => ({ ...prev, gesture }));
          // Auto-clear gesture display after timeout
          if (gestureTimer.current) clearTimeout(gestureTimer.current);
          gestureTimer.current = setTimeout(() => {
            setState(prev => ({ ...prev, gesture: null }));
          }, GESTURE_DISPLAY_MS);
          break;
        }

        case 'BACKEND_STATUS_CHANGE': {
          setState(prev => ({
            ...prev,
            connection: { ...prev.connection, ...(payload as Partial<ConnectionState>) },
          }));
          break;
        }
      }
    };

    hostShadow.addEventListener('signbridge-message', handleMessage);
    return () => hostShadow.removeEventListener('signbridge-message', handleMessage);
  }, []);

  // ── Drag handlers ──────────────────────────────────────────────────────────
  const onMouseDown = useCallback((e: React.MouseEvent) => {
    if ((e.target as HTMLElement).closest('[data-no-drag]')) return;
    setIsDragging(true);
    dragOffset.current = { x: e.clientX - pos.x, y: e.clientY - pos.y };
    e.preventDefault();
  }, [pos]);

  useEffect(() => {
    if (!isDragging) return;
    const onMove = (e: MouseEvent) => {
      const nx = Math.max(0, Math.min(window.innerWidth - 340, e.clientX - dragOffset.current.x));
      const ny = Math.max(0, Math.min(window.innerHeight - 200, e.clientY - dragOffset.current.y));
      setPos({ x: nx, y: ny });
    };
    const onUp = () => setIsDragging(false);
    window.addEventListener('mousemove', onMove);
    window.addEventListener('mouseup', onUp);
    return () => { window.removeEventListener('mousemove', onMove); window.removeEventListener('mouseup', onUp); };
  }, [isDragging]);

  // ── Render ─────────────────────────────────────────────────────────────────
  const { captions, gesture, connection, settings } = state;
  const lastCaption = captions[captions.length - 1];
  const opacity = settings.transparency / 100;

  return (
    <div
      ref={panelRef}
      style={{
        position: 'fixed',
        left: pos.x,
        top: pos.y,
        width: 340,
        pointerEvents: 'all',
        userSelect: 'none',
        zIndex: 2147483647,
        cursor: isDragging ? 'grabbing' : 'grab',
        transition: isDragging ? 'none' : 'box-shadow 0.2s',
        filter: isDragging ? 'drop-shadow(0 8px 32px rgba(0,0,0,0.5))' : 'drop-shadow(0 4px 16px rgba(0,0,0,0.4))',
      }}
      onMouseDown={onMouseDown}
    >
      {/* ── Header bar ──────────────────────────────────────────────────── */}
      <div style={{
        background: 'linear-gradient(135deg, rgba(15,23,42,0.97) 0%, rgba(30,41,59,0.97) 100%)',
        backdropFilter: 'blur(20px)',
        WebkitBackdropFilter: 'blur(20px)',
        border: '1px solid rgba(148,163,184,0.12)',
        borderRadius: isExpanded ? '16px 16px 0 0' : '16px',
        padding: '10px 14px',
        display: 'flex',
        alignItems: 'center',
        gap: 8,
      }}>
        {/* Logo */}
        <div style={{
          width: 28, height: 28, borderRadius: 8,
          background: 'linear-gradient(135deg, #3b82f6, #6366f1)',
          display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0,
        }}>
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none">
            <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-1 14H9V8h2v8zm4 0h-2V8h2v8z" fill="white"/>
          </svg>
        </div>

        <div style={{ flex: 1, minWidth: 0 }}>
          <div style={{ color: '#f1f5f9', fontSize: 12, fontWeight: 700, letterSpacing: '0.02em', fontFamily: 'system-ui,sans-serif' }}>
            SignBridge Live
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 5, marginTop: 2 }}>
            <div style={{
              width: 6, height: 6, borderRadius: '50%',
              background: connection.isConnected ? '#22c55e' : connection.isRetrying ? '#f59e0b' : '#ef4444',
              boxShadow: connection.isConnected ? '0 0 6px #22c55e80' : 'none',
            }} />
            <span style={{ color: '#94a3b8', fontSize: 10, fontFamily: 'system-ui,sans-serif' }}>
              {connection.isConnected
                ? `Live · ${connection.latencyMs}ms`
                : connection.isRetrying
                ? 'Reconnecting…'
                : connection.error ?? 'Offline'}
            </span>
          </div>
        </div>

        {/* Collapse toggle */}
        <button
          data-no-drag
          onClick={() => setIsExpanded(v => !v)}
          style={{
            background: 'rgba(148,163,184,0.1)',
            border: '1px solid rgba(148,163,184,0.15)',
            borderRadius: 8,
            width: 28, height: 28,
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            cursor: 'pointer', color: '#94a3b8', flexShrink: 0,
          }}
        >
          <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
            {isExpanded
              ? <path d="M19 9l-7 7-7-7"/>
              : <path d="M5 15l7-7 7 7"/>}
          </svg>
        </button>
      </div>

      {/* ── Expanded body ────────────────────────────────────────────────── */}
      {isExpanded && (
        <div style={{
          background: 'rgba(15,23,42,0.95)',
          backdropFilter: 'blur(20px)',
          WebkitBackdropFilter: 'blur(20px)',
          border: '1px solid rgba(148,163,184,0.12)',
          borderTop: 'none',
          borderRadius: '0 0 16px 16px',
          overflow: 'hidden',
        }}>

          {/* Gesture pill */}
          {gesture && settings.gestureEnabled && (
            <div style={{
              margin: '10px 12px 0',
              padding: '8px 12px',
              background: 'linear-gradient(135deg, rgba(59,130,246,0.15), rgba(99,102,241,0.15))',
              border: '1px solid rgba(99,102,241,0.3)',
              borderRadius: 10,
              display: 'flex',
              alignItems: 'center',
              gap: 8,
              animation: 'signbridge-fadein 0.2s ease',
            }}>
              <div style={{
                width: 32, height: 32, borderRadius: 8,
                background: 'linear-gradient(135deg, #3b82f6, #6366f1)',
                display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0,
              }}>
                <span style={{ fontSize: 16 }}>🤟</span>
              </div>
              <div style={{ flex: 1, minWidth: 0 }}>
                <div style={{ color: '#818cf8', fontSize: 9, fontWeight: 700, letterSpacing: '0.08em', textTransform: 'uppercase', fontFamily: 'system-ui,sans-serif' }}>
                  ASL Gesture
                </div>
                <div style={{ color: '#e2e8f0', fontSize: 20, fontWeight: 800, letterSpacing: '0.05em', fontFamily: 'system-ui,sans-serif', lineHeight: 1.2 }}>
                  {gesture.label}
                </div>
              </div>
              <div style={{
                background: `conic-gradient(#6366f1 ${gesture.confidence * 360}deg, rgba(148,163,184,0.1) 0deg)`,
                borderRadius: '50%',
                width: 32, height: 32,
                display: 'flex', alignItems: 'center', justifyContent: 'center',
                position: 'relative', flexShrink: 0,
              }}>
                <div style={{
                  position: 'absolute', width: 24, height: 24, borderRadius: '50%',
                  background: 'rgba(15,23,42,0.95)',
                  display: 'flex', alignItems: 'center', justifyContent: 'center',
                }}>
                  <span style={{ color: '#818cf8', fontSize: 8, fontWeight: 700, fontFamily: 'system-ui,sans-serif' }}>
                    {Math.round(gesture.confidence * 100)}%
                  </span>
                </div>
              </div>
            </div>
          )}

          {/* Caption display */}
          <div style={{
            padding: '10px 12px 12px',
            minHeight: 72,
            opacity,
          }}>
            {!lastCaption ? (
              <div style={{
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                minHeight: 52,
                gap: 6,
              }}>
                <div style={{ display: 'flex', gap: 3 }}>
                  {[0, 1, 2].map(i => (
                    <div key={i} style={{
                      width: 4, height: 4, borderRadius: '50%',
                      background: '#475569',
                      animation: `signbridge-pulse 1.4s ease-in-out ${i * 0.2}s infinite`,
                    }} />
                  ))}
                </div>
                <span style={{
                  color: '#475569', fontSize: 12,
                  fontStyle: 'italic', fontFamily: 'system-ui,sans-serif',
                }}>
                  Listening for audio & gestures…
                </span>
              </div>
            ) : (
              <div>
                <div style={{
                  color: '#38bdf8',
                  fontSize: 9,
                  fontWeight: 700,
                  letterSpacing: '0.08em',
                  textTransform: 'uppercase',
                  marginBottom: 4,
                  fontFamily: 'system-ui,sans-serif',
                }}>
                  {lastCaption.speaker}
                </div>
                <p style={{
                  color: '#f1f5f9',
                  fontSize: SIZE_MAP[settings.captionSize],
                  fontWeight: 500,
                  lineHeight: 1.55,
                  margin: 0,
                  fontFamily: 'system-ui,sans-serif',
                }}>
                  {lastCaption.text}
                </p>
              </div>
            )}
          </div>

          {/* Footer hint */}
          <div style={{
            borderTop: '1px solid rgba(148,163,184,0.08)',
            padding: '6px 12px',
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
          }}>
            <span style={{ color: '#334155', fontSize: 9, fontFamily: 'system-ui,sans-serif' }}>
              Drag to move
            </span>
            <span style={{ color: '#334155', fontSize: 9, fontFamily: 'system-ui,sans-serif' }}>
              SignBridge v1.0
            </span>
          </div>
        </div>
      )}

      {/* Keyframe styles injected inline */}
      <style>{`
        @keyframes signbridge-fadein {
          from { opacity: 0; transform: translateY(-4px); }
          to   { opacity: 1; transform: translateY(0); }
        }
        @keyframes signbridge-pulse {
          0%, 80%, 100% { transform: scale(0.6); opacity: 0.3; }
          40% { transform: scale(1); opacity: 1; }
        }
      `}</style>
    </div>
  );
};

export default OverlayContainer;
