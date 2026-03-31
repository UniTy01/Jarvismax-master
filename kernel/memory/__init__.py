# kernel/memory/ — Typed memory interfaces.
# K1 RULE: zero imports from core/ at module level.
from kernel.memory.interfaces import (
    MemoryInterface,
    get_memory,
    register_lesson_retrieve,
    register_execution_persist,
    register_execution_patterns,
    register_facade_store,   # Pass 19 — R6
    register_facade_search,  # Pass 19 — R6
)

__all__ = [
    "MemoryInterface",
    "get_memory",
    "register_lesson_retrieve",
    "register_execution_persist",
    "register_execution_patterns",
    "register_facade_store",
    "register_facade_search",
]
