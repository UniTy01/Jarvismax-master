"""
Tests — UX Redesign

Validates the redesigned user experience across mobile and web.

Phase 1-2: Structure
  U1. Theme V2 has warm neutral colors (no neon cyan)
  U2. 4-tab navigation (Home, Approvals, History, Settings)
  U3. Simple vs Advanced mode separation

Phase 3: Main Screen
  U4. Home screen has input card
  U5. Suggestion chips present
  U6. Friendly status mapping

Phase 4-5: Mission + Approval UX
  U7. Mission progress shows friendly status
  U8. Approval cards show risk level in human terms
  U9. All technical statuses have friendly equivalents

Phase 6: Web Frontend
  U10. index.html exists and is well-formed
  U11. Web frontend has same 4 pages as mobile
  U12. Web connects to real API (not mock)

Phase 7: Simple vs Advanced
  U13. Settings screen has advanced toggle
  U14. Technical labels not in simple mode

Phase 8: Wording
  U15. No French labels in V2 screens
  U16. No internal jargon in user-facing text

Phase 9-10: Design + Consistency
  U17. Color palette is warm (no neon)
  U18. Mobile and web share same status vocabulary

Phase 11: Runtime
  U19. Web frontend sends real API calls
  U20. Root URL serves index.html
"""
import os
import sys
import re
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

REPO = Path(__file__).parent.parent


class TestThemeAndStructure:

    def test_theme_v2_no_neon_cyan(self):
        """U1: Theme V2 uses warm neutrals, not neon cyan."""
        theme = (REPO / "jarvismax_app/lib/theme/app_theme_v2.dart").read_text()
        # No neon cyan (0xFF00E5FF)
        assert "00E5FF" not in theme
        # Has calm blue accent
        assert "4F8CFF" in theme
        # Has warm dark bg (not 0A0E1A hacker blue)
        assert "101114" in theme

    def test_four_tab_navigation(self):
        """U2: V2 main has exactly 4 bottom nav tabs."""
        main_v2 = (REPO / "jarvismax_app/lib/main_v2.dart").read_text()
        assert "HomeScreen()" in main_v2
        assert "ApprovalsScreen()" in main_v2
        assert "HistoryScreenV2()" in main_v2
        assert "SettingsScreenV2()" in main_v2
        # Count BottomNavigationBarItem
        items = main_v2.count("BottomNavigationBarItem")
        assert items == 4

    def test_simple_vs_advanced(self):
        """U3: Settings has advanced mode toggle."""
        settings = (REPO / "jarvismax_app/lib/screens/settings_screen_v2.dart").read_text()
        assert "_advancedMode" in settings
        assert "Advanced mode" in settings
        assert "Show technical details" in settings


class TestMainScreen:

    def test_home_has_input(self):
        """U4: Home screen has the main input card."""
        home = (REPO / "jarvismax_app/lib/screens/home_screen.dart").read_text()
        assert "What do you want Jarvis to do?" in home
        assert "_InputCard" in home

    def test_suggestion_chips(self):
        """U5: Suggestion chips are present and in English."""
        home = (REPO / "jarvismax_app/lib/screens/home_screen.dart").read_text()
        assert "_suggestions" in home
        assert "Create a performance report" in home

    def test_friendly_status_mapping(self):
        """U6: All statuses have friendly equivalents."""
        home = (REPO / "jarvismax_app/lib/screens/home_screen.dart").read_text()
        assert "'Done'" in home
        assert "'Error'" in home
        assert "'Needs your approval'" in home
        assert "'Working'" in home
        assert "'Waiting'" in home
        assert "'Analyzing'" in home
        assert "'Searching'" in home


class TestMissionAndApproval:

    def test_mission_progress_friendly(self):
        """U7: Mission progress uses friendly status."""
        home = (REPO / "jarvismax_app/lib/screens/home_screen.dart").read_text()
        assert "_friendlyStatus" in home
        assert "_MissionProgress" in home

    def test_approval_shows_risk(self):
        """U8: Approval cards show risk in human terms."""
        approvals = (REPO / "jarvismax_app/lib/screens/approvals_screen.dart").read_text()
        assert "'High risk'" in approvals
        assert "'Medium risk'" in approvals
        assert "'Low risk'" in approvals
        assert "Jarvis wants to:" in approvals

    def test_all_statuses_mapped(self):
        """U9: Technical statuses all have friendly equivalents."""
        home = (REPO / "jarvismax_app/lib/screens/home_screen.dart").read_text()
        # Ensure mapping handles: done, failed, pending, executing, submitted
        for keyword in ["done", "failed", "pending", "executing", "submitted"]:
            assert keyword in home.lower()


class TestWebFrontend:

    def test_index_html_exists(self):
        """U10: index.html exists and is well-formed."""
        index = REPO / "static/index.html"
        assert index.exists()
        content = index.read_text()
        assert "<!DOCTYPE html>" in content
        assert "</html>" in content
        assert "<title>Jarvis</title>" in content

    def test_web_has_4_pages(self):
        """U11: Web frontend has same 4 pages as mobile."""
        content = (REPO / "static/index.html").read_text()
        assert 'id="page-home"' in content
        assert 'id="page-approvals"' in content
        assert 'id="page-history"' in content
        assert 'id="page-settings"' in content

    def test_web_uses_real_api(self):
        """U12: Web frontend connects to real API endpoints."""
        content = (REPO / "static/index.html").read_text()
        assert "/health" in content
        assert "/api/v3/missions" in content or "/api/missions" in content
        assert "/api/v3/actions" in content or "/api/actions" in content
        assert "/auth/login" in content


class TestSimpleVsAdvanced:

    def test_settings_advanced_toggle(self):
        """U13: Settings has advanced toggle that hides details."""
        settings = (REPO / "jarvismax_app/lib/screens/settings_screen_v2.dart").read_text()
        assert "if (_advancedMode)" in settings
        # Technical items only in advanced block
        assert "'View model routing'" in settings
        assert "'View metrics'" in settings
        assert "'Self-improvement status'" in settings

    def test_no_technical_labels_simple_mode(self):
        """U14: Home and Approvals screens have no internal jargon."""
        home = (REPO / "jarvismax_app/lib/screens/home_screen.dart").read_text()
        approvals = (REPO / "jarvismax_app/lib/screens/approvals_screen.dart").read_text()
        for jargon in ["orchestrator", "tool_executor", "pending_validation",
                        "trace intelligence", "route dispatch", "PENDING_VALIDATION"]:
            assert jargon not in home, f"Jargon '{jargon}' found in home_screen"
            assert jargon not in approvals, f"Jargon '{jargon}' found in approvals_screen"


class TestWording:

    def test_no_french_in_v2(self):
        """U15: No French labels in V2 screens."""
        for fname in ["home_screen.dart", "approvals_screen.dart",
                       "history_screen_v2.dart", "settings_screen_v2.dart", "main_v2.dart"]:
            path = REPO / "jarvismax_app/lib/screens" / fname
            if not path.exists():
                path = REPO / "jarvismax_app/lib" / fname
            content = path.read_text()
            for french in ["Nouvelle Mission", "COMMANDE", "ÉTAPES", "EN ATTENTE",
                            "Historique", "Paramètres", "Amélio", "Capacités",
                            "ENVOYER", "REFUSER", "APPROUVER"]:
                assert french not in content, f"French '{french}' in {fname}"

    def test_no_internal_jargon(self):
        """U16: No internal jargon in user-facing text."""
        web = (REPO / "static/index.html").read_text()
        for jargon in ["orchestrator", "tool executor", "PENDING_VALIDATION",
                        "trace intelligence", "advisory score"]:
            assert jargon.lower() not in web.lower(), f"Jargon '{jargon}' in web frontend"


class TestDesignConsistency:

    def test_warm_palette(self):
        """U17: Color palette is warm, no neon."""
        theme = (REPO / "jarvismax_app/lib/theme/app_theme_v2.dart").read_text()
        web = (REPO / "static/index.html").read_text()
        # Both use similar accent blue
        assert "4F8CFF" in theme
        assert "4F8CFF" in web

    def test_same_status_vocabulary(self):
        """U18: Mobile and web share same status words."""
        web = (REPO / "static/index.html").read_text()
        home = (REPO / "jarvismax_app/lib/screens/home_screen.dart").read_text()
        for status in ["Done", "Error", "Needs approval", "Working", "Waiting"]:
            assert status in web, f"Status '{status}' missing from web"
            # Check mobile (may have slight variation like "Needs your approval")
            assert status in home or status.replace("approval", "your approval") in home


class TestRuntime:

    def test_web_real_api_calls(self):
        """U19: Web frontend makes real API calls."""
        web = (REPO / "static/index.html").read_text()
        assert "fetch(" in web
        assert "async function" in web
        assert "submitMission" in web
        assert "approveAction" in web

    def test_root_serves_index(self):
        """U20: Root URL redirects to index.html."""
        main_py = (REPO / "api/main.py").read_text()
        assert 'url="/index.html"' in main_py
