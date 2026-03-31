"""Tests for core/validator.py — MissionValidator."""
import pytest
from unittest.mock import AsyncMock, MagicMock


def test_import():
    from core.validator import MissionValidator


@pytest.mark.asyncio
async def test_validate_no_tests_detected():
    from core.validator import MissionValidator
    terminal = AsyncMock()
    terminal.execute.return_value = (0, "file1.txt  file2.txt  README.md")
    validator = MissionValidator(terminal)
    ok, msg = await validator.validate()
    assert ok is True
    assert "manuelle" in msg.lower() or "aucun test" in msg.lower()


@pytest.mark.asyncio
async def test_validate_pytest_detected_success():
    from core.validator import MissionValidator
    terminal = AsyncMock()
    # First call: ls
    terminal.execute.side_effect = [
        (0, "main.py  tests/  requirements.txt"),
        (0, "3 passed, 0 failed"),
    ]
    validator = MissionValidator(terminal)
    ok, msg = await validator.validate()
    assert ok is True
    assert "réussie" in msg.lower() or "pytest" in msg.lower()


@pytest.mark.asyncio
async def test_validate_pytest_detected_failure():
    from core.validator import MissionValidator
    terminal = AsyncMock()
    terminal.execute.side_effect = [
        (0, "main.py  tests/  requirements.txt"),
        (1, "FAILED test_main.py::test_foo - AssertionError"),
    ]
    validator = MissionValidator(terminal)
    ok, msg = await validator.validate()
    assert ok is False
    assert "échec" in msg.lower() or "failed" in msg.lower()


@pytest.mark.asyncio
async def test_validate_npm_detected():
    from core.validator import MissionValidator
    terminal = AsyncMock()
    terminal.execute.side_effect = [
        (0, "index.js  package.json  node_modules/"),
        (0, "Tests passed"),
    ]
    validator = MissionValidator(terminal)
    ok, msg = await validator.validate()
    assert ok is True
