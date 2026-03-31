"""
kernel/events/ — Canonical event system.

All critical state transitions emit events through this interface.
Events enable: replay, audit, state reconstruction, observability.
"""
from kernel.events.canonical import (
    CANONICAL_EVENTS, KernelEventEmitter, get_kernel_emitter,
)

__all__ = ["CANONICAL_EVENTS", "KernelEventEmitter", "get_kernel_emitter"]
