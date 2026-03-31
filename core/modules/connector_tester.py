"""
JARVIS MAX — Connector Tester
=================================
Real API connectivity tests for external service connectors.

Each provider has a safe read-only test endpoint.
Tests NEVER modify data, delete resources, or trigger billing.

Supported providers:
- GitHub: GET /user
- Stripe: GET /v1/account
- Telegram: getMe
- Notion: GET /v1/users/me
- Supabase: GET /rest/v1/ (health)
- Slack: GET /api/auth.test
- OpenAI: GET /v1/models
- Anthropic: GET /v1/messages (dry check)
- OpenRouter: GET /api/v1/models
- Cloudflare: GET /client/v4/user
- Vercel: GET /v9/user
"""
from __future__ import annotations

import json
import logging
import time
import urllib.request
import urllib.error
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)

TEST_TIMEOUT = 10  # seconds


@dataclass
class ConnectorTestResult:
    """Result of a connector health test."""
    success: bool
    provider: str
    status: str              # connected / invalid_token / missing_permission / unreachable / error
    latency_ms: float = 0
    scope_valid: bool = True
    missing_permissions: list[str] = field(default_factory=list)
    account_info: str = ""   # Safe summary (name, email — no secrets)
    error: str = ""
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> dict:
        return {
            "success": self.success,
            "provider": self.provider,
            "status": self.status,
            "latency_ms": round(self.latency_ms, 1),
            "scope_valid": self.scope_valid,
            "missing_permissions": self.missing_permissions,
            "account": self.account_info[:100],
            "error": self.error[:200],
        }


# ── Provider Test Configs ──

PROVIDER_TESTS = {
    "github": {
        "url": "https://api.github.com/user",
        "auth_header": "Authorization",
        "auth_prefix": "Bearer ",
        "success_field": "login",
        "account_field": "login",
    },
    "stripe": {
        "url": "https://api.stripe.com/v1/account",
        "auth_header": "Authorization",
        "auth_prefix": "Bearer ",
        "success_field": "id",
        "account_field": "business_profile",
    },
    "telegram": {
        "url_template": "https://api.telegram.org/bot{token}/getMe",
        "auth_mode": "url",
        "success_field": "ok",
        "account_field": "result",
    },
    "notion": {
        "url": "https://api.notion.com/v1/users/me",
        "auth_header": "Authorization",
        "auth_prefix": "Bearer ",
        "extra_headers": {"Notion-Version": "2022-06-28"},
        "success_field": "id",
        "account_field": "name",
    },
    "slack": {
        "url": "https://slack.com/api/auth.test",
        "auth_header": "Authorization",
        "auth_prefix": "Bearer ",
        "success_field": "ok",
        "account_field": "team",
    },
    "openai": {
        "url": "https://api.openai.com/v1/models",
        "auth_header": "Authorization",
        "auth_prefix": "Bearer ",
        "success_field": "data",
        "account_field": "",
    },
    "anthropic": {
        "url": "https://api.anthropic.com/v1/models",
        "auth_header": "x-api-key",
        "auth_prefix": "",
        "extra_headers": {"anthropic-version": "2023-06-01"},
        "success_field": "data",
        "account_field": "",
    },
    "openrouter": {
        "url": "https://openrouter.ai/api/v1/models",
        "auth_header": "Authorization",
        "auth_prefix": "Bearer ",
        "success_field": "data",
        "account_field": "",
    },
    "cloudflare": {
        "url": "https://api.cloudflare.com/client/v4/user",
        "auth_header": "Authorization",
        "auth_prefix": "Bearer ",
        "success_field": "success",
        "account_field": "result",
    },
    "vercel": {
        "url": "https://api.vercel.com/v2/user",
        "auth_header": "Authorization",
        "auth_prefix": "Bearer ",
        "success_field": "user",
        "account_field": "user",
    },
    "supabase": {
        "url_template": "{endpoint}/rest/v1/",
        "auth_header": "apikey",
        "auth_prefix": "",
        "success_field": None,  # 200 OK is enough
        "account_field": "",
    },
}


class ConnectorTester:
    """
    Tests external connector connectivity.
    All tests are read-only — never modifies external resources.
    """

    def __init__(self, vault=None):
        self._vault = vault

    def test(
        self,
        provider: str,
        token: str = "",
        endpoint: str = "",
        extra_headers: dict | None = None,
    ) -> ConnectorTestResult:
        """
        Test a connector's connectivity.
        
        Args:
            provider: Provider name (github, stripe, etc.)
            token: API token/key (or retrieved from vault)
            endpoint: Custom endpoint (for supabase, self-hosted)
            extra_headers: Additional headers
        """
        config = PROVIDER_TESTS.get(provider.lower())
        if not config:
            return self._generic_test(provider, token, endpoint)

        if not token:
            return ConnectorTestResult(
                success=False, provider=provider,
                status="no_secret",
                error="Secret not configured",
            )

        start = time.time()

        try:
            # Build URL
            if "url_template" in config:
                url = config["url_template"].format(token=token, endpoint=endpoint)
            else:
                url = config["url"]

            # Build headers
            headers = {"User-Agent": "JarvisMax/1.0"}
            if config.get("auth_mode") != "url":
                headers[config["auth_header"]] = config["auth_prefix"] + token
            if config.get("extra_headers"):
                headers.update(config["extra_headers"])
            if extra_headers:
                headers.update(extra_headers)

            # Make request
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=TEST_TIMEOUT) as resp:
                body = resp.read().decode("utf-8")
                latency = (time.time() - start) * 1000

                data = {}
                try:
                    data = json.loads(body)
                except json.JSONDecodeError:
                    pass

                # Check success
                success_field = config.get("success_field")
                if success_field and success_field not in data:
                    return ConnectorTestResult(
                        success=False, provider=provider,
                        status="invalid_token",
                        latency_ms=latency,
                        error="Unexpected response format",
                    )

                # Extract account info
                account = ""
                acc_field = config.get("account_field", "")
                if acc_field and acc_field in data:
                    acc_val = data[acc_field]
                    if isinstance(acc_val, str):
                        account = acc_val
                    elif isinstance(acc_val, dict):
                        account = acc_val.get("name", acc_val.get("username", str(acc_val)[:50]))

                return ConnectorTestResult(
                    success=True, provider=provider,
                    status="connected",
                    latency_ms=latency,
                    account_info=str(account)[:100],
                )

        except urllib.error.HTTPError as e:
            latency = (time.time() - start) * 1000
            if e.code == 401:
                return ConnectorTestResult(
                    success=False, provider=provider,
                    status="invalid_token",
                    latency_ms=latency,
                    error="This token is invalid",
                )
            elif e.code == 403:
                return ConnectorTestResult(
                    success=False, provider=provider,
                    status="missing_permission",
                    latency_ms=latency,
                    error="Permission missing: insufficient access",
                    scope_valid=False,
                )
            elif e.code == 429:
                return ConnectorTestResult(
                    success=False, provider=provider,
                    status="rate_limited",
                    latency_ms=latency,
                    error="Rate limit reached",
                )
            else:
                return ConnectorTestResult(
                    success=False, provider=provider,
                    status="error",
                    latency_ms=latency,
                    error=f"HTTP {e.code}: {str(e.reason)[:100]}",
                )

        except (urllib.error.URLError, TimeoutError, OSError) as e:
            latency = (time.time() - start) * 1000
            return ConnectorTestResult(
                success=False, provider=provider,
                status="unreachable",
                latency_ms=latency,
                error=f"Service unreachable: {str(e)[:150]}",
            )

    def _generic_test(self, provider: str, token: str, endpoint: str) -> ConnectorTestResult:
        """Generic test for unknown providers — just check endpoint reachability."""
        if not endpoint:
            return ConnectorTestResult(
                success=False, provider=provider, status="needs_setup",
                error="No endpoint configured for unknown provider",
            )

        start = time.time()
        try:
            headers = {"User-Agent": "JarvisMax/1.0"}
            if token:
                headers["Authorization"] = f"Bearer {token}"
            req = urllib.request.Request(endpoint, headers=headers)
            with urllib.request.urlopen(req, timeout=TEST_TIMEOUT) as resp:
                latency = (time.time() - start) * 1000
                return ConnectorTestResult(
                    success=True, provider=provider,
                    status="connected", latency_ms=latency,
                )
        except Exception as e:
            latency = (time.time() - start) * 1000
            return ConnectorTestResult(
                success=False, provider=provider,
                status="error", latency_ms=latency,
                error=str(e)[:200],
            )

    @staticmethod
    def supported_providers() -> list[str]:
        """List providers with built-in test support."""
        return sorted(PROVIDER_TESTS.keys())
