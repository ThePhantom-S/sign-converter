"""
OpenCV-based frame decoder and full gesture detection pipeline.

Accepts a base64-encoded image frame (JPEG/PNG from browser canvas),
decodes it with OpenCV, and classifies the gesture using either:
- A custom trained RandomForest model (.pkl) via MediaPipe hand landmarks.
- A pre-trained MediaPipe GestureRecognizer model (.task).
"""

from __future__ import annotations

import base64
import logging

import cv2
import numpy as np

from app.core.config import get_settings
from app.cv.gesture_classifier import gesture_classifier
from app.cv.landmarks import extract_landmarks
from app.schemas.gesture import GesturePrediction

logger = logging.getLogger(__name__)


def _decode_base64_frame(frame_base64: str) -> np.ndarray | None:
    """
    Decode a base64 data-URL or raw base64 string into a BGR numpy array.
    """
    try:
        if "," in frame_base64:
            frame_base64 = frame_base64.split(",", 1)[1]

        raw_bytes = base64.b64decode(frame_base64)
        nparr = np.frombuffer(raw_bytes, np.uint8)
        frame_bgr = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

        if frame_bgr is None:
            logger.warning("cv2.imdecode returned None — invalid image data")
            return None

        return frame_bgr
    except Exception as exc:
        logger.error("Frame base64 decode failed: %s", exc)
        return None


async def detect_sign_language(
    frame_base64: str,
    timestamp: float = 0.0,
) -> GesturePrediction | None:
    """
    Full pipeline: base64 frame → OpenCV decode → gesture classification.
    Supports both custom .pkl models and MediaPipe pre-trained .task models.
    """
    settings = get_settings()

    if not settings.GESTURE_ENABLED:
        return None

    if not frame_base64:
        return None

    # ── Step 1: Decode frame ──────────────────────────────────────────────
    frame_bgr = _decode_base64_frame(frame_base64)
    if frame_bgr is None:
        return None

    # ── Step 2: Resize for consistent processing (max 640px wide) ─────────
    h, w = frame_bgr.shape[:2]
    if w > 640:
        scale = 640 / w
        frame_bgr = cv2.resize(
            frame_bgr,
            (640, int(h * scale)),
            interpolation=cv2.INTER_AREA,
        )

    # ── Step 3: Classify based on loaded model type ───────────────────────
    if not gesture_classifier.is_loaded:
        logger.debug("Gesture classifier not loaded — skipping prediction")
        return None

    if gesture_classifier.model_type == "task":
        label, confidence = gesture_classifier.predict_frame(frame_bgr)
    else:
        # Custom .pkl model: extract landmarks first
        landmark_vector = extract_landmarks(frame_bgr, model_path=settings.HAND_LANDMARKER_PATH)
        if landmark_vector is None:
            logger.debug("No hand landmarks detected in frame")
            return None
        label, confidence = gesture_classifier.predict(landmark_vector)

    if not label or label in ("unknown", "None", "Unrecognized"):
        return None

    if confidence < settings.GESTURE_CONFIDENCE_THRESHOLD:
        logger.debug(
            "Gesture '%s' confidence %.3f below threshold %.3f — suppressed",
            label,
            confidence,
            settings.GESTURE_CONFIDENCE_THRESHOLD,
        )
        return None

    logger.debug("Gesture detected: %s (confidence=%.3f)", label, confidence)

    return GesturePrediction(
        label=label,
        confidence=round(confidence, 4),
        timestamp=timestamp,
    )
