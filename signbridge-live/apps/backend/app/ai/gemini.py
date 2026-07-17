"""
Gemini AI client for SignBridge Live.

Provides:
  - GeminiClient.disambiguate_gestures()  — convert a gesture label sequence
    to a natural-language sentence using Gemini.
"""

from __future__ import annotations

import logging

from app.ai.prompts import GESTURE_DISAMBIGUATION_PROMPT
from app.core.config import get_settings

logger = logging.getLogger(__name__)


class GeminiClient:
    """Thin async wrapper around the google-generativeai SDK."""

    def __init__(self) -> None:
        self._settings = get_settings()
        self._client = None
        self._model = None
        self._init()

    def _init(self) -> None:
        """Lazily initialise the Gemini SDK."""
        if not self._settings.GEMINI_API_KEY:
            logger.warning(
                "GEMINI_API_KEY is not set — Gemini features are disabled."
            )
            return

        try:
            import google.generativeai as genai  # noqa: PLC0415

            genai.configure(api_key=self._settings.GEMINI_API_KEY)
            self._model = genai.GenerativeModel(
                model_name=self._settings.GEMINI_MODEL,
                generation_config={
                    "temperature": 0.2,
                    "top_p": 0.9,
                    "max_output_tokens": 256,
                },
            )
            logger.info(
                "GeminiClient initialised with model %s", self._settings.GEMINI_MODEL
            )
        except ImportError:
            logger.error(
                "google-generativeai is not installed. "
                "Run: uv add google-generativeai"
            )
        except Exception as exc:
            logger.error("GeminiClient init failed: %s", exc)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def disambiguate_gestures(self, labels: list[str]) -> str | None:
        """
        Send a sequence of gesture labels to Gemini and receive a natural sentence.

        Args:
            labels: Ordered list of predicted gesture labels, e.g.
                    ``["H", "E", "L", "L", "O"]`` or ``["HELLO", "THANK_YOU"]``.

        Returns:
            Translated natural-language text, or ``None`` on failure.
        """
        if self._model is None:
            logger.debug("Gemini model not available — skipping disambiguation")
            return None

        if not labels:
            return None

        label_str = " → ".join(labels)
        prompt = GESTURE_DISAMBIGUATION_PROMPT.format(labels=label_str)

        try:
            # google-generativeai 0.8+ uses async natively
            response = await self._model.generate_content_async(prompt)
            text = response.text.strip()
            logger.info(
                "Gemini gesture disambiguation: %s → '%s'", label_str, text
            )
            return text
        except Exception as exc:
            logger.error("Gemini generate_content_async failed: %s", exc)
            return None
