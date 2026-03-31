"""
conftest.py — JarvisMax test configuration.

1. Pre-imports core.state so that test files using
   sys.modules.setdefault("core.state", MagicMock()) cannot overwrite it.
2. Ensures a fresh event loop for each test (pytest-asyncio asyncio_mode=auto
   closes loops after async tests, breaking sync tests that call
   asyncio.get_event_loop().run_until_complete()).
"""
import asyncio
import pytest

# ── Pre-load key modules so test-level mocks cannot overwrite them ──────────
# Tests that do sys.modules.setdefault("some.module", MagicMock()) can only
# install their mock if the real module is NOT already in sys.modules.
# By importing here (conftest is collected before test files), we protect them.
for _preload in [
    "core.state",
    "langchain_core",
    "langchain_core.language_models",
    "langchain_core.language_models.chat_models",
    "langchain_core.messages",
    "langchain_core.prompts",
    "langchain_core.outputs",
    "langchain_core.callbacks",
    "langchain_core.callbacks.manager",
    "fastapi",
    "fastapi.responses",
    "structlog",
]:
    try:
        __import__(_preload)
    except Exception:
        pass  # If missing, tests that need it will handle it themselves


@pytest.fixture(autouse=True)
def _ensure_event_loop():
    """Create a fresh event loop before each test if none exists or it's closed."""
    try:
        loop = asyncio.get_event_loop()
        if loop.is_closed():
            raise RuntimeError("closed")
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    yield
    # Do not close here — let pytest-asyncio manage its own loops.
    # Only clean up loops we created (i.e., not the pytest-asyncio-managed ones).
