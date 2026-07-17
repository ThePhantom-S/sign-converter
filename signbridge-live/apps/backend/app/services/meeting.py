import logging
from typing import Any

from app.core.supabase import supabase_manager

logger = logging.getLogger(__name__)

async def create_meeting(meeting_code: str, title: str) -> dict[str, Any] | None:
    """Registers a new active Google Meet session in Supabase."""
    if not supabase_manager.is_enabled or not supabase_manager.client:
        return None

    try:
        data = {
            "meeting_code": meeting_code,
            "title": title,
            "status": "ACTIVE"
        }
        # Check if meeting already exists and is active, otherwise insert
        response = supabase_manager.client.table("meetings").insert(data).execute()
        return response.data
    except Exception as exc:
        logger.warning(f"Failed to register meeting in Supabase: {exc}")
        return None

async def close_meeting(meeting_code: str) -> dict[str, Any] | None:
    """Marks a meeting status as ENDED in Supabase."""
    if not supabase_manager.is_enabled or not supabase_manager.client:
        return None

    try:
        response = supabase_manager.client.table("meetings")\
            .update({"status": "ENDED"})\
            .eq("meeting_code", meeting_code)\
            .execute()
        return response.data
    except Exception as exc:
        logger.warning(f"Failed to close meeting in Supabase: {exc}")
        return None
