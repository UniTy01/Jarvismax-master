"""
Tests — Mobile UX Contracts

Session
  U1.  Login restore with valid token → proceed
  U2.  Login restore with expired token + stored password → auto relogin
  U3.  Login restore with expired token + no password → show login with message
  U4.  Login restore with revoked token → show login with revoked message
  U5.  Login restore with no stored session → show login
  U6.  Logout checklist includes all storage keys
  U7.  Token validation: JWT valid
  U8.  Token validation: access token valid
  U9.  Token validation: empty → missing
  U10. Token validation: garbage → malformed
  U11. Login success result format
  U12. Login failure result has friendly error

Mission
  U13. Submit validation: empty rejected
  U14. Submit validation: too short rejected
  U15. Submit validation: too long rejected
  U16. Submit validation: normal accepted
  U17. SUBMITTED → waiting phase
  U18. EXECUTING → working phase
  U19. PENDING_VALIDATION → needs_approval phase
  U20. DONE → done phase (terminal)
  U21. FAILED → error phase (terminal)
  U22. Unknown status → working (safe fallback)
  U23. Result formatting has output and steps

Approval
  U24. Format approval with risk levels
  U25. Approve success result
  U26. Reject success result
  U27. Approve failure result

Reconnect
  U28. Health check 200 → connected
  U29. Health check 500 → reconnecting
  U30. Health check None → offline
  U31. Retry backoff: exponential up to 30s
  U32. Retry stops after max retries
  U33. Reconnecting display shows banner

Admin
  U34. Admin with advanced=off → toggle visible, rest hidden
  U35. Admin with advanced=on → all visible
  U36. Normal user → nothing advanced
  U37. Settings sections: admin vs user
  U38. Admin panel access: admin only
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from core.mobile_ux_contracts import (
    TokenStatus, SessionState, SessionContract,
    MissionPhase, MissionDisplay, MissionContract,
    RiskLevel, ApprovalDisplay, ApprovalContract,
    ConnectionState, ConnectionDisplay, ReconnectContract,
    UIMode, AdminContract,
)


# ═══════════════════════════════════════════════════════════════
# SESSION
# ═══════════════════════════════════════════════════════════════

class TestSession:

    def test_restore_valid(self):
        """U1: Valid token → proceed to home."""
        session = SessionState(token="jv-abc123", role="user")
        result = SessionContract.restore_result(TokenStatus.VALID, session)
        assert result["action"] == "proceed_to_home"

    def test_restore_expired_with_password(self):
        """U2: Expired + stored password → auto relogin."""
        session = SessionState(
            token="expired.jwt.token", login_mode="admin",
            username="admin", has_stored_password=True,
        )
        result = SessionContract.restore_result(TokenStatus.EXPIRED, session)
        assert result["action"] == "auto_relogin"

    def test_restore_expired_no_password(self):
        """U3: Expired + no password → show login with message."""
        session = SessionState(token="expired.jwt.token", username="admin")
        result = SessionContract.restore_result(TokenStatus.EXPIRED, session)
        assert result["action"] == "show_login"
        assert "expired" in result.get("message", "").lower()

    def test_restore_revoked(self):
        """U4: Revoked → show login with revoked message."""
        session = SessionState(token="jv-revoked")
        result = SessionContract.restore_result(TokenStatus.REVOKED, session)
        assert result["action"] == "show_login"
        assert "revoked" in result.get("message", "").lower()

    def test_restore_no_session(self):
        """U5: No stored session → show login."""
        result = SessionContract.restore_result(TokenStatus.MISSING, None)
        assert result["action"] == "show_login"

    def test_logout_checklist(self):
        """U6: Logout must wipe all storage keys."""
        checklist = SessionContract.logout_checklist()
        assert any("auth_token" in item for item in checklist)
        assert any("admin_password" in item for item in checklist)
        assert any("login_mode" in item for item in checklist)
        assert any("remember_me" in item for item in checklist)
        assert any("legacy" in item.lower() or "jwt" in item.lower() for item in checklist)
        assert len(checklist) >= 7

    def test_validate_jwt(self):
        """U7: JWT token format valid."""
        assert SessionContract.validate_token("eyJ.abc.def") == TokenStatus.VALID

    def test_validate_access_token(self):
        """U8: Access token format valid."""
        assert SessionContract.validate_token("jv-abc12345") == TokenStatus.VALID

    def test_validate_empty(self):
        """U9: Empty → missing."""
        assert SessionContract.validate_token("") == TokenStatus.MISSING

    def test_validate_garbage(self):
        """U10: Garbage → malformed."""
        assert SessionContract.validate_token("abc") == TokenStatus.MALFORMED

    def test_login_success_result(self):
        """U11: Login success has expected fields."""
        r = SessionContract.login_result(True, token="jv-new", role="admin")
        assert r["authenticated"] is True
        assert r["token"] == "jv-new"
        assert r["role"] == "admin"
        assert r["action"] == "proceed_to_home"

    def test_login_failure_friendly(self):
        """U12: Login failure has friendly error."""
        r = SessionContract.login_result(False, error="invalid_credentials")
        assert r["authenticated"] is False
        assert "incorrect" in r["error"].lower() or "invalid" in r["error"].lower()


# ═══════════════════════════════════════════════════════════════
# MISSION
# ═══════════════════════════════════════════════════════════════

class TestMission:

    def test_submit_empty(self):
        """U13: Empty input rejected."""
        ok, msg = MissionContract.submit_validation("")
        assert not ok
        assert msg

    def test_submit_too_short(self):
        """U14: Too short rejected."""
        ok, msg = MissionContract.submit_validation("hi")
        assert not ok

    def test_submit_too_long(self):
        """U15: Too long rejected."""
        ok, msg = MissionContract.submit_validation("x" * 5001)
        assert not ok

    def test_submit_normal(self):
        """U16: Normal input accepted."""
        ok, msg = MissionContract.submit_validation("Analyze the homepage of example.com")
        assert ok
        assert not msg

    def test_submitted_waiting(self):
        """U17: SUBMITTED → waiting."""
        d = MissionContract.display("SUBMITTED")
        assert d.phase == "waiting"
        assert d.show_progress

    def test_executing_working(self):
        """U18: EXECUTING → working."""
        d = MissionContract.display("EXECUTING")
        assert d.phase == "working"
        assert d.label == "Working"

    def test_pending_approval(self):
        """U19: PENDING_VALIDATION → needs_approval."""
        d = MissionContract.display("PENDING_VALIDATION")
        assert d.phase == "needs_approval"
        assert "approval" in d.label.lower()

    def test_done_terminal(self):
        """U20: DONE → done, terminal."""
        d = MissionContract.display("DONE")
        assert d.phase == "done"
        assert d.is_terminal
        assert d.show_result

    def test_failed_terminal(self):
        """U21: FAILED → error, terminal."""
        d = MissionContract.display("FAILED")
        assert d.phase == "error"
        assert d.is_terminal

    def test_unknown_fallback(self):
        """U22: Unknown → working (safe fallback)."""
        d = MissionContract.display("SOME_WEIRD_STATE")
        assert d.phase == "working"

    def test_result_format(self):
        """U23: Result formatting."""
        mission = {
            "final_output": "Analysis complete: the site has 3 issues",
            "plan_summary": "Analyze website",
            "plan_steps": [
                {"task": "Fetch homepage"},
                {"task": "Check SEO"},
            ],
        }
        r = MissionContract.format_result(mission)
        assert r["has_output"]
        assert r["step_count"] == 2
        assert r["steps"][0]["number"] == 1


# ═══════════════════════════════════════════════════════════════
# APPROVAL
# ═══════════════════════════════════════════════════════════════

class TestApproval:

    def test_format_risk_levels(self):
        """U24: Format with risk levels."""
        for risk in ["low", "medium", "high", "critical"]:
            a = ApprovalContract.format_approval({"id": "1", "risk": risk, "description": "test"})
            assert a.risk_label
            assert a.risk_color

    def test_approve_success(self):
        """U25: Approve success."""
        r = ApprovalContract.approve_result(True)
        assert r["ok"]
        assert "approved" in r["message"].lower()

    def test_reject_success(self):
        """U26: Reject success."""
        r = ApprovalContract.reject_result(True)
        assert r["ok"]
        assert "denied" in r["message"].lower()

    def test_approve_failure(self):
        """U27: Approve failure."""
        r = ApprovalContract.approve_result(False)
        assert not r["ok"]
        assert "try again" in r["message"].lower()


# ═══════════════════════════════════════════════════════════════
# RECONNECT
# ═══════════════════════════════════════════════════════════════

class TestReconnect:

    def test_health_200(self):
        """U28: 200 → connected."""
        assert ReconnectContract.health_check_result(200) == ConnectionState.CONNECTED

    def test_health_500(self):
        """U29: 500 → reconnecting."""
        assert ReconnectContract.health_check_result(500) == ConnectionState.RECONNECTING

    def test_health_none(self):
        """U30: None → offline."""
        assert ReconnectContract.health_check_result(None) == ConnectionState.OFFLINE

    def test_retry_backoff(self):
        """U31: Exponential backoff up to 30s."""
        _, d1 = ReconnectContract.should_retry(0)
        _, d2 = ReconnectContract.should_retry(1)
        _, d3 = ReconnectContract.should_retry(3)
        assert d1 < d2 < d3
        assert d3 <= 30

    def test_retry_stops(self):
        """U32: Stops after max retries."""
        should, _ = ReconnectContract.should_retry(5, max_retries=5)
        assert not should

    def test_reconnecting_banner(self):
        """U33: Reconnecting shows banner."""
        d = ReconnectContract.display(ConnectionState.RECONNECTING, retry_count=2)
        assert d.show_banner
        assert "reconnect" in d.label.lower()


# ═══════════════════════════════════════════════════════════════
# ADMIN
# ═══════════════════════════════════════════════════════════════

class TestAdmin:

    def test_admin_advanced_off(self):
        """U34: Admin + advanced off → toggle visible, rest hidden."""
        mode = AdminContract.ui_mode("admin", advanced_enabled=False)
        assert mode.show_advanced_toggle
        assert not mode.show_diagnostics
        assert not mode.show_extensions

    def test_admin_advanced_on(self):
        """U35: Admin + advanced on → all visible."""
        mode = AdminContract.ui_mode("admin", advanced_enabled=True)
        assert mode.show_advanced_toggle
        assert mode.show_diagnostics
        assert mode.show_extensions
        assert mode.show_model_routing
        assert mode.show_system_traces
        assert mode.show_self_improvement

    def test_normal_user(self):
        """U36: Normal user → nothing advanced."""
        mode = AdminContract.ui_mode("user")
        assert not mode.show_advanced_toggle
        assert not mode.show_diagnostics

    def test_settings_sections(self):
        """U37: Settings sections differ by role."""
        admin_sections = AdminContract.settings_sections("admin", advanced_enabled=True)
        user_sections = AdminContract.settings_sections("user")
        assert len(admin_sections) > len(user_sections)
        assert "diagnostics" in admin_sections
        assert "diagnostics" not in user_sections

    def test_admin_panel_access(self):
        """U38: Admin panel: admin only."""
        assert AdminContract.can_access_admin_panel("admin")
        assert not AdminContract.can_access_admin_panel("user")
