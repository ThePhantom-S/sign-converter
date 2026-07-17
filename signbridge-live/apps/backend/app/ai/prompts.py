"""
AI prompt templates for SignBridge Live.
"""

# ---------------------------------------------------------------------------
# Gesture → Sentence disambiguation
# ---------------------------------------------------------------------------

GESTURE_DISAMBIGUATION_PROMPT = """You are an expert ASL (American Sign Language) interpreter assistant.

Below is a sequence of recognized ASL gesture labels captured in real-time from a video stream.
Each label is either:
  - A single letter (fingerspelling): "A", "B", "C" ... "Z"
  - A common sign word: "HELLO", "THANK_YOU", "YES", "NO", etc.

Gesture sequence: {labels}

Your task:
1. Interpret the sequence as natural English text.
2. For fingerspelled letter sequences, reconstruct the intended word (e.g. H-E-L-L-O → "Hello").
3. For sign words, translate them into a grammatically correct sentence.
4. Be concise — output ONLY the final translated text, no explanation, no markdown.

Translated text:"""


# ---------------------------------------------------------------------------
# Future prompts can be added here
# ---------------------------------------------------------------------------
