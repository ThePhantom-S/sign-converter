from collections.abc import AsyncGenerator

import redis.asyncio as aioredis
from redis.asyncio.client import Redis

from app.core.config import Settings, get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)


class RedisManager:
    """Manages the async Redis connection pool lifecycle."""

    def __init__(self, settings: Settings | None = None) -> None:
        self._settings = settings or get_settings()
        self._client: Redis | None = None

    @property
    def is_enabled(self) -> bool:
        return self._settings.REDIS_ENABLED

    @property
    def client(self) -> Redis | None:
        return self._client

    async def connect(self) -> None:
        if not self.is_enabled:
            logger.info("redis_disabled")
            return

        self._client = aioredis.from_url(
            self._settings.REDIS_URL,
            encoding="utf-8",
            decode_responses=True,
            socket_timeout=self._settings.REDIS_SOCKET_TIMEOUT,
            socket_connect_timeout=self._settings.REDIS_CONNECT_TIMEOUT,
        )
        await self._client.ping()
        logger.info("redis_connected", url=self._settings.REDIS_URL)

    async def disconnect(self) -> None:
        if self._client is not None:
            await self._client.aclose()
            self._client = None
            logger.info("redis_disconnected")

    async def ping(self) -> bool:
        if not self.is_enabled or self._client is None:
            return False
        await self._client.ping()
        return True


redis_manager = RedisManager()


async def get_redis() -> AsyncGenerator[Redis | None, None]:
    yield redis_manager.client
