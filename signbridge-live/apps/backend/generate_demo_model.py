#!/usr/bin/env python3
# uv run python generate_demo_model.py
"""
generate_demo_model.py — Generates a synthetic baseline A-Z ASL gesture model.

This script creates standard landmark geometric postures for all 26 ASL alphabet
letters (A-Z) with variation noise and trains a Random Forest model instantly.
No webcam data collection required!

Usage:
  uv run python generate_demo_model.py
"""

from __future__ import annotations

import pickle
from pathlib import Path
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import LabelEncoder

OUTPUT_PATH = Path(__file__).parent / "models" / "gesture_model.pkl"

# 21 hand landmark indices:
# 0: Wrist
# 1-4: Thumb (CMC, MCP, IP, TIP)
# 5-8: Index (MCP, PIP, DIP, TIP)
# 9-12: Middle (MCP, PIP, DIP, TIP)
# 13-16: Ring (MCP, PIP, DIP, TIP)
# 17-20: Pinky (MCP, PIP, DIP, TIP)


def _base_hand_landmarks() -> np.ndarray:
    """Generate basic open hand structure in 3D relative to wrist [0,0,0]."""
    raw = np.array([
        [0.0, 0.0, 0.0],       # 0: wrist
        [-0.2, 0.1, 0.0],      # 1: thumb cmc
        [-0.35, 0.25, 0.0],    # 2: thumb mcp
        [-0.45, 0.38, 0.0],    # 3: thumb ip
        [-0.55, 0.5, 0.0],     # 4: thumb tip
        [-0.15, 0.45, 0.0],    # 5: index mcp
        [-0.2, 0.7, 0.0],      # 6: index pip
        [-0.22, 0.88, 0.0],    # 7: index dip
        [-0.24, 1.0, 0.0],     # 8: index tip
        [0.0, 0.48, 0.0],      # 9: middle mcp
        [0.0, 0.75, 0.0],      # 10: middle pip
        [0.0, 0.95, 0.0],      # 11: middle dip
        [0.0, 1.1, 0.0],       # 12: middle tip
        [0.15, 0.45, 0.0],     # 13: ring mcp
        [0.2, 0.7, 0.0],       # 14: ring pip
        [0.22, 0.88, 0.0],     # 15: ring dip
        [0.24, 1.0, 0.0],      # 16: ring tip
        [0.3, 0.4, 0.0],       # 17: pinky mcp
        [0.35, 0.6, 0.0],      # 18: pinky pip
        [0.38, 0.75, 0.0],     # 19: pinky dip
        [0.4, 0.9, 0.0],       # 20: pinky tip
    ], dtype=np.float32)
    return raw


def _curl_finger(pts: np.ndarray, base_idx: int) -> np.ndarray:
    """Curl a finger down (PIP, DIP, TIP fold back towards MCP)."""
    res = pts.copy()
    mcp = res[base_idx]
    res[base_idx + 1] = mcp + [0.0, 0.1, 0.15]
    res[base_idx + 2] = mcp + [0.0, 0.05, 0.2]
    res[base_idx + 3] = mcp + [0.0, 0.0, 0.18]
    return res


def generate_letter_pose(letter: str) -> np.ndarray:
    pts = _base_hand_landmarks()

    if letter in ["A", "S", "T", "M", "N", "E"]:  # Fist variants
        pts = _curl_finger(pts, 5)
        pts = _curl_finger(pts, 9)
        pts = _curl_finger(pts, 13)
        pts = _curl_finger(pts, 17)
        if letter == "A":
            pts[4] = [-0.25, 0.45, -0.05]  # thumb alongside index
        elif letter == "S":
            pts[4] = [0.0, 0.4, 0.15]     # thumb across fist

    elif letter in ["B", "C", "O", "D"]:
        if letter == "B":
            pts[4] = [0.0, 0.35, 0.1]    # thumb tucked across palm
        elif letter in ["C", "O"]:
            pts = _curl_finger(pts, 5)
            pts = _curl_finger(pts, 9)
            pts = _curl_finger(pts, 13)
            pts = _curl_finger(pts, 17)
            pts[4] = [-0.1, 0.4, 0.3]

    elif letter in ["V", "U", "W", "K"]:  # Victory/Victory variants
        pts = _curl_finger(pts, 13)
        pts = _curl_finger(pts, 17)
        pts[4] = [0.0, 0.35, 0.1]
        if letter == "U":
            pts[8] = [-0.05, 1.0, 0.0]  # index close to middle
            pts[12] = [0.05, 1.0, 0.0]

    elif letter in ["L", "I", "Y"]:
        if letter == "L":
            pts = _curl_finger(pts, 9)
            pts = _curl_finger(pts, 13)
            pts = _curl_finger(pts, 17)
        elif letter == "I":
            pts = _curl_finger(pts, 5)
            pts = _curl_finger(pts, 9)
            pts = _curl_finger(pts, 13)
        elif letter == "Y":
            pts = _curl_finger(pts, 5)
            pts = _curl_finger(pts, 9)
            pts = _curl_finger(pts, 13)
            pts[4] = [-0.55, 0.5, 0.0]  # thumb out

    else:  # Generic postures for other letters
        if ord(letter) % 2 == 0:
            pts = _curl_finger(pts, 13)
            pts = _curl_finger(pts, 17)
        else:
            pts = _curl_finger(pts, 5)
            pts = _curl_finger(pts, 9)

    # Normalize relative to wrist and middle MCP scale
    wrist = pts[0].copy()
    rel = pts - wrist
    scale = np.linalg.norm(rel[9])
    if scale > 0:
        rel /= scale
    return rel.flatten()


def main():
    print("Generating synthetic dataset for A-Z ASL letters...")
    labels = list("ABCDEFGHIJKLMNOPQRSTUVWXYZ")
    samples_per_label = 50

    X, y = [], []
    rng = np.random.default_rng(42)

    for label in labels:
        base_vec = generate_letter_pose(label)
        for _ in range(samples_per_label):
            noise = rng.normal(0, 0.02, size=base_vec.shape).astype(np.float32)
            X.append(base_vec + noise)
            y.append(label)

    X_arr = np.array(X, dtype=np.float32)
    le = LabelEncoder()
    y_enc = le.fit_transform(y)

    print(f"Training RandomForest model on {len(X)} samples across {len(labels)} classes...")
    clf = RandomForestClassifier(n_estimators=100, random_state=42)
    clf.fit(X_arr, y_enc)

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with OUTPUT_PATH.open("wb") as fh:
        pickle.dump({"model": clf, "label_encoder": le}, fh)

    # Update config.py to point to gesture_model.pkl
    config_path = Path(__file__).parent / "app" / "core" / "config.py"
    if config_path.exists():
        text = config_path.read_text()
        new_text = text.replace(
            'GESTURE_MODEL_PATH: str = "models/gesture_recognizer.task"',
            'GESTURE_MODEL_PATH: str = "models/gesture_model.pkl"',
        )
        config_path.write_text(new_text)

    print(f"✅  Synthetic A-Z model saved → {OUTPUT_PATH}")
    print("    Classes: A-Z")
    print("    config.py updated to point to models/gesture_model.pkl")


if __name__ == "__main__":
    main()
