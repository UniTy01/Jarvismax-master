"""
core/tools/email_tool.py — Email tool (SMTP send).

MEDIUM risk — always requires approval.
Rate limited: max 10 emails per hour.
"""
from __future__ import annotations

import os
import re
import smtplib
import time
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from core.tools.tool_template import BaseTool, ToolResult

log = logging.getLogger("jarvis.tools.email")

_MAX_BODY_CHARS = 10_000
_MAX_EMAILS_PER_HOUR = 10
_send_timestamps: list[float] = []


class EmailTool(BaseTool):
    name = "email_send"
    risk_level = "MEDIUM"
    description = "Send email via configured SMTP server"
    timeout_seconds = 15.0

    def execute(self, to: str = "", subject: str = "", body: str = "", **kw) -> ToolResult:
        # Validate inputs
        if not to or not re.match(r"^[^@]+@[^@]+\.[^@]+$", to):
            return ToolResult(ok=False, error="invalid_recipient: must be valid email")
        if not subject:
            return ToolResult(ok=False, error="missing_subject")
        if len(body) > _MAX_BODY_CHARS:
            return ToolResult(ok=False, error=f"body_too_large: {len(body)} > {_MAX_BODY_CHARS}")

        # Rate limit
        now = time.time()
        _send_timestamps[:] = [t for t in _send_timestamps if now - t < 3600]
        if len(_send_timestamps) >= _MAX_EMAILS_PER_HOUR:
            return ToolResult(ok=False, error=f"rate_limited: {_MAX_EMAILS_PER_HOUR}/hour exceeded")

        # Config
        host = os.getenv("JARVIS_SMTP_HOST", "")
        port = int(os.getenv("JARVIS_SMTP_PORT", "587"))
        user = os.getenv("JARVIS_SMTP_USER", "")
        password = os.getenv("JARVIS_SMTP_PASSWORD", "")
        from_addr = os.getenv("JARVIS_SMTP_FROM", user)

        if not host or not user:
            return ToolResult(ok=False, error="smtp_not_configured: set JARVIS_SMTP_* env vars")

        # Allowlist check
        allowlist = os.getenv("JARVIS_EMAIL_ALLOWLIST", "").strip()
        if allowlist:
            allowed = [a.strip().lower() for a in allowlist.split(",")]
            if to.lower() not in allowed:
                return ToolResult(ok=False, error=f"recipient_not_allowed: {to}")

        # Send
        try:
            msg = MIMEMultipart()
            msg["From"] = from_addr
            msg["To"] = to
            msg["Subject"] = subject
            msg.attach(MIMEText(body, "plain", "utf-8"))

            with smtplib.SMTP(host, port, timeout=self.timeout_seconds) as server:
                server.starttls()
                server.login(user, password)
                server.send_message(msg)

            _send_timestamps.append(time.time())
            log.info("email_sent", to=to, subject=subject[:50])
            return ToolResult(ok=True, result=f"Email sent to {to}")

        except smtplib.SMTPAuthenticationError:
            return ToolResult(ok=False, error="smtp_auth_failed")
        except smtplib.SMTPException as e:
            return ToolResult(ok=False, error=f"smtp_error: {str(e)[:200]}", retryable=True)
        except Exception as e:
            return ToolResult(ok=False, error=f"email_error: {str(e)[:200]}")
