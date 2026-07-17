#!/usr/bin/env python3
# Run this script via:  uv run python train_gesture_model.py
"""
train_gesture_model.py — Interactive gesture training CLI for SignBridge Live.

Uses the modern MediaPipe Tasks API (mediapipe 0.10+).
Requires models/hand_landmarker.task (downloaded automatically on first run).

Usage
-----
  # Train A–Z ASL fingerspelling (default)
  uv run python train_gesture_model.py

  # Quick test with a few labels
  uv run python train_gesture_model.py --labels A B C D E --samples 50

  # Custom output
  uv run python train_gesture_model.py --samples 100 --output models/my_model.pkl

  # Train from a pre-collected CSV (no webcam needed)
  uv run python train_gesture_model.py --dataset models/landmarks.csv

Controls (webcam mode)
----------------------
  SPACE  — capture one sample
  N      — skip to next label
  Q      — quit and save whatever has been collected

Requirements
------------
  uv add opencv-python mediapipe scikit-learn numpy
"""

from __future__ import annotations

import argparse
import csv
import logging
import os
import pickle
import sys
import time
import urllib.request
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)

# ── Defaults ──────────────────────────────────────────────────────────────────
DEFAULT_LABELS = list("ABCDEFGHIJKLMNOPQRSTUVWXYZ")
DEFAULT_SAMPLES = 100
DEFAULT_OUTPUT = Path(__file__).parent / "models" / "gesture_model.pkl"
HAND_LANDMARKER_URL = (
    "https://storage.googleapis.com/mediapipe-models/"
    "hand_landmarker/hand_landmarker/float16/1/hand_landmarker.task"
)
HAND_LANDMARKER_PATH = Path(__file__).parent / "models" / "hand_landmarker.task"


# ── Dependency check ──────────────────────────────────────────────────────────
def _check_deps():
    missing = []
    for import_name, pkg_name in {
        "cv2": "opencv-python",
        "mediapipe": "mediapipe",
        "sklearn": "scikit-learn",
        "numpy": "numpy",
    }.items():
        try:
            __import__(import_name)
        except ImportError:
            missing.append(pkg_name)

    if missing:
        logger.error("Missing packages: %s", ", ".join(missing))
        logger.error("Install via (from apps/backend/):")
        logger.error("  uv add %s", " ".join(missing))
        logger.error("Then re-run:  uv run python train_gesture_model.py")
        sys.exit(1)


# ── Download model if needed ──────────────────────────────────────────────────
def _ensure_landmarker_model():
    if HAND_LANDMARKER_PATH.exists():
        return
    HAND_LANDMARKER_PATH.parent.mkdir(parents=True, exist_ok=True)
    logger.info("Downloading hand_landmarker.task (~7 MB) …")
    try:
        urllib.request.urlretrieve(HAND_LANDMARKER_URL, HAND_LANDMARKER_PATH)
        logger.info("Saved to %s", HAND_LANDMARKER_PATH)
    except Exception as exc:
        logger.error("Failed to download hand_landmarker.task: %s", exc)
        logger.error("Manual download:")
        logger.error("  curl -L '%s' -o %s", HAND_LANDMARKER_URL, HAND_LANDMARKER_PATH)
        sys.exit(1)


# ── MediaPipe Tasks API landmarker ─────────────────────────────────────────────
def _build_landmarker():
    """Create a HandLandmarker using the modern Tasks API."""
    from mediapipe.tasks import python as mp_python
    from mediapipe.tasks.python import vision as mp_vision

    base_options = mp_python.BaseOptions(
        model_asset_path=str(HAND_LANDMARKER_PATH)
    )
    options = mp_vision.HandLandmarkerOptions(
        base_options=base_options,
        running_mode=mp_vision.RunningMode.IMAGE,
        num_hands=1,
        min_hand_detection_confidence=0.5,
        min_hand_presence_confidence=0.5,
    )
    return mp_vision.HandLandmarker.create_from_options(options)


def _extract_landmarks(frame_bgr, landmarker) -> list | None:
    """Extract + normalize 63-dim landmark vector from a BGR frame."""
    import cv2
    import mediapipe as mp
    import numpy as np

    frame_rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
    mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=frame_rgb)

    result = landmarker.detect(mp_image)
    if not result.hand_landmarks:
        return None

    hand = result.hand_landmarks[0]  # first hand
    raw = np.array([[lm.x, lm.y, lm.z] for lm in hand], dtype=np.float64)

    # Wrist-relative + scale normalize
    wrist = raw[0].copy()
    relative = raw - wrist
    scale = float(np.linalg.norm(relative[9]))  # wrist → middle-finger MCP
    if scale < 1e-6:
        return None

    relative /= scale
    return relative.flatten().astype("float32").tolist()


# ── Draw landmarks on frame (Tasks API version) ────────────────────────────────
def _draw_landmarks(frame, result):
    """Draw hand landmark dots and connections onto frame in-place."""
    import cv2
    h, w = frame.shape[:2]

    # MediaPipe Tasks hand connections (same topology as legacy API)
    CONNECTIONS = [
        (0,1),(1,2),(2,3),(3,4),           # thumb
        (0,5),(5,6),(6,7),(7,8),           # index
        (0,9),(9,10),(10,11),(11,12),      # middle
        (0,13),(13,14),(14,15),(15,16),    # ring
        (0,17),(17,18),(18,19),(19,20),    # pinky
        (5,9),(9,13),(13,17),              # palm
    ]

    if not result.hand_landmarks:
        return

    for hand in result.hand_landmarks:
        pts = [(int(lm.x * w), int(lm.y * h)) for lm in hand]
        for a, b in CONNECTIONS:
            cv2.line(frame, pts[a], pts[b], (0, 220, 100), 2)
        for pt in pts:
            cv2.circle(frame, pt, 4, (255, 255, 255), -1)
            cv2.circle(frame, pt, 4, (0, 150, 255), 1)


# ── Webcam collection ──────────────────────────────────────────────────────────
def collect_from_webcam(labels: list[str], samples_per_label: int) -> tuple[list, list]:
    """Interactive webcam-based landmark collection. Returns (X, y)."""
    import cv2

    X, y = [], []
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        logger.error("Cannot open webcam (device 0). Check camera permissions.")
        sys.exit(1)

    landmarker = _build_landmarker()

    for label_idx, label in enumerate(labels):
        label_samples = 0
        logger.info(
            "\n[%d/%d] Label: '%s'  |  Need %d samples  |  SPACE=capture  N=next  Q=quit",
            label_idx + 1, len(labels), label, samples_per_label,
        )

        # 3-second countdown
        t0 = time.time()
        while time.time() - t0 < 3:
            ret, frame = cap.read()
            if not ret:
                break
            frame = cv2.flip(frame, 1)
            secs_left = int(3 - (time.time() - t0)) + 1
            cv2.putText(frame, f"Label: '{label}'  Starting in {secs_left}s",
                        (20, 50), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 255, 255), 2)
            cv2.imshow("SignBridge — Gesture Trainer", frame)
            cv2.waitKey(1)

        while label_samples < samples_per_label:
            ret, frame = cap.read()
            if not ret:
                logger.warning("Webcam read failed")
                continue

            frame = cv2.flip(frame, 1)

            # Run detection for preview
            import mediapipe as mp
            frame_rgb = __import__("cv2").cvtColor(frame, __import__("cv2").COLOR_BGR2RGB)
            mp_img = mp.Image(image_format=mp.ImageFormat.SRGB, data=frame_rgb)
            result = landmarker.detect(mp_img)
            _draw_landmarks(frame, result)

            # HUD overlay
            cv2.rectangle(frame, (0, 0), (frame.shape[1], 65), (0, 0, 0), -1)
            cv2.putText(frame, f"Label: {label}  [{label_samples}/{samples_per_label}]",
                        (15, 35), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 255, 80), 2)
            cv2.putText(frame, "SPACE=capture   N=next   Q=quit",
                        (15, 58), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (180, 180, 180), 1)

            cv2.imshow("SignBridge — Gesture Trainer", frame)
            key = cv2.waitKey(1) & 0xFF

            if key == ord("q"):
                logger.info("Quit — saving collected data.")
                cap.release()
                cv2.destroyAllWindows()
                landmarker.close()
                return X, y

            elif key == ord("n"):
                logger.info("Skipping label '%s'", label)
                break

            elif key == ord(" "):
                vec = _extract_landmarks(frame, landmarker)
                if vec is None:
                    logger.warning("No hand detected — try again")
                    continue
                X.append(vec)
                y.append(label)
                label_samples += 1
                logger.info("  ✓ %d/%d for '%s'", label_samples, samples_per_label, label)

    cap.release()
    cv2.destroyAllWindows()
    landmarker.close()
    return X, y


# ── CSV helpers ────────────────────────────────────────────────────────────────
def load_from_csv(csv_path: Path) -> tuple[list, list]:
    import numpy as np
    X, y = [], []
    with csv_path.open() as fh:
        reader = csv.reader(fh)
        next(reader, None)  # skip header
        for row in reader:
            y.append(row[-1])
            X.append(np.array(row[:-1], dtype="float32"))
    logger.info("Loaded %d samples from %s", len(X), csv_path)
    return X, y


def save_dataset_csv(X: list, y: list, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="") as fh:
        writer = csv.writer(fh)
        writer.writerow([f"f{i}" for i in range(len(X[0]))] + ["label"])
        for vec, label in zip(X, y):
            writer.writerow(list(vec) + [label])
    logger.info("Dataset saved to %s", path)


# ── Training ───────────────────────────────────────────────────────────────────
def train_model(X: list, y: list, output_path: Path) -> None:
    import numpy as np
    from sklearn.ensemble import RandomForestClassifier
    from sklearn.metrics import accuracy_score, classification_report
    from sklearn.model_selection import train_test_split
    from sklearn.preprocessing import LabelEncoder

    X_arr = np.array(X, dtype="float32")
    le = LabelEncoder()
    y_enc = le.fit_transform(y)

    logger.info("Training — %d samples, %d classes: %s", len(X), len(le.classes_), list(le.classes_))

    X_train, X_test, y_train, y_test = train_test_split(
        X_arr, y_enc, test_size=0.2, random_state=42, stratify=y_enc
    )

    clf = RandomForestClassifier(n_estimators=200, random_state=42, n_jobs=-1)
    clf.fit(X_train, y_train)

    y_pred = clf.predict(X_test)
    acc = accuracy_score(y_test, y_pred)
    logger.info("Test accuracy: %.2f%%", acc * 100)
    print("\n" + classification_report(y_test, y_pred, target_names=le.classes_))

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("wb") as fh:
        pickle.dump({"model": clf, "label_encoder": le}, fh)

    logger.info("✅  Model saved → %s", output_path)
    logger.info("    Classes: %s", list(le.classes_))
    logger.info("    Accuracy: %.2f%%", acc * 100)
    logger.info("\nNext steps:")
    logger.info("  Start server: uv run uvicorn app.main:app --reload --port 8000")


# ── CLI ────────────────────────────────────────────────────────────────────────
def main():
    _check_deps()
    _ensure_landmarker_model()

    parser = argparse.ArgumentParser(
        description="SignBridge Live — Gesture Model Trainer (MediaPipe Tasks API)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--labels", nargs="+", default=DEFAULT_LABELS, metavar="LABEL",
                        help="Gesture labels (default: A-Z)")
    parser.add_argument("--samples", type=int, default=DEFAULT_SAMPLES, metavar="N",
                        help=f"Samples per label (default: {DEFAULT_SAMPLES})")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT, metavar="PATH",
                        help=f"Output .pkl path (default: {DEFAULT_OUTPUT})")
    parser.add_argument("--dataset", type=Path, default=None, metavar="CSV",
                        help="Load pre-existing landmarks CSV instead of webcam")
    parser.add_argument("--save-csv", type=Path, default=None, metavar="CSV",
                        help="Also save collected landmarks to CSV for later reuse")
    args = parser.parse_args()

    if args.dataset:
        if not args.dataset.exists():
            logger.error("Dataset not found: %s", args.dataset)
            sys.exit(1)
        X, y = load_from_csv(args.dataset)
    else:
        logger.info(
            "Webcam collection: %d labels × %d samples = %d total frames",
            len(args.labels), args.samples, len(args.labels) * args.samples,
        )
        X, y = collect_from_webcam(args.labels, args.samples)

    if not X:
        logger.error("No samples collected — aborting.")
        sys.exit(1)

    if args.save_csv:
        save_dataset_csv(X, y, args.save_csv)

    train_model(X, y, args.output)


if __name__ == "__main__":
    main()
