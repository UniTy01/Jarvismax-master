"""
JARVIS MAX — Business Agent Tool Bindings
============================================
Practical tools for business agents. Wraps existing tooling with
business-specific interfaces. No uncontrolled external dependencies.

Available tools:
  - structured_intake: form-like input collection
  - markdown_generator: professional document generation
  - html_generator: HTML content generation
  - email_draft: email composition (draft only, no send)
  - crm_store: lightweight CRM-like structured storage
  - quote_formatter: professional quote/estimate formatting
  - file_read / file_write: safe file operations (bounded)
  - web_research: reference lookup via existing web tools
"""
from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


# ═══════════════════════════════════════════════════════════════
# BASE
# ═══════════════════════════════════════════════════════════════

@dataclass
class ToolResult:
    """Standardized tool result."""
    success: bool
    data: Any = None
    error: str = ""
    tool_name: str = ""


class BusinessTool:
    """Base class for business agent tools."""
    name: str = "base"
    description: str = ""
    risk_level: str = "low"

    def execute(self, **kwargs) -> ToolResult:
        raise NotImplementedError


# ═══════════════════════════════════════════════════════════════
# TOOLS
# ═══════════════════════════════════════════════════════════════

class StructuredIntakeTool(BusinessTool):
    """Collects and validates structured input from forms/messages."""
    name = "structured_intake"
    description = "Parse and validate structured input against a schema"
    risk_level = "low"

    def execute(self, raw_input: str = "", schema: list[dict] | None = None,
                **kwargs) -> ToolResult:
        if not raw_input:
            return ToolResult(success=False, error="No input provided",
                              tool_name=self.name)
        parsed: dict[str, Any] = {"raw": raw_input}
        missing: list[str] = []

        if schema:
            for field_def in schema:
                fname = field_def.get("name", "")
                required = field_def.get("required", False)
                # Simple keyword extraction from raw input
                if fname.lower().replace("_", " ") in raw_input.lower():
                    parsed[fname] = f"[extracted from input]"
                elif required:
                    missing.append(fname)

        return ToolResult(
            success=True,
            data={"parsed": parsed, "missing_fields": missing,
                  "complete": len(missing) == 0},
            tool_name=self.name,
        )


class MarkdownGeneratorTool(BusinessTool):
    """Generate professional markdown documents."""
    name = "markdown_generator"
    description = "Generate formatted markdown documents (quotes, reports, content)"
    risk_level = "low"

    def execute(self, title: str = "", sections: list[dict] | None = None,
                template: str = "default", **kwargs) -> ToolResult:
        if not title:
            return ToolResult(success=False, error="Title required",
                              tool_name=self.name)
        lines = [f"# {title}", ""]
        if sections:
            for section in sections:
                lines.append(f"## {section.get('heading', 'Section')}")
                lines.append(section.get("content", ""))
                lines.append("")
        return ToolResult(
            success=True,
            data={"markdown": "\n".join(lines), "word_count": len(" ".join(lines).split())},
            tool_name=self.name,
        )


class HtmlGeneratorTool(BusinessTool):
    """Generate HTML content from structured data."""
    name = "html_generator"
    description = "Generate HTML pages and content blocks"
    risk_level = "low"

    def execute(self, title: str = "", body_markdown: str = "",
                template: str = "default", **kwargs) -> ToolResult:
        if not title and not body_markdown:
            return ToolResult(success=False, error="Title or body required",
                              tool_name=self.name)
        # Simple markdown → HTML conversion
        html_body = body_markdown.replace("# ", "<h1>").replace("\n## ", "</h1>\n<h2>")
        html_body = html_body.replace("\n", "<br>\n")

        html = f"""<!DOCTYPE html>
<html>
<head><title>{title}</title>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
</head>
<body>
<h1>{title}</h1>
{html_body}
</body>
</html>"""
        return ToolResult(success=True, data={"html": html}, tool_name=self.name)


class EmailDraftTool(BusinessTool):
    """Compose professional email drafts (does NOT send)."""
    name = "email_draft"
    description = "Generate professional email drafts"
    risk_level = "low"

    def execute(self, to: str = "", subject: str = "", body: str = "",
                from_name: str = "", **kwargs) -> ToolResult:
        if not subject or not body:
            return ToolResult(success=False, error="Subject and body required",
                              tool_name=self.name)
        draft = {
            "to": to,
            "from": from_name,
            "subject": subject,
            "body": body,
            "status": "draft",
            "created_at": time.time(),
        }
        return ToolResult(success=True, data=draft, tool_name=self.name)


class CRMStoreTool(BusinessTool):
    """Lightweight CRM-like structured storage using JSON files."""
    name = "crm_store"
    description = "Store and retrieve customer/business records"
    risk_level = "medium"

    def __init__(self, storage_dir: Path | None = None):
        self._dir = storage_dir or Path("workspace/business_data/crm")

    def execute(self, action: str = "store", record_type: str = "customer",
                record_id: str = "", data: dict | None = None,
                **kwargs) -> ToolResult:
        self._dir.mkdir(parents=True, exist_ok=True)

        if action == "store" and data:
            if not record_id:
                record_id = f"{record_type}_{int(time.time())}"
            path = self._dir / f"{record_type}_{record_id}.json"
            record = {"id": record_id, "type": record_type,
                      "data": data, "updated_at": time.time()}
            path.write_text(json.dumps(record, indent=2, default=str), encoding="utf-8")
            return ToolResult(success=True, data={"id": record_id, "path": str(path)},
                              tool_name=self.name)

        elif action == "retrieve" and record_id:
            path = self._dir / f"{record_type}_{record_id}.json"
            if path.exists():
                record = json.loads(path.read_text(encoding="utf-8"))
                return ToolResult(success=True, data=record, tool_name=self.name)
            return ToolResult(success=False, error=f"Record not found: {record_id}",
                              tool_name=self.name)

        elif action == "list":
            records = []
            for path in self._dir.glob(f"{record_type}_*.json"):
                try:
                    records.append(json.loads(path.read_text(encoding="utf-8")))
                except Exception:
                    pass
            return ToolResult(success=True, data={"records": records, "count": len(records)},
                              tool_name=self.name)

        return ToolResult(success=False, error=f"Invalid action: {action}",
                          tool_name=self.name)


class QuoteFormatterTool(BusinessTool):
    """Format professional quotes and estimates."""
    name = "quote_formatter"
    description = "Generate formatted quotes with line items, totals, terms"
    risk_level = "low"

    def execute(self, customer_name: str = "", line_items: list[dict] | None = None,
                currency: str = "EUR", tax_rate: float = 0.21,
                validity_days: int = 30, terms: str = "",
                **kwargs) -> ToolResult:
        if not line_items:
            return ToolResult(success=False, error="Line items required",
                              tool_name=self.name)
        subtotal = sum(item.get("amount", 0) for item in line_items)
        tax = round(subtotal * tax_rate, 2)
        total = round(subtotal + tax, 2)

        quote = {
            "customer": customer_name,
            "line_items": line_items,
            "subtotal": subtotal,
            "tax_rate": tax_rate,
            "tax_amount": tax,
            "total": total,
            "currency": currency,
            "validity_days": validity_days,
            "terms": terms or f"Valid for {validity_days} days. Payment within 30 days of acceptance.",
            "created_at": time.time(),
        }
        return ToolResult(success=True, data=quote, tool_name=self.name)


# ═══════════════════════════════════════════════════════════════
# TOOL REGISTRY
# ═══════════════════════════════════════════════════════════════

_TOOLS: dict[str, BusinessTool] = {}


def _init_tools() -> dict[str, BusinessTool]:
    if not _TOOLS:
        for cls in (StructuredIntakeTool, MarkdownGeneratorTool, HtmlGeneratorTool,
                    EmailDraftTool, CRMStoreTool, QuoteFormatterTool):
            tool = cls()
            _TOOLS[tool.name] = tool
    return _TOOLS


def get_business_tool(name: str) -> BusinessTool | None:
    _init_tools()
    return _TOOLS.get(name)


def list_business_tools() -> list[dict]:
    _init_tools()
    return [{"name": t.name, "description": t.description, "risk_level": t.risk_level}
            for t in _TOOLS.values()]


def execute_tool(name: str, **kwargs) -> ToolResult:
    """Execute a business tool by name."""
    tool = get_business_tool(name)
    if not tool:
        return ToolResult(success=False, error=f"Tool not found: {name}", tool_name=name)
    try:
        return tool.execute(**kwargs)
    except Exception as e:
        return ToolResult(success=False, error=str(e), tool_name=name)
