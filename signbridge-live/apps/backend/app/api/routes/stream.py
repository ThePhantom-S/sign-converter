"""
WebSocket streaming endpoint for SignBridge Live.

Supported message types (client → server):
  - "ping"         → heartbeat, echoed back as "pong"
  - "audio"        → legacy audio caption flow
  - "video_frame"  → base64 video frame for gesture recognition (NEW)
  - "build_sentence" → trigger Gemini to form a sentence from buffered gestures
  - "reset"        → clear gesture sentence buffer

Server → client responses:
  - "pong"         → heartbeat response
  - "caption"      → live caption from audio pipeline
  - "gesture"      → gesture prediction { label, confidence, timestamp }
  - "sentence"     → Gemini-built natural-language sentence
  - "error"        → error description
"""

from __future__ import annotations

import json
import logging

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.services.gesture import gesture_service

logger = logging.getLogger(__name__)
router = APIRouter()


@router.websocket("/stream")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    logger.info("WebSocket connection accepted from %s", websocket.client)

    try:
        while True:
            raw = await websocket.receive_text()

            try:
                message = json.loads(raw)
            except json.JSONDecodeError:
                await _send(websocket, {"type": "error", "message": "Invalid JSON"})
                continue

            msg_type = message.get("type", "")

            # ── Heartbeat ────────────────────────────────────────────────
            if msg_type == "ping":
                await _send(
                    websocket,
                    {"type": "pong", "timestamp": message.get("timestamp")},
                )

            # ── Legacy audio caption (kept for backwards-compat) ─────────
            elif msg_type == "audio" or "audio" in message:
                await _send(
                    websocket,
                    {
                        "type": "caption",
                        "payload": {
                            "id": "live-backend-caption",
                            "speaker": "Meeting Participant",
                            "text": "Translation streaming successfully!",
                            "timestamp": message.get("timestamp", 0),
                            "isFinal": True,
                        },
                    },
                )

            # ── Gesture recognition (NEW) ────────────────────────────────
            elif msg_type == "video_frame":
                payload = message.get("payload", {})
                frame_b64 = payload.get("frame", "")
                timestamp = float(payload.get("timestamp", 0))

                if not frame_b64:
                    await _send(
                        websocket,
                        {"type": "error", "message": "Empty 'frame' in video_frame payload"},
                    )
                    continue

                prediction = await gesture_service.process_frame(frame_b64, timestamp)

                if prediction is not None:
                    await _send(
                        websocket,
                        {
                            "type": "gesture",
                            "payload": {
                                "label": prediction.label,
                                "confidence": prediction.confidence,
                                "timestamp": prediction.timestamp,
                            },
                        },
                    )

            # ── Build sentence from gesture buffer ───────────────────────
            elif msg_type == "build_sentence":
                sentence = await gesture_service.build_sentence()
                if sentence:
                    await _send(
                        websocket,
                        {"type": "sentence", "payload": {"text": sentence}},
                    )
                else:
                    await _send(
                        websocket,
                        {
                            "type": "sentence",
                            "payload": {"text": None, "reason": "gemini_disabled_or_empty_buffer"},
                        },
                    )

            # ── Reset gesture buffer ─────────────────────────────────────
            elif msg_type == "reset":
                gesture_service.reset_sentence_buffer()
                await _send(websocket, {"type": "reset_ack"})

            else:
                logger.debug("Unknown message type: %s", msg_type)

    except WebSocketDisconnect:
        logger.info("WebSocket disconnected: %s", websocket.client)
    except Exception as exc:
        logger.warning("Error in WebSocket stream: %s", exc, exc_info=True)


async def _send(websocket: WebSocket, data: dict) -> None:
    """Safely send a JSON message, suppressing send-after-close errors."""
    try:
        await websocket.send_text(json.dumps(data))
    except Exception as exc:
        logger.debug("WebSocket send failed (likely closed): %s", exc)
