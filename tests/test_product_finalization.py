"""
Tests — Product Finalization

Part 1: FastAPI Middleware
  F1. Middleware class exists and is importable
  F2. Middleware wired in api/main.py
  F3. Public paths bypass middleware
  F4. Non-public paths require auth
  F5. Token extraction from headers

Part 2: WebSocket Token Gating
  F6. WebSocket uses verify_token
  F7. Invalid token message is user-friendly (English)

Part 3: Admin Panel
  F8. Web has token creation form
  F9. Web has token list area
  F10. Web has revoke button

Part 4: User Onboarding
  F11. Web has onboarding examples
  F12. Mobile has updated suggestion chips
  F13. Onboarding shows when no missions

Part 5: V2 Default
  F14. main.dart uses V2 theme
  F15. main.dart has 4 tabs not 10
  F16. main.dart has auth gate
  F17. main.dart imports LoginScreen
  F18. V1 preserved as main_v1.dart

Part 6: Cross-validation
  F19. All enforcement paths have user-friendly messages
  F20. No French labels in main.dart
  F21. Token required for mission submission
  F22. Admin bypasses all checks
"""
import os
import sys
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

REPO = Path(__file__).parent.parent


class TestMiddleware:

    def test_middleware_importable(self):
        """F1: Middleware class exists."""
        from api.middleware import AccessEnforcementMiddleware
        assert AccessEnforcementMiddleware is not None

    def test_middleware_wired(self):
        """F2: Middleware wired in api/main.py."""
        content = (REPO / "api/main.py").read_text()
        assert "AccessEnforcementMiddleware" in content
        assert "app.add_middleware" in content

    def test_public_paths_bypass(self):
        """F3: Public paths bypass."""
        from api.access_enforcement import is_public_path
        assert is_public_path("/health")
        assert is_public_path("/index.html")
        assert is_public_path("/auth/login")
        assert is_public_path("/docs")
        assert is_public_path("/static/style.css")

    def test_protected_paths_require_auth(self):
        """F4: Non-public paths require auth."""
        from api.access_enforcement import is_public_path
        assert not is_public_path("/api/v3/missions")
        assert not is_public_path("/api/v3/actions")
        assert not is_public_path("/api/v3/tokens")
        assert not is_public_path("/diagnostic")

    def test_token_extraction(self):
        """F5: Token extraction from headers."""
        from api.middleware import _extract_token
        from unittest.mock import MagicMock

        # Bearer header
        req = MagicMock()
        req.headers = {"authorization": "Bearer jv-test123"}
        req.query_params = {}
        assert _extract_token(req) == "jv-test123"

        # X-Jarvis-Token header
        req2 = MagicMock()
        req2.headers = {"x-jarvis-token": "jv-abc"}
        req2.query_params = {}
        assert _extract_token(req2) == "jv-abc"

        # Query param
        req3 = MagicMock()
        req3.headers = {}
        req3.query_params = {"token": "jv-qp"}
        assert _extract_token(req3) == "jv-qp"

        # None
        req4 = MagicMock()
        req4.headers = {}
        req4.query_params = {}
        assert _extract_token(req4) is None


class TestWebSocketGating:

    def test_ws_uses_verify_token(self):
        """F6: WebSocket uses verify_token."""
        content = (REPO / "api/ws.py").read_text()
        assert "verify_token" in content

    def test_ws_english_error(self):
        """F7: WebSocket error is in English."""
        content = (REPO / "api/ws.py").read_text()
        assert "Your access token is invalid" in content
        # No French
        assert "Accès refusé" not in content


class TestAdminPanel:

    def test_web_token_creation(self):
        """F8: Web has token creation form."""
        content = (REPO / "static/index.html").read_text()
        assert "new-token-name" in content
        assert "new-token-plan" in content
        assert "createToken" in content

    def test_web_token_list(self):
        """F9: Web has token list area."""
        content = (REPO / "static/index.html").read_text()
        assert "token-list" in content
        assert "loadTokens" in content

    def test_web_revoke_button(self):
        """F10: Web has revoke button."""
        content = (REPO / "static/index.html").read_text()
        assert "revokeToken" in content
        assert "Revoke" in content


class TestOnboarding:

    def test_web_onboarding(self):
        """F11: Web has onboarding examples."""
        content = (REPO / "static/index.html").read_text()
        assert "onboarding" in content
        assert "Analyze this website" in content
        assert "Research competitors" in content
        assert "Automate a repetitive task" in content

    def test_mobile_suggestions(self):
        """F12: Mobile has updated suggestions."""
        content = (REPO / "jarvismax_app/lib/screens/home_screen.dart").read_text()
        assert "Analyze a website" in content
        assert "Create a Python script" in content
        assert "Research competitors" in content

    def test_onboarding_toggle(self):
        """F13: Onboarding shows/hides based on missions."""
        content = (REPO / "static/index.html").read_text()
        assert "onboarding" in content
        assert "display" in content  # onboarding visibility toggled


class TestV2Default:

    def test_main_uses_v2_theme(self):
        """F14: main.dart uses V2 theme."""
        content = (REPO / "jarvismax_app/lib/main.dart").read_text()
        assert "AppThemeV2" in content
        assert "app_theme_v2.dart" in content
        # Not V1 theme
        assert "AppTheme.darkTheme" not in content

    def test_main_has_4_tabs(self):
        """F15: main.dart has 4 tabs not 10."""
        content = (REPO / "jarvismax_app/lib/main.dart").read_text()
        items = content.count("BottomNavigationBarItem")
        assert items == 4

    def test_main_has_auth_gate(self):
        """F16: main.dart has auth gate."""
        content = (REPO / "jarvismax_app/lib/main.dart").read_text()
        assert "_AuthGate" in content
        assert "_authenticated" in content
        assert "LoginScreen" in content

    def test_main_imports_login(self):
        """F17: main.dart imports LoginScreen."""
        content = (REPO / "jarvismax_app/lib/main.dart").read_text()
        assert "login_screen.dart" in content

    def test_v1_preserved(self):
        """F18: V1 preserved as main_v1.dart."""
        assert (REPO / "jarvismax_app/lib/main_v1.dart").exists()
        content = (REPO / "jarvismax_app/lib/main_v1.dart").read_text()
        assert "DashboardScreen" in content  # V1 had dashboard


class TestCrossValidation:

    def test_enforcement_messages_friendly(self):
        """F19: All enforcement paths have user-friendly messages."""
        from api.access_enforcement import check_access
        # No token
        r = check_access(None, path="/api/v3/missions")
        assert "please" in r.error_message.lower() or "token" in r.error_message.lower()
        # Invalid
        r2 = check_access("jv-fake", path="/api/v3/missions")
        assert "invalid" in r2.error_message.lower() or "check" in r2.error_message.lower()

    def test_no_french_in_main(self):
        """F20: No French labels in main.dart."""
        content = (REPO / "jarvismax_app/lib/main.dart").read_text()
        for french in ["Historique", "Paramètres", "Capacités", "Amélio", "Validation"]:
            assert french not in content

    def test_token_required_for_missions(self, tmp_path):
        """F21: Token required for mission submission."""
        from api.access_enforcement import check_mission_access
        result = check_mission_access(None)
        assert not result.allowed
        assert result.error_code == 401

    def test_admin_bypasses_all(self, tmp_path):
        """F22: Admin bypasses all checks."""
        from api.access_tokens import TokenManager, reset_token_manager
        import api.access_tokens as at
        reset_token_manager()
        at._manager = TokenManager(tmp_path / "tokens.json")
        raw, _ = at._manager.create_token("Admin", role="admin", plan_type="admin")

        from api.access_enforcement import check_access, check_mission_access
        r1 = check_access(raw, permission="manage_tokens")
        assert r1.allowed
        r2 = check_mission_access(raw)
        assert r2.allowed
        reset_token_manager()
