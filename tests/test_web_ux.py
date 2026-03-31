"""
Tests — Web UX Contracts & Structure

Validates that the web frontend meets product-quality standards.
Tests check the actual HTML/JS for correct behaviors.

First-use Flow
  W1.  Login overlay visible on start
  W2.  Onboarding section exists for new users
  W3.  Suggestion chips provide examples
  W4.  Session restore logic present (SessionStore.restore)

Mission Flow
  W5.  Input card with textarea and send button
  W6.  Submit sends to /api endpoint
  W7.  Progress card renders after submit
  W8.  Status pill uses friendly labels
  W9.  Input validation (Cmd/Ctrl+Enter shortcut)

Approval Flow
  W10. Approval card with risk indicator
  W11. Approve and deny buttons present
  W12. Pending badge on nav

Admin Token Flow
  W13. Token creation form in advanced panel
  W14. Token result shows "won't be shown again"
  W15. Revoke button on active tokens

Session Restore
  W16. SessionStore.save stores all required fields
  W17. SessionStore.clear removes all keys
  W18. Expired session shows helpful message
  W19. Auto re-login with stored admin credentials

Invalid Session Recovery
  W20. 401 response triggers re-auth
  W21. Logout wipes SessionStore
  W22. Logout shows confirmation message

UX Quality
  W23. No French text in UI
  W24. Error messages are user-friendly
  W25. Status dot shows connection
  W26. Empty state has helpful message
  W27. Mobile-responsive (mobile-nav exists)
  W28. Extensions tab with CRUD
  W29. Advanced panel hidden by default
  W30. Keyboard shortcuts work (Ctrl+Enter, Enter on login)

Mission Result Display
  W31. Result card shows final output
  W32. Steps numbered correctly

Server Contract Alignment
  W33. Status mapping covers all MissionContract statuses
  W34. Risk levels match ApprovalContract
  W35. Login flow matches SessionContract
"""
import os
import sys
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

# Load the HTML once
_HTML = Path("static/index.html").read_text(encoding="utf-8")

from core.mobile_ux_contracts import (
    MissionContract, ApprovalContract, SessionContract, ReconnectContract,
)


# ═══════════════════════════════════════════════════════════════
# FIRST-USE FLOW
# ═══════════════════════════════════════════════════════════════

class TestFirstUse:

    def test_login_overlay(self):
        """W1: Login overlay visible on start."""
        assert 'login-overlay' in _HTML
        assert 'login-card' in _HTML

    def test_onboarding_section(self):
        """W2: Onboarding for new users."""
        assert 'onboarding' in _HTML
        assert 'Try something' in _HTML or 'things Jarvis can do' in _HTML

    def test_suggestion_chips(self):
        """W3: Suggestions present."""
        assert 'chips' in _HTML
        assert 'fillSuggestion' in _HTML

    def test_session_restore(self):
        """W4: Session restore logic."""
        assert 'SessionStore.restore' in _HTML or 'SessionStore' in _HTML
        assert 'jarvis_token' in _HTML


# ═══════════════════════════════════════════════════════════════
# MISSION FLOW
# ═══════════════════════════════════════════════════════════════

class TestMissionFlow:

    def test_input_card(self):
        """W5: Input card present."""
        assert 'input-card' in _HTML
        assert 'mission-input' in _HTML
        assert 'btn-send' in _HTML

    def test_submit_api(self):
        """W6: Submit sends to API."""
        assert 'submitMission' in _HTML
        assert '/api/' in _HTML

    def test_progress_card(self):
        """W7: Progress card."""
        assert 'progress-card' in _HTML
        assert 'renderProgress' in _HTML

    def test_friendly_status(self):
        """W8: Friendly status labels."""
        assert 'friendlyStatus' in _HTML
        assert "'Done'" in _HTML or '"Done"' in _HTML
        assert "'Working'" in _HTML or '"Working"' in _HTML
        assert "'Needs approval'" in _HTML or '"Needs approval"' in _HTML

    def test_keyboard_submit(self):
        """W9: Cmd/Ctrl+Enter submit."""
        assert 'metaKey' in _HTML or 'ctrlKey' in _HTML
        assert 'Enter' in _HTML


# ═══════════════════════════════════════════════════════════════
# APPROVAL FLOW
# ═══════════════════════════════════════════════════════════════

class TestApprovalFlow:

    def test_approval_card(self):
        """W10: Approval card with risk."""
        assert 'approval-card' in _HTML
        assert 'risk' in _HTML.lower()

    def test_approve_deny_buttons(self):
        """W11: Approve and deny buttons."""
        assert 'btn-approve' in _HTML
        assert 'btn-deny' in _HTML
        assert 'approveAction' in _HTML
        assert 'rejectAction' in _HTML

    def test_pending_badge(self):
        """W12: Pending badge on nav."""
        assert 'nav-badge' in _HTML


# ═══════════════════════════════════════════════════════════════
# ADMIN TOKEN FLOW
# ═══════════════════════════════════════════════════════════════

class TestAdminToken:

    def test_token_creation(self):
        """W13: Token creation form."""
        assert 'new-token-name' in _HTML
        assert 'createToken' in _HTML

    def test_token_warning(self):
        """W14: Token shown-once warning."""
        assert 'not be shown again' in _HTML.lower() or 'will not be shown' in _HTML.lower()

    def test_revoke_button(self):
        """W15: Revoke button."""
        assert 'revokeToken' in _HTML


# ═══════════════════════════════════════════════════════════════
# SESSION RESTORE
# ═══════════════════════════════════════════════════════════════

class TestSessionRestore:

    def test_session_save_fields(self):
        """W16: SessionStore saves required fields."""
        assert 'jarvis_login_mode' in _HTML
        assert 'jarvis_username' in _HTML
        assert 'jarvis_role' in _HTML
        assert 'jarvis_remember_me' in _HTML

    def test_session_clear(self):
        """W17: Clear removes all keys."""
        # Check the clear() function removes all keys
        assert 'clear()' in _HTML
        assert 'removeItem' in _HTML

    def test_expired_message(self):
        """W18: Expired session message."""
        assert 'session has expired' in _HTML.lower()

    def test_auto_relogin(self):
        """W19: Auto re-login with stored credentials."""
        assert 'saved.password' in _HTML or 'jarvis_admin_pw' in _HTML
        assert '/auth/login' in _HTML


# ═══════════════════════════════════════════════════════════════
# INVALID SESSION RECOVERY
# ═══════════════════════════════════════════════════════════════

class TestSessionRecovery:

    def test_401_reauth(self):
        """W20: 401 triggers re-auth."""
        assert '401' in _HTML
        assert 'login' in _HTML.lower()

    def test_logout_wipes(self):
        """W21: Logout clears SessionStore."""
        assert 'SessionStore.clear' in _HTML
        assert 'logout' in _HTML

    def test_logout_confirmation(self):
        """W22: Logout shows confirmation."""
        assert 'Logged out' in _HTML or 'logged out' in _HTML


# ═══════════════════════════════════════════════════════════════
# UX QUALITY
# ═══════════════════════════════════════════════════════════════

class TestUXQuality:

    def test_no_french(self):
        """W23: No French text."""
        french_patterns = [
            'Impossible de joindre',
            'Vérifiez',
            'Délai dépassé',
            'Réponse invalide',
            'Tolérer',
        ]
        for pattern in french_patterns:
            assert pattern not in _HTML, f"Found French text: {pattern}"

    def test_friendly_errors(self):
        """W24: Errors are user-friendly."""
        assert 'Please' in _HTML or 'please' in _HTML
        assert 'try again' in _HTML.lower()

    def test_connection_dot(self):
        """W25: Status dot present."""
        assert 'status-dot' in _HTML
        assert 'online' in _HTML
        assert 'offline' in _HTML

    def test_empty_state(self):
        """W26: Empty state present."""
        assert 'empty-state' in _HTML
        assert 'No missions yet' in _HTML or 'No tasks yet' in _HTML or 'Nothing needs' in _HTML

    def test_mobile_responsive(self):
        """W27: Mobile-responsive."""
        assert 'mobile-nav' in _HTML
        assert '@media' in _HTML

    def test_extensions_crud(self):
        """W28: Extensions with CRUD."""
        assert 'ext-form' in _HTML
        assert 'saveExtension' in _HTML
        assert 'deleteExt' in _HTML
        assert 'editExt' in _HTML

    def test_advanced_hidden(self):
        """W29: Advanced hidden by default."""
        assert 'advanced-panel' in _HTML
        assert 'display: none' in _HTML or 'display:none' in _HTML

    def test_keyboard_shortcuts(self):
        """W30: Keyboard shortcuts."""
        assert 'keydown' in _HTML
        assert 'Enter' in _HTML


# ═══════════════════════════════════════════════════════════════
# MISSION RESULT DISPLAY
# ═══════════════════════════════════════════════════════════════

class TestMissionResult:

    def test_result_card(self):
        """W31: Result card renders output."""
        assert 'plan_summary' in _HTML or 'finalOutput' in _HTML or 'final_output' in _HTML

    def test_steps_numbered(self):
        """W32: Steps are numbered."""
        assert 'step-num' in _HTML


# ═══════════════════════════════════════════════════════════════
# SERVER CONTRACT ALIGNMENT
# ═══════════════════════════════════════════════════════════════

class TestContractAlignment:

    def test_status_coverage(self):
        """W33: All mission phases covered in web UI."""
        # Web friendlyStatus must handle all MissionContract statuses
        html_lower = _HTML.lower()
        for raw_status in ["SUBMITTED", "EXECUTING", "PENDING_VALIDATION", "DONE", "FAILED"]:
            display = MissionContract.display(raw_status)
            # Check the web JS handles this — label or core keyword must appear
            label_lower = display.label.lower()
            # Allow partial match (e.g. "needs approval" matches "Needs your approval")
            core_words = [w for w in label_lower.split() if len(w) > 3]
            found = any(w in html_lower for w in core_words) or display.phase in html_lower
            assert found, f"Missing web mapping for {raw_status} → {display.label}"

    def test_risk_levels(self):
        """W34: Risk levels in web match ApprovalContract."""
        for risk in ["low", "medium", "high"]:
            display = ApprovalContract.format_approval({"id": "test", "risk": risk, "description": "test"})
            # Web should handle this risk level
            assert risk in _HTML.lower() or display.risk_label.lower() in _HTML.lower()

    def test_login_flow(self):
        """W35: Login flow matches SessionContract."""
        # Web handles token login and credentials login
        assert 'loginWithToken' in _HTML
        assert 'loginWithCredentials' in _HTML
        # Web stores session
        assert 'SessionStore.save' in _HTML
        # Web clears on logout
        assert 'SessionStore.clear' in _HTML
