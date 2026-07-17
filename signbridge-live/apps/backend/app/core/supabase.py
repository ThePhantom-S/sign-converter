from supabase import Client, create_client

from app.core.config import Settings, get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)


class SupabaseManager:
    """Manages the Supabase client lifecycle."""

    def __init__(self, settings: Settings | None = None) -> None:
        self._settings = settings or get_settings()
        self._client: Client | None = None

    @property
    def is_enabled(self) -> bool:
        return self._settings.SUPABASE_ENABLED

    @property
    def is_configured(self) -> bool:
        return self._settings.supabase_configured

    @property
    def client(self) -> Client | None:
        return self._client

    def connect(self) -> None:
        if not self.is_enabled:
            logger.info("supabase_disabled")
            return

        if not self.is_configured:
            logger.warning(
                "supabase_not_configured",
                message="SUPABASE_URL and SUPABASE_KEY are required when enabled",
            )
            return

        self._client = create_client(
            self._settings.SUPABASE_URL,
            self._settings.SUPABASE_KEY,
        )
        logger.info("supabase_connected", url=self._settings.SUPABASE_URL)

    def disconnect(self) -> None:
        self._client = None
        logger.info("supabase_disconnected")

    async def ping(self) -> bool:
        if not self.is_enabled or not self.is_configured or self._client is None:
            return False

        self._client.table("meetings").select("id").limit(1).execute()
        return True


supabase_manager = SupabaseManager()


def get_supabase() -> Client | None:
    return supabase_manager.client
