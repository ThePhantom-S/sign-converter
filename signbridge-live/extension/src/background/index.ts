import { wsClient } from '../services/webSocketClient';
import { AppSettings, ExtensionMessage } from '../types';

console.log('[SignBridge SW] Background Service Worker v1.0 started');

let isStreaming = false;

// ── Default settings ─────────────────────────────────────────────────────────
const DEFAULT_SETTINGS: AppSettings = {
  language: 'en-US',
  theme: 'dark',
  captionSize: 'medium',
  captionPosition: 'bottom',
  voice: 'default',
  avatar: 'default-3d-signbot',
  speechSpeed: 1.0,
  transparency: 85,
  backendUrl: 'http://localhost:8000',
  apiKey: '',
  recognitionMode: 'speech-api',
  micEnabled: false,
  camEnabled: false,
  gestureEnabled: true,
  gestureConfidenceThreshold: 0.6,
};

// ── Broadcast to all Meet tabs ────────────────────────────────────────────────
async function broadcastToMeetTabs(message: ExtensionMessage) {
  const tabs = await chrome.tabs.query({ url: 'https://meet.google.com/*' });
  for (const tab of tabs) {
    if (tab.id) {
      chrome.tabs.sendMessage(tab.id, message).catch(() => {});
    }
  }
}

// ── Set up WebSocket callbacks ────────────────────────────────────────────────
function setupWsCallbacks() {
  wsClient.onCaptionCallback = (caption) => {
    broadcastToMeetTabs({ action: 'NEW_CAPTION', payload: caption });
  };

  wsClient.onGestureCallback = (gesture) => {
    broadcastToMeetTabs({ action: 'NEW_GESTURE', payload: gesture });
  };

  wsClient.onStatusChangeCallback = (status) => {
    // Broadcast to all extension contexts (popup, content scripts)
    chrome.runtime.sendMessage({ action: 'BACKEND_STATUS_CHANGE', payload: status }).catch(() => {});
    broadcastToMeetTabs({ action: 'BACKEND_STATUS_CHANGE', payload: status });
  };
}

// ── Message Router ────────────────────────────────────────────────────────────
chrome.runtime.onMessage.addListener((message: ExtensionMessage, _sender, sendResponse) => {
  const { action, payload } = message;

  (async () => {
    try {
      switch (action) {
        case 'GET_SETTINGS': {
          const stored = await chrome.storage.local.get(null);
          sendResponse({ ...DEFAULT_SETTINGS, ...stored });
          break;
        }

        case 'UPDATE_SETTINGS': {
          await chrome.storage.local.set(payload);
          // If backend URL changed while streaming, reconnect
          if (payload.backendUrl && isStreaming) {
            wsClient.disconnect();
            setupWsCallbacks();
            await wsClient.connect(payload.backendUrl);
          }
          sendResponse({ success: true });
          break;
        }

        case 'MEETING_STARTED': {
          console.log('[SignBridge SW] Meeting started:', payload?.title);
          isStreaming = true;

          const stored = await chrome.storage.local.get(['backendUrl']);
          const backendUrl = stored.backendUrl || DEFAULT_SETTINGS.backendUrl;

          setupWsCallbacks();
          await wsClient.connect(backendUrl);
          sendResponse({ success: true });
          break;
        }

        case 'MEETING_ENDED': {
          console.log('[SignBridge SW] Meeting ended');
          isStreaming = false;
          wsClient.disconnect();
          sendResponse({ success: true });
          break;
        }

        case 'AUDIO_DATA': {
          // payload = { data: base64, timestamp }
          wsClient.sendAudio(payload);
          sendResponse({ success: true });
          break;
        }

        case 'VIDEO_FRAME': {
          // payload = { frame: base64, timestamp }
          wsClient.sendVideoFrame(payload);
          sendResponse({ success: true });
          break;
        }

        default:
          sendResponse({ error: `Unknown action: ${action}` });
      }
    } catch (err: any) {
      console.error('[SignBridge SW] Error handling:', action, err);
      sendResponse({ error: err.message });
    }
  })();

  return true; // Keep async channel open
});

// ── Install handler ───────────────────────────────────────────────────────────
chrome.runtime.onInstalled.addListener(({ reason }) => {
  console.log('[SignBridge SW] onInstalled:', reason);
  chrome.storage.local.set(DEFAULT_SETTINGS);
});

export {};
