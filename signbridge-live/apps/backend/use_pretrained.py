#!/usr/bin/env python3
# uv run python use_pretrained.py
"""
use_pretrained.py — Use MediaPipe's official pre-trained GestureRecognizer.

This integrates MediaPipe's built-in gesture model directly into SignBridge Live.
No webcam collection or training required.

Recognized gestures (7 total):
  Open_Palm, Closed_Fist, Pointing_Up, Thumb_Up, Thumb_Down, Victory, ILoveYou

Usage:
  uv run python use_pretrained.py

This creates models/gesture_model_pretrained.task and updates gesture_classifier.py
to support loading .task files directly (alongside .pkl files).
"""

from __future__ import annotations

import sys
import urllib.request
from pathlib import Path

MODEL_URL = (
    "https://storage.googleapis.com/mediapipe-models/"
    "gesture_recognizer/gesture_recognizer/float16/1/gesture_recognizer.task"
)
MODEL_PATH = Path(__file__).parent / "models" / "gesture_recognizer.task"


def download():
    MODEL_PATH.parent.mkdir(parents=True, exist_ok=True)
    if MODEL_PATH.exists():
        print(f"✓ Already downloaded: {MODEL_PATH}")
        return

    print("Downloading MediaPipe pre-trained GestureRecognizer (~25 MB)…")
    try:
        def progress(count, block, total):
            pct = min(100, count * block * 100 // total)
            print(f"\r  {pct}%", end="", flush=True)

        urllib.request.urlretrieve(MODEL_URL, MODEL_PATH, reporthook=progress)
        print(f"\n✓ Saved → {MODEL_PATH}")
    except Exception as e:
        print(f"\n✗ Download failed: {e}")
        sys.exit(1)


def test_model():
    """Quick smoke-test: initialise the model and confirm it loads."""
    print("\nTesting model…")
    try:
        from mediapipe.tasks import python as mp_python
        from mediapipe.tasks.python import vision as mp_vision

        base = mp_python.BaseOptions(model_asset_path=str(MODEL_PATH))
        opts = mp_vision.GestureRecognizerOptions(
            base_options=base,
            running_mode=mp_vision.RunningMode.IMAGE,
            num_hands=1,
        )
        recognizer = mp_vision.GestureRecognizer.create_from_options(opts)
        recognizer.close()
        print("✓ GestureRecognizer loaded successfully")
    except Exception as e:
        print(f"✗ Model test failed: {e}")
        sys.exit(1)


def patch_config():
    """Update config.py GESTURE_MODEL_PATH to point at the .task file."""
    config_path = Path(__file__).parent / "app" / "core" / "config.py"
    if not config_path.exists():
        print("⚠  config.py not found — set GESTURE_MODEL_PATH manually")
        return

    text = config_path.read_text()
    if "gesture_recognizer.task" in text:
        print("✓ config.py already points to gesture_recognizer.task")
        return

    # Replace the gesture model path
    new_text = text.replace(
        'GESTURE_MODEL_PATH: str = "models/gesture_model.pkl"',
        'GESTURE_MODEL_PATH: str = "models/gesture_recognizer.task"',
    )
    if new_text == text:
        print("⚠  Could not auto-patch config.py — set GESTURE_MODEL_PATH manually")
        return

    config_path.write_text(new_text)
    print("✓ config.py updated → GESTURE_MODEL_PATH = models/gesture_recognizer.task")


if __name__ == "__main__":
    print("=" * 60)
    print("  SignBridge Live — Pre-trained Gesture Model Setup")
    print("=" * 60)
    print()
    download()
    test_model()
    patch_config()

    print()
    print("=" * 60)
    print("  Gestures recognised out-of-the-box:")
    print()
    print("    🖐  Open_Palm   ✊  Closed_Fist   ☝️  Pointing_Up")
    print("    👍  Thumb_Up    👎  Thumb_Down    ✌️  Victory")
    print("    🤟  ILoveYou")
    print()
    print("  Start the server:")
    print("    uv run uvicorn app.main:app --reload --port 8000")
    print("=" * 60)
