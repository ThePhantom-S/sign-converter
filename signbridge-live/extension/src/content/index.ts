/**
 * SignBridge Live — Content Script
 *
 * Injected into every https://meet.google.com/* page.
 * Responsibilities:
 *   1. Detect when a Google Meet call is actually active (not just the lobby)
 *   2. Inject the React overlay into a Shadow DOM host
 *   3. Capture webcam frames and send them to the background SW as VIDEO_FRAME
 *   4. Forward NEW_CAPTION, NEW_GESTURE, BACKEND_STATUS_CHANGE messages to the overlay
 */

import React from 'react';
import { createRoot } from 'react-dom/client';
import OverlayContainer from '../overlay/OverlayContainer';

// ── State ─────────────────────────────────────────────────────────────────────
let overlayHost: HTMLElement | null = null;
let reactRoot: ReturnType<typeof createRoot> | null = null;
let isMeetingActive = false;
let videoFrameInterval: ReturnType<typeof setInterval> | null = null;
let captureCanvas: HTMLCanvasElement | null = null;
let captureCtx: CanvasRenderingContext2D | null = null;
const FRAME_INTERVAL_MS = 300; // ~3fps to backend
const FRAME_WIDTH = 640;
const FRAME_HEIGHT = 480;

// ── CSS injection into shadow DOM ─────────────────────────────────────────────
function injectStyles(shadow: ShadowRoot) {
  const link = document.createElement('link');
  link.rel = 'stylesheet';
  link.href = chrome.runtime.getURL('assets/index.css');
  shadow.appendChild(link);
}

// ── Overlay injection ─────────────────────────────────────────────────────────
function injectOverlay() {
  if (document.getElementById('signbridge-overlay-host')) return;

  const host = document.createElement('div');
  host.id = 'signbridge-overlay-host';
  Object.assign(host.style, {
    position: 'fixed',
    top: '0',
    left: '0',
    width: '100vw',
    height: '100vh',
    pointerEvents: 'none',
    zIndex: '2147483647', // max z-index
  });
  document.body.appendChild(host);
  overlayHost = host;

  const shadow = host.attachShadow({ mode: 'open' });
  injectStyles(shadow);

  const container = document.createElement('div');
  container.className = 'signbridge-root dark';
  Object.assign(container.style, {
    width: '100%',
    height: '100%',
    pointerEvents: 'none',
    fontFamily: "'Inter', system-ui, sans-serif",
  });
  shadow.appendChild(container);

  reactRoot = createRoot(container);
  reactRoot.render(React.createElement(OverlayContainer));
  console.log('[SignBridge] Overlay mounted');
}

function removeOverlay() {
  stopVideoCapture();
  if (reactRoot) {
    reactRoot.unmount();
    reactRoot = null;
  }
  if (overlayHost) {
    overlayHost.remove();
    overlayHost = null;
  }
}

// ── Video frame capture ───────────────────────────────────────────────────────
function findMeetVideoElement(): HTMLVideoElement | null {
  // Google Meet renders remote/local video in <video> elements
  // The largest video element (by area) is typically the main feed
  const videos = Array.from(document.querySelectorAll('video')) as HTMLVideoElement[];
  if (!videos.length) return null;

  return videos.reduce((best, v) => {
    const area = v.videoWidth * v.videoHeight;
    const bestArea = best.videoWidth * best.videoHeight;
    return area > bestArea ? v : best;
  });
}

function ensureCanvas() {
  if (!captureCanvas) {
    captureCanvas = document.createElement('canvas');
    captureCanvas.width = FRAME_WIDTH;
    captureCanvas.height = FRAME_HEIGHT;
    captureCtx = captureCanvas.getContext('2d', { willReadFrequently: true });
  }
}

function startVideoCapture() {
  if (videoFrameInterval) return;
  ensureCanvas();

  videoFrameInterval = setInterval(async () => {
    // Check if gesture recognition is enabled
    const settings = await chrome.storage.local.get(['gestureEnabled', 'camEnabled']);
    if (!settings.gestureEnabled || !settings.camEnabled) return;

    const video = findMeetVideoElement();
    if (!video || video.readyState < 2 || !captureCtx || !captureCanvas) return;

    try {
      captureCtx.drawImage(video, 0, 0, FRAME_WIDTH, FRAME_HEIGHT);
      const frame = captureCanvas.toDataURL('image/jpeg', 0.6);

      chrome.runtime.sendMessage({
        action: 'VIDEO_FRAME',
        payload: { frame, timestamp: Date.now() / 1000 },
      }).catch(() => {});
    } catch (_err) {
      // Cross-origin video taint or canvas error — silently ignore
    }
  }, FRAME_INTERVAL_MS);
}

function stopVideoCapture() {
  if (videoFrameInterval) {
    clearInterval(videoFrameInterval);
    videoFrameInterval = null;
  }
}

// ── Message listener (from background SW) ────────────────────────────────────
chrome.runtime.onMessage.addListener((message, _sender, sendResponse) => {
  const { action, payload } = message;

  switch (action) {
    case 'NEW_CAPTION':
    case 'NEW_GESTURE':
    case 'BACKEND_STATUS_CHANGE': {
      // Forward into the overlay's shadow DOM via a custom event
      const event = new CustomEvent('signbridge-message', {
        detail: { action, payload },
        bubbles: false,
      });
      overlayHost?.shadowRoot?.dispatchEvent(event);
      sendResponse({ ok: true });
      break;
    }

    case 'TOGGLE_ACCESSIBILITY': {
      if (overlayHost) {
        overlayHost.style.display = overlayHost.style.display === 'none' ? '' : 'none';
      }
      sendResponse({ ok: true });
      break;
    }

    default:
      break;
  }

  return false;
});

// ── Meeting lifecycle detection ───────────────────────────────────────────────
function isMeetCallActive(): boolean {
  // Only trigger when actually inside a call, not lobby/join screen
  // Google Meet call URL has a 10-char code: /abc-defg-hij
  const pathMatch = /^\/[a-z]{3}-[a-z]{4}-[a-z]{3}(\/|$)/.test(window.location.pathname);
  const hasCallUI =
    !!document.querySelector('[data-call-ended]') === false &&
    (!!document.querySelector('[jscontroller="CzwT1c"]') ||
      !!document.querySelector('[data-is-meeting-controls]') ||
      !!document.querySelector('[data-participant-id]'));

  return pathMatch && hasCallUI;
}

function observeMeetingLifecycle() {
  let checkTimer: ReturnType<typeof setTimeout> | null = null;

  const observer = new MutationObserver(() => {
    // Debounce DOM change checks
    if (checkTimer) clearTimeout(checkTimer);
    checkTimer = setTimeout(() => {
      const active = isMeetCallActive();

      if (active && !isMeetingActive) {
        isMeetingActive = true;
        console.log('[SignBridge] Call detected — injecting overlay');
        injectOverlay();
        startVideoCapture();

        chrome.runtime.sendMessage({
          action: 'MEETING_STARTED',
          payload: {
            id: window.location.pathname.replace(/\//g, ''),
            title: document.title || 'Google Meet',
            status: 'ACTIVE',
            participantCount: document.querySelectorAll('[data-participant-id]').length || 1,
          },
        }).catch(() => {});

      } else if (!active && isMeetingActive) {
        isMeetingActive = false;
        console.log('[SignBridge] Call ended — removing overlay');
        removeOverlay();
        chrome.runtime.sendMessage({ action: 'MEETING_ENDED' }).catch(() => {});
      }
    }, 500);
  });

  observer.observe(document.body, { childList: true, subtree: true });

  // Also re-check on URL changes (SPA navigation)
  let lastPath = window.location.pathname;
  setInterval(() => {
    if (window.location.pathname !== lastPath) {
      lastPath = window.location.pathname;
      observer.takeRecords(); // flush pending
    }
  }, 1000);
}

// ── Bootstrap ─────────────────────────────────────────────────────────────────
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', observeMeetingLifecycle);
} else {
  observeMeetingLifecycle();
}

export {};
