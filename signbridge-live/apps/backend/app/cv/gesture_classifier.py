"""
Gesture classifier — supports both:
1. Custom trained scikit-learn models (.pkl files) using normalized 63-dim landmark vectors.
2. MediaPipe pre-trained Task models (.task files, e.g. gesture_recognizer.task) operating on raw BGR frames.
"""

from __future__ import annotations

import logging
import pickle
from pathlib import Path
from typing import Any

import numpy as np

logger = logging.getLogger(__name__)


class GestureClassifier:
    """
    Unified classifier supporting both custom scikit-learn (.pkl) models
    and MediaPipe GestureRecognizer (.task) models.
    """

    def __init__(self) -> None:
        self._model_type: str | None = None  # "pkl" or "task"
        self._model: Any = None
        self._label_encoder: Any = None
        self._classes: list[str] = []
        self._model_path: str = ""
        self._task_recognizer: Any = None

    def load(self, model_path: str | Path) -> bool:
        """
        Load a model from ``model_path`` (.pkl or .task).

        Returns:
            ``True`` on success, ``False`` on failure.
        """
        path = Path(model_path)
        if not path.exists():
            logger.warning(
                "Gesture model not found at %s — classifier disabled. "
                "Run train_gesture_model.py or use_pretrained.py.",
                path,
            )
            return False

        if path.suffix == ".task":
            return self._load_task_model(path)
        return self._load_pkl_model(path)

    def _load_task_model(self, path: Path) -> bool:
        try:
            from mediapipe.tasks import python as mp_python  # noqa: PLC0415
            from mediapipe.tasks.python import vision as mp_vision  # noqa: PLC0415

            base_options = mp_python.BaseOptions(model_asset_path=str(path))
            options = mp_vision.GestureRecognizerOptions(
                base_options=base_options,
                running_mode=mp_vision.RunningMode.IMAGE,
                num_hands=1,
            )
            self._task_recognizer = mp_vision.GestureRecognizer.create_from_options(options)
            self._model_type = "task"
            self._model_path = str(path)
            self._classes = ["Open_Palm", "Closed_Fist", "Pointing_Up", "Thumb_Up", "Thumb_Down", "Victory", "ILoveYou"]
            logger.info("MediaPipe GestureRecognizer (.task) loaded from %s", path)
            return True
        except Exception as exc:
            logger.error("Failed to load MediaPipe .task model from %s: %s", path, exc)
            return False

    def _load_pkl_model(self, path: Path) -> bool:
        try:
            with path.open("rb") as fh:
                payload = pickle.load(fh)  # noqa: S301

            if isinstance(payload, dict):
                self._model = payload["model"]
                self._label_encoder = payload.get("label_encoder")
                if self._label_encoder is not None:
                    self._classes = list(self._label_encoder.classes_)
                else:
                    self._classes = list(self._model.classes_)
            else:
                self._model = payload
                self._classes = list(payload.classes_)

            self._model_type = "pkl"
            self._model_path = str(path)
            logger.info(
                "Custom gesture model (.pkl) loaded from %s (%d classes: %s)",
                path,
                len(self._classes),
                self._classes,
            )
            return True
        except Exception as exc:
            logger.error("Failed to load gesture model from %s: %s", path, exc)
            return False

    @property
    def is_loaded(self) -> bool:
        return self._model_type is not None

    @property
    def model_type(self) -> str | None:
        return self._model_type

    def predict(self, landmark_vector: np.ndarray) -> tuple[str, float]:
        """
        Predict gesture label for a 63-dim landmark vector (for .pkl models).
        """
        if self._model_type != "pkl" or self._model is None:
            return "unknown", 0.0

        try:
            vec = np.array(landmark_vector, dtype=np.float32).reshape(1, -1)
            proba = self._model.predict_proba(vec)[0]
            class_idx = int(np.argmax(proba))
            confidence = float(proba[class_idx])
            label = self._classes[class_idx]
            return label, confidence
        except Exception as exc:
            logger.error("Gesture classifier predict() error: %s", exc)
            return "unknown", 0.0

    def predict_frame(self, frame_bgr: np.ndarray) -> tuple[str, float]:
        """
        Predict gesture label directly from a BGR frame (for .task models).
        """
        if self._model_type != "task" or self._task_recognizer is None:
            return "None", 0.0

        try:
            import cv2  # noqa: PLC0415
            import mediapipe as mp  # noqa: PLC0415

            frame_rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
            mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=frame_rgb)
            result = self._task_recognizer.recognize(mp_image)

            if result.gestures and len(result.gestures[0]) > 0:
                top_gesture = result.gestures[0][0]
                name = top_gesture.category_name
                score = float(top_gesture.score)
                if name and name != "None" and name != "Unrecognized":
                    return name, score

            return "None", 0.0
        except Exception as exc:
            logger.error("MediaPipe GestureRecognizer predict_frame() error: %s", exc)
            return "None", 0.0

    @property
    def classes(self) -> list[str]:
        return list(self._classes)

    def close(self):
        if self._task_recognizer is not None:
            self._task_recognizer.close()
            self._task_recognizer = None


# Module-level singleton
gesture_classifier = GestureClassifier()
