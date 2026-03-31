"""Tool Intelligence Layer V1 — fail-open, feature flag USE_TOOL_INTELLIGENCE."""
import os
_ENABLED = os.getenv("USE_TOOL_INTELLIGENCE", "false").lower() == "true"

def is_enabled() -> bool:
    return _ENABLED

# Re-export selector components for convenient imports
from core.tool_intelligence.selector import (
    ToolSelector,
    ToolMetadata,
    ToolRecommendation,
    get_tool_selector,
)

# Backwards-compatible alias
get_tool_intelligence = get_tool_selector
ToolIntelligence = ToolSelector
