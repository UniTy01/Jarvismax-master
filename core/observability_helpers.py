"""
JARVIS MAX — Lightweight Observability Helpers
================================================
Dependency-light utilities for timing, error categorization, and retries.

All functions are fail-open: they never crash the caller.
Zero external dependencies (stdlib only + structlog if available).
"""
from __future__ import annotations

import functools
import time
from typing import Any, Callable, TypeVar, ParamSpec

try:
    import structlog
    log = structlog.get_logger(__name__)
except ImportError:
    import logging
    log = logging.getLogger(__name__)


P = ParamSpec("P")
R = TypeVar("R")


# ═══════════════════════════════════════════════════════════════
# 1. TIMING DECORATOR
# ═══════════════════════════════════════════════════════════════

def timed(fn: Callable[P, R]) -> Callable[P, R]:
    """
    Decorator that logs execution time of sync functions.

    Logs: function_name, duration_ms, success/error.
    Fail-open: if logging fails, function still executes normally.

    Usage:
        @timed
        def my_function():
            ...
    """
    @functools.wraps(fn)
    def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
        t0 = time.monotonic()
        try:
            result = fn(*args, **kwargs)
            ms = int((time.monotonic() - t0) * 1000)
            try:
                log.debug("fn_timed", fn=fn.__name__, ms=ms, ok=True)
            except Exception:
                pass
            return result
        except Exception as e:
            ms = int((time.monotonic() - t0) * 1000)
            try:
                log.warning("fn_timed", fn=fn.__name__, ms=ms, ok=False, err=str(e)[:100])
            except Exception:
                pass
            raise
    return wrapper


def async_timed(fn: Callable) -> Callable:
    """
    Decorator that logs execution time of async functions.

    Usage:
        @async_timed
        async def my_function():
            ...
    """
    @functools.wraps(fn)
    async def wrapper(*args, **kwargs):
        t0 = time.monotonic()
        try:
            result = await fn(*args, **kwargs)
            ms = int((time.monotonic() - t0) * 1000)
            try:
                log.debug("fn_timed", fn=fn.__name__, ms=ms, ok=True)
            except Exception:
                pass
            return result
        except Exception as e:
            ms = int((time.monotonic() - t0) * 1000)
            try:
                log.warning("fn_timed", fn=fn.__name__, ms=ms, ok=False, err=str(e)[:100])
            except Exception:
                pass
            raise
    return wrapper


class Timer:
    """
    Context manager for timing blocks of code.

    Usage:
        with Timer("my_operation") as t:
            do_stuff()
        print(t.ms)  # elapsed milliseconds
    """
    def __init__(self, label: str = ""):
        self.label = label
        self.start: float = 0
        self.end: float = 0
        self.ms: int = 0

    def __enter__(self) -> "Timer":
        self.start = time.monotonic()
        return self

    def __exit__(self, *exc):
        self.end = time.monotonic()
        self.ms = int((self.end - self.start) * 1000)
        try:
            if exc[0] is not None:
                log.debug("timer", label=self.label, ms=self.ms, error=True)
            elif self.label:
                log.debug("timer", label=self.label, ms=self.ms)
        except Exception:
            pass
        return False


# ═══════════════════════════════════════════════════════════════
# 2. ERROR CATEGORIZATION
# ═══════════════════════════════════════════════════════════════

# Error category → exception types
_ERROR_CATEGORIES: dict[str, tuple[type, ...]] = {
    # Order matters: specific subclasses before generic parents.
    # FileNotFoundError/PermissionError are OSError subclasses — check first.
    "not_found":   (FileNotFoundError, ModuleNotFoundError),
    "permission":  (PermissionError,),
    "network":     (ConnectionError, TimeoutError, OSError),
    "type_error":  (TypeError, ValueError, AttributeError),
    "assertion":   (AssertionError,),
    "runtime":     (RuntimeError,),
    "import":      (ImportError,),
    "memory":      (MemoryError,),
    "keyboard":    (KeyboardInterrupt,),
}

# Keywords in error message → category
# Order matters: more specific categories first to avoid misclassification.
_ERROR_KEYWORDS: dict[str, list[str]] = {
    "quota":       ["quota", "rate limit", "too many requests", "429"],
    "auth":        ["unauthorized", "forbidden", "403", "401", "auth", "token expired"],
    "not_found":   ["not found", "404", "no such file"],
    "network":     ["timeout", "connection", "refused", "unreachable", "reset by peer",
                    "503", "502"],
    "syntax":      ["syntax error", "unexpected token", "invalid syntax"],
    "oom":         ["out of memory", "oom", "memory"],
}


def categorize_error(error: BaseException) -> str:
    """
    Categorize an error into a human-readable category.

    Returns one of: network, permission, not_found, type_error, assertion,
    runtime, import, memory, auth, quota, syntax, oom, unknown.
    """
    # Check by type first
    for category, types in _ERROR_CATEGORIES.items():
        if isinstance(error, types):
            return category

    # Check by message keywords
    msg = str(error).lower()
    for category, keywords in _ERROR_KEYWORDS.items():
        if any(kw in msg for kw in keywords):
            return category

    return "unknown"


def error_summary(error: BaseException) -> dict:
    """
    Structured error summary for logging and storage.

    Returns:
        {
            "type": "TimeoutError",
            "category": "network",
            "message": "Connection timed out",
            "retryable": True,
        }
    """
    category = categorize_error(error)
    retryable = category in ("network", "quota")
    return {
        "type": type(error).__name__,
        "category": category,
        "message": str(error)[:300],
        "retryable": retryable,
    }


# ═══════════════════════════════════════════════════════════════
# 3. RETRY WRAPPER (minimal)
# ═══════════════════════════════════════════════════════════════

def retry(
    max_attempts: int = 3,
    delay: float = 1.0,
    backoff: float = 2.0,
    retryable: tuple[type, ...] = (ConnectionError, TimeoutError, OSError),
) -> Callable:
    """
    Minimal retry decorator for sync functions.

    Only retries on specified exception types. Logs each attempt.
    Fail-open: if all retries fail, raises the last exception.

    Usage:
        @retry(max_attempts=3, delay=1.0)
        def fetch_data():
            ...
    """
    def decorator(fn: Callable[P, R]) -> Callable[P, R]:
        @functools.wraps(fn)
        def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
            last_error: BaseException | None = None
            for attempt in range(1, max_attempts + 1):
                try:
                    return fn(*args, **kwargs)
                except retryable as e:
                    last_error = e
                    if attempt < max_attempts:
                        wait = delay * (backoff ** (attempt - 1))
                        try:
                            log.info("retry", fn=fn.__name__, attempt=attempt,
                                     max=max_attempts, wait_s=round(wait, 2),
                                     err=str(e)[:80])
                        except Exception:
                            pass
                        time.sleep(wait)
                    else:
                        raise
                except Exception:
                    raise  # Non-retryable errors propagate immediately
            raise last_error  # type: ignore[misc]
        return wrapper
    return decorator


def async_retry(
    max_attempts: int = 3,
    delay: float = 1.0,
    backoff: float = 2.0,
    retryable: tuple[type, ...] = (ConnectionError, TimeoutError, OSError),
) -> Callable:
    """
    Minimal retry decorator for async functions.

    Usage:
        @async_retry(max_attempts=3, delay=1.0)
        async def fetch_data():
            ...
    """
    import asyncio

    def decorator(fn: Callable) -> Callable:
        @functools.wraps(fn)
        async def wrapper(*args, **kwargs):
            last_error: BaseException | None = None
            for attempt in range(1, max_attempts + 1):
                try:
                    return await fn(*args, **kwargs)
                except retryable as e:
                    last_error = e
                    if attempt < max_attempts:
                        wait = delay * (backoff ** (attempt - 1))
                        try:
                            log.info("async_retry", fn=fn.__name__, attempt=attempt,
                                     max=max_attempts, wait_s=round(wait, 2),
                                     err=str(e)[:80])
                        except Exception:
                            pass
                        await asyncio.sleep(wait)
                    else:
                        raise
                except Exception:
                    raise
            raise last_error  # type: ignore[misc]
        return wrapper
    return decorator
