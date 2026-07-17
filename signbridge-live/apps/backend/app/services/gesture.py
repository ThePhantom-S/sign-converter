"""
GestureService — application-level service that manages the gesture
recognition lifecycle, stability filtering, and optional Gemini sentence building.

Features
--------
* Singleton pattern via ``gesture_service`` module-level instance.
* Stability filter: only emits a gesture after N consecutive identical predictions
  (reduces flicker in real-time streams).
* Gesture buffer: accumulates a rolling window of confirmed gestures to pass to
  Gemini for contextual sentence construction.
"""

from __future__ import annotations

import logging
from collections import deque
from pathlib import Path

from app.core.config import get_settings
from app.cv.detector import detect_sign_language
from app.cv.gesture_classifier import gesture_classifier
from app.schemas.gesture import GesturePrediction

logger = logging.getLogger(__name__)

# How many consecutive identical predictions are required before confirming
_STABILITY_WINDOW = 3

# Max gestures to keep in the rolling sentence buffer
_SENTENCE_BUFFER_SIZE = 20


class GestureService:
    """Singleton service for gesture recognition with stability filtering."""

    def __init__(self) -> None:
        self._pending_label: str = ""
        self._pending_count: int = 0
        self._last_confirmed: str = ""
        self._sentence_buffer: deque[str] = deque(maxlen=_SENTENCE_BUFFER_SIZE)
        self._loaded: bool = False

    # ------------------------------------------------------------------
    # Initialisation
    # ------------------------------------------------------------------

    def load_model(self, model_path: str | None = None) -> bool:
        """
        Load the gesture classifier model.

        Args:
            model_path: Override path. Falls back to ``settings.GESTURE_MODEL_PATH``.

        Returns:
            ``True`` if the model loaded successfully.
        """
        settings = get_settings()
        path = model_path or settings.GESTURE_MODEL_PATH
        self._loaded = gesture_classifier.load(Path(path))
        if self._loaded:
            logger.info("GestureService: model loaded from %s", path)
        else:
            logger.warning(
                "GestureService: no model loaded. Gesture recognition will be "
                "disabled until train_gesture_model.py is run."
            )
        return self._loaded

    @property
    def is_ready(self) -> bool:
        """True if the classifier model is loaded and ready."""
        return gesture_classifier.is_loaded

    @property
    def supported_gestures(self) -> list[str]:
        """List of gesture labels the loaded model can classify."""
        return gesture_classifier.classes

    # ------------------------------------------------------------------
    # Frame processing
    # ------------------------------------------------------------------

    async def process_frame(
        self, frame_base64: str, timestamp: float = 0.0
    ) -> GesturePrediction | None:
        """
        Process a single video frame and return a stable gesture prediction.

        Applies a stability filter: the same gesture must appear in
        ``_STABILITY_WINDOW`` consecutive frames before being emitted.
        Prevents one-off flickering predictions from reaching the client.

        Args:
            frame_base64: Base64-encoded JPEG/PNG from the browser extension.
            timestamp:    Client-side frame timestamp (seconds).

        Returns:
            A confirmed :class:`~app.schemas.gesture.GesturePrediction`, or
            ``None`` if no stable gesture was detected.
        """
        prediction = await detect_sign_language(frame_base64, timestamp)

        if prediction is None:
            # Reset stability counter on no-detection
            self._pending_label = ""
            self._pending_count = 0
            return None

        if prediction.label == self._pending_label:
            self._pending_count += 1
        else:
            # New candidate — reset counter
            self._pending_label = prediction.label
            self._pending_count = 1

        if self._pending_count >= _STABILITY_WINDOW:
            # Confirmed — emit only if it changed since last confirmed
            if prediction.label != self._last_confirmed:
                self._last_confirmed = prediction.label
                self._sentence_buffer.append(prediction.label)
                logger.info(
                    "Gesture confirmed: %s (confidence=%.3f)",
                    prediction.label,
                    prediction.confidence,
                )
                return prediction

        return None  # Still accumulating stability evidence

    # ------------------------------------------------------------------
    # Gemini sentence building (optional)
    # ------------------------------------------------------------------

    async def build_sentence(self) -> str | None:
        """
        Pass the accumulated gesture buffer to Gemini to form a natural sentence.

        Returns:
            A natural-language sentence, or ``None`` if Gemini is disabled or
            the buffer is empty.
        """
        settings = get_settings()
        if not settings.GEMINI_GESTURE_ENABLED:
            return None

        labels = list(self._sentence_buffer)
        if not labels:
            return None

        try:
            from app.ai.gemini import GeminiClient  # noqa: PLC0415

            client = GeminiClient()
            return await client.disambiguate_gestures(labels)
        except Exception as exc:
            logger.error("Gemini sentence building failed: %s", exc)
            return None

    def reset_sentence_buffer(self) -> None:
        """Clear the rolling sentence buffer (e.g., on new speaker turn)."""
        self._sentence_buffer.clear()
        self._last_confirmed = ""
        self._pending_label = ""
        self._pending_count = 0


# Module-level singleton
gesture_service = GestureService()
