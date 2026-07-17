import React, { useEffect, useState, useCallback } from 'react';
import { AppSettings, ConnectionState } from '../types';

const DEFAULT_SETTINGS: AppSettings = {
  language: 'en-US', theme: 'dark', captionSize: 'medium', captionPosition: 'bottom',
  voice: 'default', avatar: 'default-3d-signbot', speechSpeed: 1.0, transparency: 85,
  backendUrl: 'http://localhost:8000', apiKey: '', recognitionMode: 'speech-api',
  micEnabled: false, camEnabled: false, gestureEnabled: true, gestureConfidenceThreshold: 0.6,
};

const PopupApp: React.FC = () => {
  const [settings, setSettings] = useState<AppSettings>(DEFAULT_SETTINGS);
  const [conn, setConn] = useState<ConnectionState>({ isConnected: false, latencyMs: 0, error: null, isRetrying: false });
  const [saving, setSaving] = useState(false);
  const [lastSaved, setLastSaved] = useState('');

  // ── Load settings & connection state ───────────────────────────────────────
  useEffect(() => {
    chrome.runtime.sendMessage({ action: 'GET_SETTINGS' }, (resp) => {
      if (resp && !chrome.runtime.lastError) {
        setSettings((prev) => ({ ...prev, ...resp }));
      }
    });
  }, []);

  // ── Listen for live status updates ─────────────────────────────────────────
  useEffect(() => {
    const handler = (msg: any) => {
      if (msg.action === 'BACKEND_STATUS_CHANGE' && msg.payload) {
        setConn(prev => ({ ...prev, ...msg.payload }));
      }
    };
    chrome.runtime.onMessage.addListener(handler);
    return () => chrome.runtime.onMessage.removeListener(handler);
  }, []);

  // ── Save a single setting ──────────────────────────────────────────────────
  const setSetting = useCallback(<K extends keyof AppSettings>(key: K, value: AppSettings[K]) => {
    const patch = { [key]: value } as Partial<AppSettings>;
    setSettings(prev => ({ ...prev, ...patch }));
    chrome.runtime.sendMessage({ action: 'UPDATE_SETTINGS', payload: patch });
  }, []);

  // ── Save backend URL ───────────────────────────────────────────────────────
  const saveBackendUrl = async () => {
    setSaving(true);
    chrome.runtime.sendMessage({ action: 'UPDATE_SETTINGS', payload: { backendUrl: settings.backendUrl } }, () => {
      setSaving(false);
      setLastSaved(new Date().toLocaleTimeString());
    });
  };

  // ── Toggle overlay visibility on active Meet tab ───────────────────────────
  const toggleAccessibility = () => {
    chrome.tabs.query({ active: true, currentWindow: true }, (tabs) => {
      if (tabs[0]?.id) {
        chrome.tabs.sendMessage(tabs[0].id, { action: 'TOGGLE_ACCESSIBILITY' });
      }
    });
  };

  const openOptions = () => chrome.runtime.openOptionsPage();

  // ── Status color ───────────────────────────────────────────────────────────
  const statusColor = conn.isConnected ? '#22c55e' : conn.isRetrying ? '#f59e0b' : '#ef4444';
  const statusText = conn.isConnected
    ? `Connected · ${conn.latencyMs}ms`
    : conn.isRetrying
    ? 'Reconnecting…'
    : 'Not connected';

  return (
    <div style={{
      width: 340,
      background: 'linear-gradient(160deg, #0f172a 0%, #1e293b 100%)',
      color: '#f1f5f9',
      fontFamily: "'Inter', system-ui, -apple-system, sans-serif",
      minHeight: 480,
      display: 'flex',
      flexDirection: 'column',
    }}>

      {/* ── Header ─────────────────────────────────────────────────────────── */}
      <div style={{
        padding: '18px 18px 14px',
        background: 'linear-gradient(135deg, rgba(59,130,246,0.12), rgba(99,102,241,0.08))',
        borderBottom: '1px solid rgba(148,163,184,0.1)',
        display: 'flex',
        alignItems: 'center',
        gap: 12,
      }}>
        <div style={{
          width: 38, height: 38, borderRadius: 12,
          background: 'linear-gradient(135deg, #3b82f6, #6366f1)',
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          boxShadow: '0 4px 14px rgba(99,102,241,0.4)',
          flexShrink: 0,
        }}>
          <span style={{ fontSize: 18 }}>🤟</span>
        </div>
        <div style={{ flex: 1 }}>
          <div style={{ fontSize: 15, fontWeight: 700, letterSpacing: '-0.01em' }}>SignBridge Live</div>
          <div style={{ fontSize: 11, color: '#64748b', marginTop: 1 }}>AI Sign Language Bridge</div>
        </div>
        <button
          onClick={openOptions}
          title="Settings"
          style={{
            background: 'rgba(148,163,184,0.1)',
            border: '1px solid rgba(148,163,184,0.15)',
            borderRadius: 8, padding: 7,
            cursor: 'pointer', color: '#94a3b8',
            display: 'flex', alignItems: 'center',
          }}
        >
          <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-4 0v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83-2.83l.06-.06A1.65 1.65 0 0 0 4.68 15a1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1 0-4h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 2.83-2.83l.06.06A1.65 1.65 0 0 0 9 4.68a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 2.83l-.06.06A1.65 1.65 0 0 0 19.4 9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1z"/>
          </svg>
        </button>
      </div>

      {/* ── Backend Status ──────────────────────────────────────────────────── */}
      <div style={{ padding: '14px 18px 0' }}>
        <div style={{
          background: 'rgba(15,23,42,0.8)',
          border: `1px solid ${conn.isConnected ? 'rgba(34,197,94,0.25)' : 'rgba(148,163,184,0.1)'}`,
          borderRadius: 12,
          padding: '10px 14px',
          display: 'flex',
          alignItems: 'center',
          gap: 10,
        }}>
          <div style={{
            width: 8, height: 8, borderRadius: '50%',
            background: statusColor,
            boxShadow: conn.isConnected ? `0 0 8px ${statusColor}` : 'none',
            flexShrink: 0,
            animation: conn.isRetrying ? 'pulse 1s infinite' : 'none',
          }} />
          <div style={{ flex: 1, minWidth: 0 }}>
            <div style={{ fontSize: 11, fontWeight: 600, color: conn.isConnected ? '#22c55e' : '#94a3b8' }}>
              {statusText}
            </div>
            {conn.error && !conn.isConnected && (
              <div style={{ fontSize: 10, color: '#64748b', marginTop: 2, whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                {conn.error}
              </div>
            )}
          </div>
          <div style={{
            fontSize: 10,
            color: '#475569',
            background: 'rgba(148,163,184,0.08)',
            padding: '3px 7px',
            borderRadius: 6,
            whiteSpace: 'nowrap',
          }}>
            FastAPI
          </div>
        </div>
      </div>

      {/* ── Quick Toggles ───────────────────────────────────────────────────── */}
      <div style={{ padding: '14px 18px 0' }}>
        <div style={{ fontSize: 10, fontWeight: 700, color: '#475569', letterSpacing: '0.08em', textTransform: 'uppercase', marginBottom: 8 }}>
          Quick Controls
        </div>
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 8 }}>
          {[
            {
              label: 'Camera',
              icon: settings.camEnabled
                ? <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M23 7l-7 5 7 5V7z"/><rect x="1" y="5" width="15" height="14" rx="2" ry="2"/></svg>
                : <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M16 16v1a2 2 0 0 1-2 2H3a2 2 0 0 1-2-2V7a2 2 0 0 1 2-2h2m5.66 0H14a2 2 0 0 1 2 2v3.34l1 1L23 7v10"/><line x1="1" y1="1" x2="23" y2="23"/></svg>,
              active: settings.camEnabled,
              onClick: () => setSetting('camEnabled', !settings.camEnabled),
            },
            {
              label: 'Gesture',
              icon: <span style={{ fontSize: 16 }}>🤟</span>,
              active: settings.gestureEnabled,
              onClick: () => setSetting('gestureEnabled', !settings.gestureEnabled),
            },
            {
              label: 'Overlay',
              icon: <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><rect x="3" y="3" width="18" height="18" rx="2"/><path d="M3 9h18M9 21V9"/></svg>,
              active: true,
              onClick: toggleAccessibility,
            },
          ].map(({ label, icon, active, onClick }) => (
            <button
              key={label}
              onClick={onClick}
              style={{
                background: active
                  ? 'linear-gradient(135deg, rgba(59,130,246,0.2), rgba(99,102,241,0.15))'
                  : 'rgba(15,23,42,0.8)',
                border: `1px solid ${active ? 'rgba(99,102,241,0.4)' : 'rgba(148,163,184,0.1)'}`,
                borderRadius: 10,
                padding: '10px 8px',
                cursor: 'pointer',
                color: active ? '#818cf8' : '#64748b',
                display: 'flex',
                flexDirection: 'column',
                alignItems: 'center',
                gap: 5,
                transition: 'all 0.15s',
              }}
            >
              {icon}
              <span style={{ fontSize: 10, fontWeight: 600, color: active ? '#e2e8f0' : '#64748b' }}>
                {label}
              </span>
            </button>
          ))}
        </div>
      </div>

      {/* ── Backend URL ─────────────────────────────────────────────────────── */}
      <div style={{ padding: '14px 18px 0' }}>
        <div style={{ fontSize: 10, fontWeight: 700, color: '#475569', letterSpacing: '0.08em', textTransform: 'uppercase', marginBottom: 8 }}>
          Backend URL
        </div>
        <div style={{ display: 'flex', gap: 6 }}>
          <input
            type="text"
            value={settings.backendUrl}
            onChange={e => setSettings(prev => ({ ...prev, backendUrl: e.target.value }))}
            style={{
              flex: 1,
              background: 'rgba(15,23,42,0.8)',
              border: '1px solid rgba(148,163,184,0.15)',
              borderRadius: 8,
              padding: '7px 10px',
              color: '#e2e8f0',
              fontSize: 11,
              fontFamily: 'monospace',
              outline: 'none',
            }}
            placeholder="http://localhost:8000"
          />
          <button
            onClick={saveBackendUrl}
            disabled={saving}
            style={{
              background: 'linear-gradient(135deg, #3b82f6, #6366f1)',
              border: 'none',
              borderRadius: 8,
              padding: '7px 12px',
              color: 'white',
              fontSize: 11,
              fontWeight: 600,
              cursor: 'pointer',
              opacity: saving ? 0.7 : 1,
            }}
          >
            {saving ? '…' : 'Save'}
          </button>
        </div>
        {lastSaved && (
          <div style={{ fontSize: 10, color: '#22c55e', marginTop: 4 }}>✓ Saved at {lastSaved}</div>
        )}
      </div>

      {/* ── Caption size ────────────────────────────────────────────────────── */}
      <div style={{ padding: '14px 18px 0' }}>
        <div style={{ fontSize: 10, fontWeight: 700, color: '#475569', letterSpacing: '0.08em', textTransform: 'uppercase', marginBottom: 8 }}>
          Caption Size
        </div>
        <div style={{ display: 'flex', gap: 6 }}>
          {(['small', 'medium', 'large', 'huge'] as const).map(size => (
            <button
              key={size}
              onClick={() => setSetting('captionSize', size)}
              style={{
                flex: 1,
                background: settings.captionSize === size ? 'rgba(99,102,241,0.2)' : 'rgba(15,23,42,0.8)',
                border: `1px solid ${settings.captionSize === size ? 'rgba(99,102,241,0.5)' : 'rgba(148,163,184,0.1)'}`,
                borderRadius: 7,
                padding: '6px 4px',
                color: settings.captionSize === size ? '#818cf8' : '#64748b',
                fontSize: 10,
                fontWeight: 600,
                cursor: 'pointer',
                textTransform: 'capitalize',
              }}
            >
              {size}
            </button>
          ))}
        </div>
      </div>

      {/* ── Transparency ────────────────────────────────────────────────────── */}
      <div style={{ padding: '14px 18px 0' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 8 }}>
          <div style={{ fontSize: 10, fontWeight: 700, color: '#475569', letterSpacing: '0.08em', textTransform: 'uppercase' }}>
            Overlay Opacity
          </div>
          <div style={{ fontSize: 10, color: '#818cf8', fontWeight: 700 }}>{settings.transparency}%</div>
        </div>
        <input
          type="range" min={30} max={100} value={settings.transparency}
          onChange={e => setSetting('transparency', parseInt(e.target.value))}
          style={{ width: '100%', accentColor: '#6366f1', cursor: 'pointer' }}
        />
      </div>

      {/* ── Footer ──────────────────────────────────────────────────────────── */}
      <div style={{
        marginTop: 'auto',
        padding: '14px 18px',
        borderTop: '1px solid rgba(148,163,184,0.08)',
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
      }}>
        <span style={{ fontSize: 10, color: '#334155' }}>Open Google Meet to begin</span>
        <button
          onClick={() => window.open(settings.backendUrl + '/docs', '_blank')}
          style={{
            background: 'transparent',
            border: '1px solid rgba(148,163,184,0.15)',
            borderRadius: 6,
            padding: '4px 10px',
            color: '#64748b',
            fontSize: 10,
            cursor: 'pointer',
          }}
        >
          API Docs ↗
        </button>
      </div>
    </div>
  );
};

export default PopupApp;
