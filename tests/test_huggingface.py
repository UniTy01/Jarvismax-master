"""
Tests — HuggingFace Integration
Couverture :
    1. test_image_generation_mocked    : mock httpx.AsyncClient.post → generate_image_hf() returns path
    2. test_stt_mocked                 : mock HF API → speech_to_text() returns string
    3. test_tts_mocked                 : mock HF API → _hf_tts() returns path
    4. test_embedding_provider_local   : EMBEDDING_PROVIDER=local → no HF call
    5. test_image_agent_registered     : "image-agent" in AgentCrew registry
"""
from __future__ import annotations

import os
import sys
import types
import tempfile
import asyncio
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


# ── Helpers ───────────────────────────────────────────────────

def _ensure_structlog():
    if "structlog" not in sys.modules:
        mock_sl = types.ModuleType("structlog")
        mock_sl.get_logger = lambda *a, **k: types.SimpleNamespace(
            debug=lambda *a, **k: None,
            info=lambda *a, **k: None,
            warning=lambda *a, **k: None,
            error=lambda *a, **k: None,
        )
        sys.modules["structlog"] = mock_sl


_ensure_structlog()


def _run(coro):
    """Run a coroutine synchronously (compatible with Python 3.10+)."""
    return asyncio.run(coro)


# ── Mock settings ─────────────────────────────────────────────

class _FakeSettings:
    huggingface_api_key = "hf_test_key"
    embedding_provider  = "local"
    workspace_dir       = tempfile.mkdtemp()

    def get_llm(self, role="default"):
        return None


# ══════════════════════════════════════════════════════════════
# TEST 1 — generate_image_hf mocked
# ══════════════════════════════════════════════════════════════

def test_image_generation_mocked():
    """generate_image_hf() should return a .png path when HF API succeeds."""
    _ensure_structlog()

    fake_image_bytes = b"\x89PNG\r\n\x1a\n" + b"\x00" * 64  # minimal PNG-like header

    mock_response = MagicMock()
    mock_response.content = fake_image_bytes
    mock_response.raise_for_status = MagicMock()

    mock_post = AsyncMock(return_value=mock_response)

    # Patch httpx.AsyncClient so it uses our mock
    with patch.dict(os.environ, {"HUGGINGFACE_API_KEY": "hf_test_key"}):
        with patch("httpx.AsyncClient") as mock_client_cls:
            mock_client = MagicMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client.post = mock_post
            mock_client_cls.return_value = mock_client

            from modules.multimodal.image import generate_image_hf
            result = _run(generate_image_hf("a beautiful sunset"))

    assert result is not None, "Expected a path, got None"
    assert result.endswith(".png"), f"Expected .png path, got: {result}"
    assert Path(result).exists(), f"File was not written: {result}"


# ══════════════════════════════════════════════════════════════
# TEST 2 — speech_to_text mocked (HF whisper path)
# ══════════════════════════════════════════════════════════════

def test_stt_mocked():
    """speech_to_text() should return a non-empty string via HF Whisper mock."""
    _ensure_structlog()

    fake_audio = b"RIFF" + b"\x00" * 40  # minimal WAV-like bytes

    mock_response = MagicMock()
    mock_response.json.return_value = {"text": "Bonjour le monde"}
    mock_response.raise_for_status = MagicMock()

    mock_post = AsyncMock(return_value=mock_response)

    with patch.dict(os.environ, {"OPENAI_API_KEY": "", "HUGGINGFACE_API_KEY": "hf_test_key"}):
        with patch("httpx.AsyncClient") as mock_client_cls:
            mock_client = MagicMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client.post = mock_post
            mock_client_cls.return_value = mock_client

            from modules.multimodal.voice import _hf_whisper
            result = _run(_hf_whisper(fake_audio))

    assert result is not None
    assert isinstance(result.text, str)
    assert len(result.text) > 0, "Expected non-empty transcript"
    assert "Bonjour" in result.text


# ══════════════════════════════════════════════════════════════
# TEST 3 — _hf_tts mocked
# ══════════════════════════════════════════════════════════════

def test_tts_mocked():
    """_hf_tts() should return a .flac path when HF API succeeds."""
    _ensure_structlog()

    fake_audio_bytes = b"fLaC" + b"\x00" * 64  # minimal FLAC-like header

    mock_response = MagicMock()
    mock_response.content = fake_audio_bytes
    mock_response.raise_for_status = MagicMock()

    mock_post = AsyncMock(return_value=mock_response)

    with patch.dict(os.environ, {"HUGGINGFACE_API_KEY": "hf_test_key"}):
        with patch("httpx.AsyncClient") as mock_client_cls:
            mock_client = MagicMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client.post = mock_post
            mock_client_cls.return_value = mock_client

            from modules.multimodal.voice import _hf_tts
            result = _run(_hf_tts("Bonjour le monde"))

    assert result is not None, "Expected a path, got None"
    assert result.endswith(".flac"), f"Expected .flac path, got: {result}"
    assert Path(result).exists(), f"File was not written: {result}"


# ══════════════════════════════════════════════════════════════
# TEST 4 — EMBEDDING_PROVIDER=local → no HF call
# ══════════════════════════════════════════════════════════════

def test_embedding_provider_local():
    """When EMBEDDING_PROVIDER=local, _encode_hf should not be called."""
    _ensure_structlog()

    with tempfile.TemporaryDirectory() as tmpdir:

        class _LocalSettings:
            huggingface_api_key = "hf_test_key"
            embedding_provider  = "local"
            workspace_dir       = tmpdir

        with patch.dict(os.environ, {"EMBEDDING_PROVIDER": "local"}):
            from memory.vector_memory import VectorMemory

            # Patch get_settings to return local-only settings
            with patch("memory.vector_memory.VectorMemory._get_embedding_provider", return_value="local"):
                vm = VectorMemory(_LocalSettings())

                hf_called = []

                def _track_hf_call(self, text):
                    hf_called.append(text)
                    return None

                original_hf = VectorMemory._encode_hf
                VectorMemory._encode_hf = _track_hf_call

                try:
                    vm._encode("test text")
                finally:
                    VectorMemory._encode_hf = original_hf

                assert len(hf_called) == 0, (
                    f"_encode_hf was called {len(hf_called)} time(s) "
                    f"despite EMBEDDING_PROVIDER=local"
                )


# ══════════════════════════════════════════════════════════════
# TEST 5 — "image-agent" in AgentCrew registry
# ══════════════════════════════════════════════════════════════

def test_image_agent_registered():
    """AgentCrew should have 'image-agent' in its registry."""
    _ensure_structlog()

    # Mock heavy dependencies so we can import AgentCrew without full setup
    for _mod_name in [
        "langchain_core",
        "langchain_core.messages",
        "langchain_openai",
        "langchain_anthropic",
        "langchain_google_genai",
        "langchain_ollama",
    ]:
        if _mod_name not in sys.modules:
            _m = types.ModuleType(_mod_name)
            if _mod_name == "langchain_core.messages":
                _m.SystemMessage = lambda content="": MagicMock(content=content)
                _m.HumanMessage  = lambda content="": MagicMock(content=content)
            sys.modules[_mod_name] = _m
            parts = _mod_name.split(".")
            if len(parts) > 1 and parts[0] in sys.modules:
                setattr(sys.modules[parts[0]], parts[-1], _m)

    class _MinimalSettings:
        huggingface_api_key = ""
        embedding_provider  = "local"
        workspace_dir       = tempfile.mkdtemp()
        browser_headless    = True
        browser_timeout     = 30000

        def get_llm(self, role="default"):
            return None

    # Patch _register_v2_agents and _init_tools to avoid heavy imports
    with patch("agents.crew.AgentCrew._register_v2_agents", return_value=None):
        with patch("agents.crew.AgentCrew._init_tools", return_value={}):
            from agents.crew import AgentCrew
            crew = AgentCrew(_MinimalSettings())

    assert "image-agent" in crew.registry, (
        f"'image-agent' not found in crew.registry. "
        f"Available agents: {list(crew.registry.keys())}"
    )
    agent = crew.registry["image-agent"]
    assert agent.role == "builder", f"Expected role='builder', got: {agent.role}"
