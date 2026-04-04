"""
connectors/composio_adapter.py — Composio connector adapter (stub).

Composio (https://composio.dev) provides 250+ pre-built integrations:
Gmail, Slack, GitHub, Linear, Notion, HubSpot, Salesforce, Google Drive, etc.
Agents can call any Composio action without managing OAuth/API keys directly.

Feature flag : COMPOSIO_ENABLED=true   (default: false)
Dependency   : pip install composio-core  (NOT in main requirements — optional)
API key      : COMPOSIO_API_KEY

Status: STUB — implement execute() when COMPOSIO_ENABLED=true is needed.
This file is the integration point. Do not add composio to requirements.txt
until the feature is explicitly enabled in production.

Security:
  - API key via env only (never committed)
  - All actions go through ConnectorResult (auditable)
  - High-risk actions (send_email, create_issue) should require human approval
  - composio-core is not installed by default (fail-open if missing)

Usage example (when enabled):
    from connectors.composio_adapter import ComposioAdapter
    adapter = ComposioAdapter()
    if adapter.is_configured():
        result = adapter.execute("gmail_send_email", {
            "to": "user@example.com",
            "subject": "Jarvis report",
            "body": "Here is your analysis...",
        })
"""
from __future__ import annotations

import os
import time
import structlog

from .base import ConnectorBase, ConnectorResult

log = structlog.get_logger("connectors.composio")

# Composio actions that require explicit approval before execution
_HIGH_RISK_ACTIONS = frozenset({
    "gmail_send_email",
    "gmail_delete_email",
    "slack_send_message",
    "github_create_repository",
    "github_delete_repository",
    "notion_delete_page",
    "hubspot_create_deal",
    "salesforce_create_lead",
    "linear_delete_issue",
})


class ComposioAdapter(ConnectorBase):
    """
    Composio integration adapter.

    Delegates to the composio-core Python SDK when COMPOSIO_ENABLED=true.
    Fails gracefully if composio-core is not installed or API key is missing.
    """

    name = "composio"
    description = "Composio — 250+ app integrations (Gmail, Slack, GitHub, ...)"
    actions = ["*"]  # Composio supports arbitrary action names

    def is_configured(self) -> bool:
        """
        Returns True only if:
        1. COMPOSIO_ENABLED=true
        2. COMPOSIO_API_KEY is set
        3. composio-core package is installed
        """
        if not _composio_feature_enabled():
            return False
        if not os.environ.get("COMPOSIO_API_KEY", ""):
            log.warning("composio_not_configured", reason="COMPOSIO_API_KEY not set")
            return False
        try:
            import composio  # noqa: F401
            return True
        except ImportError:
            log.warning(
                "composio_not_installed",
                hint="pip install composio-core",
            )
            return False

    def execute(self, action: str, params: dict) -> ConnectorResult:
        """
        Execute a Composio action.

        Args:
            action: Composio action name (e.g. "gmail_send_email")
            params: Action parameters (action-specific)

        Returns:
            ConnectorResult with success/error info.
        """
        result = ConnectorResult(connector=self.name, action=action)
        t0 = time.monotonic()

        # Guard: feature flag
        if not self.is_configured():
            result.error = (
                "Composio not configured. Set COMPOSIO_ENABLED=true and "
                "COMPOSIO_API_KEY, then pip install composio-core."
            )
            return result

        # Guard: high-risk actions
        if action in _HIGH_RISK_ACTIONS:
            log.warning(
                "composio_high_risk_action",
                action=action,
                hint="This action should be approved by a human before execution.",
            )
            # Note: actual approval gate is enforced by the ActionQueue/PipelineGuard
            # at the orchestration level. This is a logging guard only.

        try:
            result = self._execute_composio(action, params, result)
        except Exception as exc:
            result.error = f"Composio execution error: {exc}"
            log.error("composio_execute_failed", action=action, error=str(exc))
        finally:
            result.duration_ms = (time.monotonic() - t0) * 1000

        return result

    def _execute_composio(
        self,
        action: str,
        params: dict,
        result: ConnectorResult,
    ) -> ConnectorResult:
        """
        Internal: delegates to composio-core SDK.

        TODO: implement when COMPOSIO_ENABLED is needed in production.
        Current state: stub that raises NotImplementedError.
        Replace this method with actual composio SDK calls.

        Example implementation:
            from composio import ComposioToolSet, Action
            toolset = ComposioToolSet(api_key=os.environ["COMPOSIO_API_KEY"])
            response = toolset.execute_action(
                action=Action(action),
                params=params,
            )
            result.success = response.get("successfull", False)
            result.output = response
            return result
        """
        raise NotImplementedError(
            f"ComposioAdapter._execute_composio not yet implemented for action={action!r}. "
            "See composio-core docs: https://docs.composio.dev"
        )

    def list_apps(self) -> list[str]:
        """
        List available Composio app names.
        Returns empty list if not configured.

        TODO: implement when COMPOSIO_ENABLED is needed.
        """
        if not self.is_configured():
            return []
        try:
            # from composio import ComposioToolSet
            # toolset = ComposioToolSet(api_key=os.environ["COMPOSIO_API_KEY"])
            # return [app.name for app in toolset.get_apps()]
            raise NotImplementedError("list_apps stub")
        except Exception as exc:
            log.warning("composio_list_apps_failed", error=str(exc))
            return []


def _composio_feature_enabled() -> bool:
    """Read COMPOSIO_ENABLED env var. Default: false."""
    return os.environ.get("COMPOSIO_ENABLED", "false").lower() in ("1", "true", "yes")
