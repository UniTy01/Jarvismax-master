"""
JARVIS MAX — SafeTool Wrapper (Phase 4)
========================================
Enveloppe sécurisée pour l'exécution de tous les outils externes.

Garanties :
    - Jamais de crash du main loop (try/catch universel)
    - Résultat toujours structuré (ToolResult)
    - Timeout par outil (configurable)
    - Retry automatique si TRANSIENT failure
    - Logging structuré à chaque appel

Usage (sync) :
    result = safe_call(my_tool_fn, arg1, arg2, tool_name="my_tool")

Usage (async) :
    result = await safe_call_async(my_async_fn, arg1, timeout_s=30.0)

Usage (decorator) :
    @safe_tool(timeout_s=45.0, max_retries=2)
    async def my_agent_tool(query: str) -> str:
        ...
"""
from __future__ import annotations

import asyncio
import functools
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Awaitable, TypeVar

import structlog

from executor.mission_result import classify_failure, FailureClass
from executor.retry_policy import is_retryable, RetryPolicy, DEFAULT_POLICY, compute_delay

log = structlog.get_logger(__name__)

T = TypeVar("T")

# Default timeouts per tool category
TOOL_TIMEOUTS: dict[str, float] = {
    "llm":        90.0,
    "web_search": 30.0,
    "file_io":    15.0,
    "database":   20.0,
    "agent":      120.0,
    "default":    45.0,
}


# ─────────────────────────────────────────────────────────────────────────────
# ToolResult
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class ToolResult:
    """
    Résultat structuré d'un appel outil.
    Toujours retourné — jamais d'exception levée vers l'appelant.
    """
    tool_name:     str
    success:       bool
    output:        Any          = None
    error:         str          = ""
    failure_class: FailureClass = FailureClass.UNKNOWN
    retryable:     bool         = False
    duration_ms:   int          = 0
    attempts:      int          = 1
    fallback_used: bool         = False
    metadata:      dict         = field(default_factory=dict)

    @property
    def output_str(self) -> str:
        """Safe string conversion of output."""
        if self.output is None:
            return ""
        return str(self.output)[:4000]

    def to_dict(self) -> dict:
        return {
            "tool_name":    self.tool_name,
            "success":      self.success,
            "output":       self.output_str[:500],
            "error":        self.error,
            "failure_class": self.failure_class.value,
            "retryable":    self.retryable,
            "duration_ms":  self.duration_ms,
            "attempts":     self.attempts,
        }

    @classmethod
    def from_error(
        cls,
        tool_name: str,
        error:     Exception | str,
        attempts:  int = 1,
    ) -> "ToolResult":
        # Include type name so TimeoutError/"" still classifies correctly
        if isinstance(error, Exception):
            err_str = (type(error).__name__ + " " + str(error)).strip()[:300]
        else:
            err_str = str(error)[:300]
        fc      = classify_failure(err_str)
        return cls(
            tool_name     = tool_name,
            success       = False,
            error         = err_str,
            failure_class = fc,
            retryable     = fc == FailureClass.TRANSIENT,
            attempts      = attempts,
        )


# ─────────────────────────────────────────────────────────────────────────────
# Core wrappers
# ─────────────────────────────────────────────────────────────────────────────

def safe_call(
    fn:          Callable,
    *args,
    tool_name:   str   = "",
    timeout_s:   float = 0.0,
    fallback:    Any   = None,
    **kwargs,
) -> ToolResult:
    """
    Synchronous safe tool call.
    Never raises — always returns ToolResult.
    """
    name = tool_name or getattr(fn, "__name__", "unknown_tool")
    t0   = time.monotonic()

    try:
        result = fn(*args, **kwargs)
        ms     = int((time.monotonic() - t0) * 1000)
        log.debug("tool.call.ok", tool=name, duration_ms=ms)
        return ToolResult(tool_name=name, success=True, output=result, duration_ms=ms)

    except Exception as e:
        ms  = int((time.monotonic() - t0) * 1000)
        fc  = classify_failure(e)
        log.warning("tool.call.error", tool=name, error=str(e)[:100],
                    failure_class=fc.value, duration_ms=ms)
        tr = ToolResult.from_error(name, e)
        tr.duration_ms = ms
        if fallback is not None:
            tr.output       = fallback
            tr.fallback_used = True
        return tr


async def safe_call_async(
    fn:          Callable[..., Awaitable[T]],
    *args,
    tool_name:   str   = "",
    timeout_s:   float = 0.0,
    max_retries: int   = 1,
    retry_policy: RetryPolicy | None = None,
    fallback:    Any   = None,
    **kwargs,
) -> ToolResult:
    """
    Async safe tool call with timeout + retry.
    Never raises — always returns ToolResult.

    Retry only on TRANSIENT failures (timeout, network, rate limit).
    """
    name    = tool_name or getattr(fn, "__name__", "unknown_tool")
    policy  = retry_policy or DEFAULT_POLICY
    timeout = timeout_s or TOOL_TIMEOUTS.get("default", 45.0)
    t0      = time.monotonic()
    attempt = 0

    last_err: Exception | None = None

    while attempt <= max_retries:
        attempt += 1
        try:
            if timeout > 0:
                raw = await asyncio.wait_for(fn(*args, **kwargs), timeout=timeout)
            else:
                raw = await fn(*args, **kwargs)

            ms = int((time.monotonic() - t0) * 1000)
            log.debug("tool.async.ok", tool=name, duration_ms=ms, attempt=attempt)
            return ToolResult(
                tool_name   = name,
                success     = True,
                output      = raw,
                duration_ms = ms,
                attempts    = attempt,
            )

        except asyncio.TimeoutError as e:
            last_err = e
            ms = int((time.monotonic() - t0) * 1000)
            log.warning("tool.async.timeout", tool=name, attempt=attempt,
                        timeout_s=timeout, duration_ms=ms)
            if attempt > max_retries:
                break
            delay = compute_delay(attempt, policy)
            await asyncio.sleep(delay)

        except Exception as e:
            last_err = e
            ms = int((time.monotonic() - t0) * 1000)
            fc = classify_failure(e)
            log.warning("tool.async.error", tool=name, attempt=attempt,
                        failure_class=fc.value, error=str(e)[:80], duration_ms=ms)
            if fc != FailureClass.TRANSIENT or attempt > max_retries:
                break
            delay = compute_delay(attempt, policy)
            await asyncio.sleep(delay)

    # All attempts exhausted
    ms = int((time.monotonic() - t0) * 1000)
    tr = ToolResult.from_error(name, last_err or Exception("unknown"), attempts=attempt)
    tr.duration_ms = ms
    if fallback is not None:
        tr.output       = fallback
        tr.fallback_used = True
    return tr


# ─────────────────────────────────────────────────────────────────────────────
# Decorator
# ─────────────────────────────────────────────────────────────────────────────

def safe_tool(
    timeout_s:   float = 45.0,
    max_retries: int   = 1,
    fallback:    Any   = None,
    tool_name:   str   = "",
):
    """
    Decorator that wraps an async function with safe_call_async.

    @safe_tool(timeout_s=30.0, max_retries=2)
    async def search_web(query: str) -> str:
        ...

    result = await search_web("AI trends")
    # result is always ToolResult, never raises
    """
    def decorator(fn: Callable[..., Awaitable[T]]):
        name = tool_name or fn.__name__

        @functools.wraps(fn)
        async def wrapper(*args, **kwargs) -> ToolResult:
            return await safe_call_async(
                fn,
                *args,
                tool_name   = name,
                timeout_s   = timeout_s,
                max_retries = max_retries,
                fallback    = fallback,
                **kwargs,
            )

        wrapper._is_safe_tool = True
        wrapper._original_fn  = fn
        return wrapper

    return decorator
