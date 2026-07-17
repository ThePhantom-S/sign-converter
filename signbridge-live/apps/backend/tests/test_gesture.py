"""
Unit tests for the gesture recognition pipeline.

Run with:  pytest tests/test_gesture.py -v
"""

from __future__ import annotations

import base64
import pickle
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import numpy as np
import pytest


# ── Fixtures ────────────────────────────────────────────────────────────────

@pytest.fixture()
def dummy_landmark_vector() -> np.ndarray:
    """A valid 63-element landmark vector (random, normalized)."""
    rng = np.random.default_rng(42)
    return rng.random(63).astype(np.float32)


@pytest.fixture()
def dummy_model_path(tmp_path: Path) -> Path:
    """Creates a minimal RandomForest pkl in a temp directory."""
    from sklearn.ensemble import RandomForestClassifier
    from sklearn.preprocessing import LabelEncoder

    X = np.random.default_rng(0).random((30, 63)).astype(np.float32)
    y = ["A"] * 10 + ["B"] * 10 + ["C"] * 10
    le = LabelEncoder()
    y_enc = le.fit_transform(y)

    clf = RandomForestClassifier(n_estimators=10, random_state=0)
    clf.fit(X, y_enc)

    path = tmp_path / "test_model.pkl"
    with path.open("wb") as fh:
        pickle.dump({"model": clf, "label_encoder": le}, fh)
    return path


@pytest.fixture()
def dummy_frame_b64() -> str:
    """A tiny 10×10 green JPEG frame as base64."""
    import cv2

    frame = np.zeros((10, 10, 3), dtype=np.uint8)
    frame[:] = (0, 200, 0)
    _, buf = cv2.imencode(".jpg", frame)
    return base64.b64encode(buf).decode()


# ── GestureClassifier tests ──────────────────────────────────────────────────

class TestGestureClassifier:
    def test_not_loaded_initially(self):
        from app.cv.gesture_classifier import GestureClassifier

        gc = GestureClassifier()
        assert not gc.is_loaded

    def test_load_missing_file_returns_false(self, tmp_path: Path):
        from app.cv.gesture_classifier import GestureClassifier

        gc = GestureClassifier()
        result = gc.load(tmp_path / "nonexistent.pkl")
        assert result is False
        assert not gc.is_loaded

    def test_load_valid_model(self, dummy_model_path: Path):
        from app.cv.gesture_classifier import GestureClassifier

        gc = GestureClassifier()
        result = gc.load(dummy_model_path)
        assert result is True
        assert gc.is_loaded
        assert set(gc.classes) == {"A", "B", "C"}

    def test_predict_returns_label_and_confidence(
        self, dummy_model_path: Path, dummy_landmark_vector: np.ndarray
    ):
        from app.cv.gesture_classifier import GestureClassifier

        gc = GestureClassifier()
        gc.load(dummy_model_path)
        label, confidence = gc.predict(dummy_landmark_vector)

        assert label in {"A", "B", "C"}
        assert 0.0 <= confidence <= 1.0

    def test_predict_when_not_loaded(self, dummy_landmark_vector: np.ndarray):
        from app.cv.gesture_classifier import GestureClassifier

        gc = GestureClassifier()
        label, confidence = gc.predict(dummy_landmark_vector)
        assert label == "unknown"
        assert confidence == 0.0


# ── Landmark normalization tests ─────────────────────────────────────────────

class TestLandmarks:
    def test_normalize_returns_63_elements(self):
        from app.cv.landmarks import _normalize_landmarks

        raw = np.random.default_rng(1).random((21, 3)).astype(np.float64)
        vec = _normalize_landmarks(raw)
        assert vec.shape == (63,)
        assert vec.dtype == np.float32

    def test_wrist_is_at_origin_after_normalize(self):
        from app.cv.landmarks import _normalize_landmarks

        raw = np.random.default_rng(2).random((21, 3)).astype(np.float64)
        raw[0] = [0.5, 0.5, 0.0]  # Set wrist to a known position
        vec = _normalize_landmarks(raw)
        # First landmark (wrist) should be ~[0,0,0] after subtraction
        wrist_vec = vec[:3]
        np.testing.assert_allclose(wrist_vec, [0.0, 0.0, 0.0], atol=1e-5)

    def test_degenerate_hand_returns_zeros(self):
        from app.cv.landmarks import _normalize_landmarks

        # All landmarks at the same point → scale = 0
        raw = np.zeros((21, 3), dtype=np.float64)
        vec = _normalize_landmarks(raw)
        assert np.all(vec == 0.0)


# ── Detector tests ───────────────────────────────────────────────────────────

class TestDetector:
    @pytest.mark.asyncio
    async def test_empty_frame_returns_none(self):
        from app.cv.detector import detect_sign_language

        result = await detect_sign_language("")
        assert result is None

    @pytest.mark.asyncio
    async def test_gesture_disabled_returns_none(self, dummy_frame_b64: str):
        with patch("app.cv.detector.get_settings") as mock_settings:
            mock_settings.return_value.GESTURE_ENABLED = False
            from app.cv.detector import detect_sign_language

            result = await detect_sign_language(dummy_frame_b64)
            assert result is None


# ── GestureService tests ──────────────────────────────────────────────────────

class TestGestureService:
    def test_not_ready_without_model(self):
        from app.services.gesture import GestureService

        svc = GestureService()
        assert not svc.is_ready

    @pytest.mark.asyncio
    async def test_stability_filter_suppresses_single_prediction(
        self, dummy_model_path: Path
    ):
        """A gesture appearing once should NOT be emitted (stability=3)."""
        from app.services.gesture import GestureService

        svc = GestureService()
        svc.load_model(str(dummy_model_path))

        with patch("app.services.gesture.detect_sign_language", new_callable=AsyncMock) as mock_detect:
            from app.schemas.gesture import GesturePrediction

            mock_detect.return_value = GesturePrediction(
                label="A", confidence=0.9, timestamp=1.0
            )
            result = await svc.process_frame("dummy", 1.0)

        assert result is None  # Only 1 frame — below stability threshold

    @pytest.mark.asyncio
    async def test_stability_filter_emits_after_three_frames(
        self, dummy_model_path: Path
    ):
        """The same gesture appearing 3+ times should be emitted."""
        from app.schemas.gesture import GesturePrediction
        from app.services.gesture import GestureService

        svc = GestureService()
        svc.load_model(str(dummy_model_path))

        prediction = GesturePrediction(label="B", confidence=0.85, timestamp=2.0)

        with patch("app.services.gesture.detect_sign_language", new_callable=AsyncMock) as mock_detect:
            mock_detect.return_value = prediction
            results = [await svc.process_frame("dummy", 2.0) for _ in range(3)]

        assert results[0] is None
        assert results[1] is None
        assert results[2] is not None
        assert results[2].label == "B"

    def test_reset_clears_buffer(self):
        from app.services.gesture import GestureService

        svc = GestureService()
        svc._sentence_buffer.append("A")
        svc._sentence_buffer.append("B")
        svc.reset_sentence_buffer()
        assert len(svc._sentence_buffer) == 0
