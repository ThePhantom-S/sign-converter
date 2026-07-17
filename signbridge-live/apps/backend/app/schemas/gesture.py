"""Pydantic schemas for gesture recognition."""
from pydantic import BaseModel, Field


class GesturePrediction(BaseModel):
    """A single gesture prediction from the CV pipeline."""

    label: str = Field(..., description="Predicted gesture label (e.g. ASL letter or word)")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Classifier confidence [0, 1]")
    timestamp: float = Field(default=0.0, description="Frame timestamp in seconds")


class VideoFramePayload(BaseModel):
    """Incoming video frame from the extension."""

    frame: str = Field(..., description="Base64-encoded image frame (JPEG/PNG)")
    timestamp: float = Field(default=0.0, description="Capture timestamp in seconds")


class GestureWebSocketResponse(BaseModel):
    """WebSocket response envelope for a gesture event."""

    type: str = "gesture"
    payload: GesturePrediction
