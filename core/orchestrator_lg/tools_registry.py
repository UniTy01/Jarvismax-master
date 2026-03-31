"""
LangChain tool wrappers for JarvisMax.
Wraps existing tool implementations as LangChain BaseTool.
Fail-open: returns empty list if langchain_core not available.
"""
import logging
from typing import List

logger = logging.getLogger(__name__)

_tools: List = []

try:
    from langchain_core.tools import tool as lc_tool

    @lc_tool
    def shell_execution(command: str) -> str:
        """Execute a shell command safely via core tools."""
        try:
            from core.tools.dev_tools import run_shell_command
            return run_shell_command(command)
        except Exception as e:
            return f"Error: {e}"

    @lc_tool
    def python_execution(code: str) -> str:
        """Execute Python code in a sandboxed environment."""
        try:
            from core.tools.dev_tools import run_python_code
            return run_python_code(code)
        except Exception as e:
            return f"Error: {e}"

    @lc_tool
    def vector_search(query: str) -> str:
        """Search the knowledge base for relevant context."""
        try:
            from core.knowledge.pattern_detector import search_similar_patterns
            results = search_similar_patterns(query)
            return str(results) if results else "No results found."
        except Exception as e:
            return f"Error: {e}"

    @lc_tool
    def file_read(path: str) -> str:
        """Read a file from the workspace (capped at 4000 chars)."""
        try:
            import os
            safe_path = os.path.join("workspace", os.path.basename(path))
            with open(safe_path, "r", encoding="utf-8") as f:
                return f.read()[:4000]
        except Exception as e:
            return f"Error: {e}"

    @lc_tool
    def web_research(query: str) -> str:
        """Perform web research via the web_research_tool."""
        try:
            from core.tools.web_research_tool import web_search
            return web_search(query)
        except Exception as e:
            return f"Error: {e}"

    @lc_tool
    def memory_lookup(key: str) -> str:
        """Look up a stored solution from memory."""
        try:
            from core.tools.memory_toolkit import memory_lookup_solution
            return memory_lookup_solution(key) or "No entry found."
        except Exception as e:
            return f"Error: {e}"

    _tools = [shell_execution, python_execution, vector_search, file_read, web_research, memory_lookup]
    logger.info("[LangGraph:tools] %d tools registered", len(_tools))

except ImportError as e:
    logger.warning("[LangGraph:tools] langchain_core not available: %s", e)


def get_tools() -> List:
    """Return the registered LangChain tool list."""
    return _tools
