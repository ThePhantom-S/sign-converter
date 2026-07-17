"""
MediaPipe Hands landmark extraction — using the modern Tasks API (mediapipe 0.10+).

The legacy mp.solutions.hands API was fully removed in mediapipe 0.10.x.
This module uses mediapipe.tasks.python.vision.HandLandmarker instead.

Requires:  models/hand_landmarker.task  (downloaded via Makefile / setup)
Download:  curl -L https://storage.googleapis.com/mediapipe-models/hand_landmarker/hand_landmarker/float16/1/hand_landmarker.task -o models/hand_landmarker.task

Normalization strategy (best-practice from gesture recognition research):
  1. Wrist-relative translation  → subtract landmark[0] from all 21 landmarks
  2. Scale normalization          → divide by wrist→middle-finger-MCP distance
  3. Flatten                      → 63-dim float32 vector [x0,y0,z0, ..., x20,y20,z20]
"""

from __future__ import annotations

import logging
from pathlib import Path

import numpy as np

logger = logging.getLogger(__name__)

_N_LANDMARKS = 21
_FEATURE_DIM = _N_LANDMARKS * 3  # 63
_WRIST_IDX = 0
_MIDDLE_MCP_IDX = 9  # wrist → middle-finger MCP used for scale

# Cached landmarker instance
_landmarker = None
_model_path: str = ""


def _get_landmarker(model_path: str = "models/hand_landmarker.task"):
    """Return a cached MediaPipe HandLandmarker instance (lazy-init)."""
    global _landmarker, _model_path

    if _landmarker is not None:
        return _landmarker

    task_path = Path(model_path)
    if not task_path.exists():
        logger.error(
            "MediaPipe hand_landmarker.task not found at '%s'. "
            "Download it with:\n"
            "  curl -L https://storage.googleapis.com/mediapipe-models/"
            "hand_landmarker/hand_landmarker/float16/1/hand_landmarker.task "
            "-o %s",
            task_path,
            task_path,
        )
        return None

    try:
        from mediapipe.tasks import python as mp_python  # noqa: PLC0415
        from mediapipe.tasks.python import vision as mp_vision  # noqa: PLC0415

        base_options = mp_python.BaseOptions(model_asset_path=str(task_path))
        options = mp_vision.HandLandmarkerOptions(
            base_options=base_options,
            running_mode=mp_vision.RunningMode.IMAGE,
            num_hands=1,
            min_hand_detection_confidence=0.5,
            min_hand_presence_confidence=0.5,
            min_tracking_confidence=0.5,
        )
        _landmarker = mp_vision.HandLandmarker.create_from_options(options)
        _model_path = str(task_path)
        logger.info("MediaPipe HandLandmarker initialised from %s", task_path)
    except ImportError as exc:
        logger.error("mediapipe.tasks not available: %s", exc)
    except Exception as exc:
        logger.error("HandLandmarker init failed: %s", exc)

    return _landmarker


def _normalize_landmarks(raw: np.ndarray) -> np.ndarray:
    """
    Normalize a (21, 3) array to a wrist-relative, scale-invariant (63,) vector.

    Args:
        raw: Shape (21, 3) float array of [x, y, z] normalized image coordinates.

    Returns:
        Flat (63,) float32 vector or zeros on degenerate input.
    """
    wrist = raw[_WRIST_IDX].copy()
    relative = raw - wrist  # translate: wrist at origin

    scale = float(np.linalg.norm(relative[_MIDDLE_MCP_IDX]))
    if scale < 1e-6:
        logger.debug("Degenerate hand scale — returning zero vector")
        return np.zeros(_FEATURE_DIM, dtype=np.float32)

    relative /= scale  # scale-normalize
    return relative.flatten().astype(np.float32)


def extract_landmarks(
    frame_bgr: np.ndarray,
    model_path: str = "models/hand_landmarker.task",
) -> np.ndarray | None:
    """
    Run MediaPipe HandLandmarker on a BGR frame and return a normalized vector.

    Args:
        frame_bgr: BGR uint8 numpy array (as produced by OpenCV).
        model_path: Path to hand_landmarker.task relative to cwd.

    Returns:
        A (63,) float32 numpy array on success, or ``None`` if no hand found.
    """
    import cv2  # noqa: PLC0415
    import mediapipe as mp  # noqa: PLC0415

    landmarker = _get_landmarker(model_path)
    if landmarker is None:
        return None

    # Convert BGR → RGB and wrap in MediaPipe Image
    frame_rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
    mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=frame_rgb)

    try:
        result = landmarker.detect(mp_image)
    except Exception as exc:
        logger.error("HandLandmarker.detect() failed: %s", exc)
        return None

    if not result.hand_landmarks:
        return None  # no hand detected

    # Use first detected hand — list of NormalizedLandmark objects
    hand = result.hand_landmarks[0]
    raw = np.array([[lm.x, lm.y, lm.z] for lm in hand], dtype=np.float64)

    return _normalize_landmarks(raw)


def close_hands():
    """Release the HandLandmarker instance (call on app shutdown)."""
    global _landmarker
    if _landmarker is not None:
        _landmarker.close()
        _landmarker = None
        logger.info("MediaPipe HandLandmarker released")
