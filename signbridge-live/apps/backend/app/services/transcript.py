import logging
from typing import Any

from app.core.supabase import supabase_manager

logger = logging.getLogger(__name__)

async def save_transcript(
    meeting_id: str, speaker: str, text: str, is_final: bool = True
) -> dict[str, Any] | None:
    """Saves a transcription slice to the Supabase database if enabled."""
    if not supabase_manager.is_enabled or not supabase_manager.client:
        logger.debug("Supabase not enabled; skipping transcript save.")
        return None

    try:
        data = {
            "meeting_id": meeting_id,
            "speaker": speaker,
            "text": text,
            "is_final": is_final
        }
        # Run synchronous Supabase client insert in executor if needed, or direct call
        response = supabase_manager.client.table("transcripts").insert(data).execute()
        return response.data
    except Exception as exc:
        logger.warning(f"Failed to save transcript to Supabase: {exc}")
        return None
