import os

import pytest
from fastapi.testclient import TestClient

os.environ.setdefault("REDIS_ENABLED", "false")
os.environ.setdefault("SUPABASE_ENABLED", "false")
os.environ.setdefault("RATE_LIMIT_ENABLED", "false")

from app.core.config import get_settings  # noqa: E402

get_settings.cache_clear()


@pytest.fixture
def client() -> TestClient:
    get_settings.cache_clear()
    from app.main import create_app

    return TestClient(create_app())
