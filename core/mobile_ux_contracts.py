"""
JARVIS MAX — Mobile UX Contracts
==================================
Server-side contracts that the mobile app depends on.
Guarantees consistent, user-friendly behavior for:

1. SessionContract      — login restore, logout wipe, token validation, expiry handling
2. MissionContract      — submit, progress states, result formatting
3. ApprovalContract     — approval states, approve/reject, pending count
4. ReconnectContract    — health check, graceful offline, reconnect flow
5. AdminContract        — role detection, advanced mode gating

Design: pure logic, no Flask/FastAPI dependency. Tests validate contracts directly.
"""
from __future__ import annotations

import hashlib
import re
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


# ═══════════════════════════════════════════════════════════════
# 1. SESSION CONTRACT
# ═══════════════════════════════════════════════════════════════

class TokenStatus(str, Enum):
    VALID = "valid"
    EXPIRED = "expired"
    REVOKED = "revoked"
    MALFORMED = "malformed"
    MISSING = "missing"


@dataclass
class SessionState:
    """Represents client-side session state."""
    token: str = ""
    login_mode: str = "token"   # "admin" or "token"
    username: str = ""
    role: str = "user"          # "admin" or "user"
    remember_me: bool = False
    has_stored_password: bool = False

    @property
    def is_authenticated(self) -> bool:
        return bool(self.token)

    @property
    def is_admin(self) -> bool:
        return self.role == "admin"


class SessionContract:
    """
    Contract: how login/logout/restore MUST behave.
    Mobile and web clients implement these contracts identically.
    """

    @staticmethod
    def validate_token(token: str) -> TokenStatus:
        """Classify a token's validity."""
        if not token:
            return TokenStatus.MISSING
        if not isinstance(token, str) or len(token) < 8:
            return TokenStatus.MALFORMED
        # JWT pattern (3 dot-separated base64 sections)
        if token.count(".") == 2:
            return TokenStatus.VALID  # Actual expiry checked server-side
        # Access token pattern (jv-xxx)
        if token.startswith("jv-"):
            return TokenStatus.VALID
        return TokenStatus.MALFORMED

    @staticmethod
    def login_result(success: bool, token: str = "", role: str = "user",
                     error: str = "") -> dict:
        """Standardized login response."""
        if success:
            return {
                "authenticated": True,
                "token": token,
                "role": role,
                "error": None,
                "action": "proceed_to_home",
            }
        # Friendly error messages
        error_map = {
            "invalid_credentials": "Incorrect username or password. Please try again.",
            "token_invalid": "This access token is invalid. Please check and try again.",
            "token_expired": "Your session has expired. Please sign in again.",
            "token_revoked": "Your access has been revoked. Contact your administrator.",
            "network_error": "Can't reach the server. Check your internet connection.",
            "server_error": "Something went wrong on our end. Please try again later.",
        }
        return {
            "authenticated": False,
            "token": "",
            "role": "user",
            "error": error_map.get(error, error or "Something went wrong. Please try again."),
            "action": "show_login",
        }

    @staticmethod
    def restore_result(token_status: TokenStatus, stored_session: SessionState | None
                       ) -> dict:
        """What to do when app starts and tries to restore session."""
        if stored_session is None or not stored_session.token:
            return {"action": "show_login", "reason": "no_stored_session"}

        if token_status == TokenStatus.VALID:
            return {"action": "proceed_to_home", "reason": "session_restored"}

        if token_status == TokenStatus.EXPIRED:
            if stored_session.has_stored_password and stored_session.login_mode == "admin":
                return {"action": "auto_relogin", "reason": "token_expired_but_credentials_stored"}
            return {
                "action": "show_login",
                "reason": "session_expired",
                "prefill_username": stored_session.username,
                "message": "Your session has expired. Please sign in again.",
            }

        if token_status == TokenStatus.REVOKED:
            return {
                "action": "show_login",
                "reason": "access_revoked",
                "message": "Your access has been revoked. Contact your administrator.",
            }

        return {"action": "show_login", "reason": "invalid_session"}

    @staticmethod
    def logout_checklist() -> list[str]:
        """Everything that MUST be wiped on logout."""
        return [
            "secure_storage:auth_token",
            "secure_storage:admin_password",
            "prefs:login_mode",
            "prefs:username",
            "prefs:remember_me",
            "prefs:role",
            "prefs:legacy_jwt_token",
            "memory:api_service_token",
        ]


# ═══════════════════════════════════════════════════════════════
# 2. MISSION CONTRACT
# ═══════════════════════════════════════════════════════════════

class MissionPhase(str, Enum):
    """User-facing mission phases (not internal states)."""
    WAITING = "waiting"          # Submitted, queued
    ANALYZING = "analyzing"      # Planning, classifying
    WORKING = "working"          # Executing
    NEEDS_APPROVAL = "needs_approval"  # Waiting for user
    DONE = "done"                # Completed successfully
    ERROR = "error"              # Failed


@dataclass
class MissionDisplay:
    """How a mission should be displayed to the user."""
    phase: str
    label: str
    description: str
    icon: str
    color: str      # "accent", "success", "warning", "error", "muted"
    show_progress: bool = False
    show_result: bool = False
    is_terminal: bool = False

    def to_dict(self) -> dict:
        return {
            "phase": self.phase,
            "label": self.label,
            "description": self.description,
            "icon": self.icon,
            "color": self.color,
            "show_progress": self.show_progress,
            "show_result": self.show_result,
            "is_terminal": self.is_terminal,
        }


class MissionContract:
    """
    Contract: how missions MUST be presented to users.
    Maps raw backend statuses → friendly phases.
    """

    # Raw status → (phase, label, description, icon, color)
    _STATUS_MAP = {
        "SUBMITTED":            ("waiting",        "Waiting",              "Your request is queued",                      "hourglass",    "muted"),
        "QUEUED":               ("waiting",        "Waiting",              "Your request is queued",                      "hourglass",    "muted"),
        "CLASSIFYING":          ("analyzing",      "Analyzing",            "Understanding your request",                  "brain",        "accent"),
        "PLANNING":             ("analyzing",      "Planning",             "Figuring out the best approach",              "brain",        "accent"),
        "ANALYZING":            ("analyzing",      "Analyzing",            "Analyzing what's needed",                     "brain",        "accent"),
        "PENDING_VALIDATION":   ("needs_approval", "Needs your approval",  "Jarvis needs your OK before continuing",     "hand",         "warning"),
        "APPROVED":             ("working",        "Working",              "Executing your request",                      "sync",         "accent"),
        "EXECUTING":            ("working",        "Working",              "Running the plan",                            "sync",         "accent"),
        "IN_PROGRESS":          ("working",        "Working",              "Processing...",                               "sync",         "accent"),
        "DONE":                 ("done",           "Done",                 "Completed successfully",                      "check",        "success"),
        "COMPLETED":            ("done",           "Done",                 "Completed successfully",                      "check",        "success"),
        "FAILED":               ("error",          "Error",                "Something went wrong",                        "error",        "error"),
        "ERROR":                ("error",          "Error",                "Something went wrong",                        "error",        "error"),
        "TIMEOUT":              ("error",          "Timed out",            "The request took too long",                   "timeout",      "error"),
        "CANCELLED":            ("done",           "Cancelled",            "Request was cancelled",                       "cancel",       "muted"),
        "BLOCKED":              ("needs_approval", "Blocked",              "Requires manual intervention",                "hand",         "warning"),
    }

    @classmethod
    def display(cls, raw_status: str) -> MissionDisplay:
        """Map a raw backend status to a user-friendly display."""
        key = raw_status.upper().replace(" ", "_")
        entry = cls._STATUS_MAP.get(key)
        if entry:
            phase, label, desc, icon, color = entry
        else:
            phase, label, desc, icon, color = ("working", raw_status.replace("_", " ").title(),
                                                 "Processing...", "sync", "accent")

        is_terminal = phase in ("done", "error")
        show_progress = phase in ("analyzing", "working", "waiting")
        show_result = phase == "done"

        return MissionDisplay(
            phase=phase, label=label, description=desc,
            icon=icon, color=color,
            show_progress=show_progress, show_result=show_result,
            is_terminal=is_terminal,
        )

    @staticmethod
    def submit_validation(user_input: str) -> tuple[bool, str]:
        """Validate mission input before sending."""
        text = user_input.strip()
        if not text:
            return False, "Please describe what you want Jarvis to do."
        if len(text) < 3:
            return False, "Could you be more specific? Try describing your request in a sentence."
        if len(text) > 5000:
            return False, "Your request is too long. Please keep it under 5,000 characters."
        return True, ""

    @staticmethod
    def format_result(mission: dict) -> dict:
        """Format mission result for display."""
        output = mission.get("final_output", "") or mission.get("output", "")
        plan = mission.get("plan_summary", "")
        steps = mission.get("plan_steps", [])

        return {
            "output": output,
            "has_output": bool(output),
            "plan_summary": plan,
            "step_count": len(steps),
            "steps": [
                {
                    "number": i + 1,
                    "task": s.get("task", s.get("description", f"Step {i + 1}")),
                }
                for i, s in enumerate(steps)
            ],
        }


# ═══════════════════════════════════════════════════════════════
# 3. APPROVAL CONTRACT
# ═══════════════════════════════════════════════════════════════

class RiskLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class ApprovalDisplay:
    """How an approval request should look to the user."""
    id: str
    what: str           # What Jarvis wants to do
    why: str            # Why it needs approval
    risk_level: str
    risk_label: str
    risk_color: str

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "what": self.what,
            "why": self.why,
            "risk_level": self.risk_level,
            "risk_label": self.risk_label,
            "risk_color": self.risk_color,
        }


class ApprovalContract:
    """Contract: how approvals are presented."""

    @staticmethod
    def format_approval(raw: dict) -> ApprovalDisplay:
        """Format raw action for display."""
        risk = (raw.get("risk") or "low").lower()
        risk_map = {
            "low":      ("Low risk",    "success"),
            "medium":   ("Medium risk", "warning"),
            "high":     ("High risk",   "error"),
            "critical": ("High risk",   "error"),
        }
        label, color = risk_map.get(risk, ("Unknown risk", "muted"))

        return ApprovalDisplay(
            id=raw.get("id", ""),
            what=raw.get("description", raw.get("plan_summary", "Perform an action")),
            why=raw.get("approval_reason", raw.get("reason", "")),
            risk_level=risk,
            risk_label=label,
            risk_color=color,
        )

    @staticmethod
    def approve_result(success: bool, error: str = "") -> dict:
        """Standardized approve response."""
        if success:
            return {"ok": True, "message": "Approved — Jarvis is on it", "action": "refresh"}
        return {"ok": False, "message": error or "Could not approve. Please try again.", "action": "retry"}

    @staticmethod
    def reject_result(success: bool, error: str = "") -> dict:
        if success:
            return {"ok": True, "message": "Denied", "action": "refresh"}
        return {"ok": False, "message": error or "Could not deny. Please try again.", "action": "retry"}


# ═══════════════════════════════════════════════════════════════
# 4. RECONNECT CONTRACT
# ═══════════════════════════════════════════════════════════════

class ConnectionState(str, Enum):
    CONNECTED = "connected"
    RECONNECTING = "reconnecting"
    OFFLINE = "offline"


@dataclass
class ConnectionDisplay:
    """How connection state should look."""
    state: str
    label: str
    color: str
    show_retry: bool = False
    show_banner: bool = False

    def to_dict(self) -> dict:
        return {
            "state": self.state,
            "label": self.label,
            "color": self.color,
            "show_retry": self.show_retry,
            "show_banner": self.show_banner,
        }


class ReconnectContract:
    """Contract: how connection state is presented."""

    @staticmethod
    def display(state: ConnectionState, retry_count: int = 0) -> ConnectionDisplay:
        if state == ConnectionState.CONNECTED:
            return ConnectionDisplay(
                state="connected", label="Connected", color="success",
            )
        if state == ConnectionState.RECONNECTING:
            return ConnectionDisplay(
                state="reconnecting",
                label=f"Reconnecting{'.' * min(retry_count, 3)}",
                color="warning", show_banner=True,
            )
        return ConnectionDisplay(
            state="offline",
            label="No connection",
            color="error", show_retry=True, show_banner=True,
        )

    @staticmethod
    def should_retry(retry_count: int, max_retries: int = 5) -> tuple[bool, float]:
        """Should we auto-retry? Returns (should_retry, delay_seconds)."""
        if retry_count >= max_retries:
            return False, 0
        # Exponential backoff: 2, 4, 8, 16, 30 seconds
        delay = min(30, 2 ** (retry_count + 1))
        return True, delay

    @staticmethod
    def health_check_result(status_code: int | None) -> ConnectionState:
        """Map health check result to connection state."""
        if status_code is not None and 200 <= status_code < 300:
            return ConnectionState.CONNECTED
        if status_code is not None:
            return ConnectionState.RECONNECTING
        return ConnectionState.OFFLINE


# ═══════════════════════════════════════════════════════════════
# 5. ADMIN CONTRACT
# ═══════════════════════════════════════════════════════════════

@dataclass
class UIMode:
    """What UI elements to show based on role."""
    show_advanced_toggle: bool = False
    show_diagnostics: bool = False
    show_extensions: bool = False
    show_model_routing: bool = False
    show_system_traces: bool = False
    show_self_improvement: bool = False

    def to_dict(self) -> dict:
        return {
            "show_advanced_toggle": self.show_advanced_toggle,
            "show_diagnostics": self.show_diagnostics,
            "show_extensions": self.show_extensions,
            "show_model_routing": self.show_model_routing,
            "show_system_traces": self.show_system_traces,
            "show_self_improvement": self.show_self_improvement,
        }


class AdminContract:
    """Contract: what admin vs normal user sees."""

    @staticmethod
    def ui_mode(role: str, advanced_enabled: bool = False) -> UIMode:
        """Determine visible UI elements."""
        if role == "admin":
            return UIMode(
                show_advanced_toggle=True,
                show_diagnostics=advanced_enabled,
                show_extensions=advanced_enabled,
                show_model_routing=advanced_enabled,
                show_system_traces=advanced_enabled,
                show_self_improvement=advanced_enabled,
            )
        # Normal user: no advanced toggle, no advanced features
        return UIMode()

    @staticmethod
    def can_access_admin_panel(role: str) -> bool:
        return role == "admin"

    @staticmethod
    def settings_sections(role: str, advanced_enabled: bool = False) -> list[str]:
        """Which settings sections to show."""
        sections = ["connection", "server"]
        if role == "admin":
            sections.append("advanced_toggle")
            if advanced_enabled:
                sections.extend([
                    "diagnostics", "models_routing", "tools_capabilities",
                    "self_improvement", "system_traces",
                ])
        return sections
