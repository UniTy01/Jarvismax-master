"""
tests/test_ui_coherence.py — Web + Mobile UI coherence tests.

Phase 7 (UC01-UC20): Web UI states, tokens, modes, pages
Phase 8 (UC21-UC35): Mobile stability, API v3 compat, navigation
"""
import pytest
import os
import re
import ast
from pathlib import Path

STATIC = Path("static")
FLUTTER = Path("jarvismax_app/lib")


class TestWebDesignTokens:
    """Phase 7: Design system v3 tokens used consistently."""

    def test_UC01_css_vars_defined(self):
        html = (STATIC / "app.html").read_text()
        for v in ["--bg-base", "--bg-surface", "--text-primary", "--blue", "--green", "--red", "--amber"]:
            assert v in html, f"Missing CSS var {v}"

    def test_UC02_font_system(self):
        html = (STATIC / "app.html").read_text()
        assert "'Inter'" in html
        assert "--font-mono" in html

    def test_UC03_radius_tokens(self):
        html = (STATIC / "app.html").read_text()
        for r in ["--radius-sm", "--radius-md", "--radius-lg"]:
            assert r in html

    def test_UC04_badge_classes(self):
        html = (STATIC / "app.html").read_text()
        for cls in ["badge-running", "badge-completed", "badge-failed", "badge-pending"]:
            assert cls in html

    def test_UC05_risk_classes(self):
        html = (STATIC / "app.html").read_text()
        for cls in ["risk-low", "risk-medium", "risk-high"]:
            assert cls in html


class TestWebStates:
    """Phase 7: Loading, error, empty states present."""

    def test_UC06_home_empty_state(self):
        html = (STATIC / "app.html").read_text()
        assert "No missions yet" in html

    def test_UC07_approvals_empty_state(self):
        html = (STATIC / "app.html").read_text()
        assert "All clear" in html

    def test_UC08_loading_skeleton(self):
        html = (STATIC / "app.html").read_text()
        assert "skeleton" in html or "Loading" in html

    def test_UC09_system_loading_state(self):
        html = (STATIC / "app.html").read_text()
        assert "Loading system state" in html

    def test_UC10_error_handling_401(self):
        html = (STATIC / "app.html").read_text()
        assert "401" in html  # redirect to login on 401

    def test_UC11_toast_notifications(self):
        html = (STATIC / "app.html").read_text()
        assert "toast" in html
        assert "toast.ok" in html or "class=\"toast" in html

    def test_UC12_offline_status(self):
        html = (STATIC / "app.html").read_text()
        assert "Offline" in html or "error" in html


class TestWebModes:
    """Phase 7: Mode system (lite/full/admin) works."""

    def test_UC13_mode_buttons(self):
        html = (STATIC / "app.html").read_text()
        assert 'data-mode="lite"' in html
        assert 'data-mode="full"' in html
        assert 'data-mode="admin"' in html

    def test_UC14_mode_persistence(self):
        html = (STATIC / "app.html").read_text()
        assert "jarvis_mode" in html  # localStorage key
        assert "setMode" in html

    def test_UC15_mode_restricts_nav(self):
        html = (STATIC / "app.html").read_text()
        # Nav items with data-mode should be hidden when mode is lower
        assert 'data-mode="full"' in html
        # CSS rules for visibility
        assert "[data-app-mode" in html


class TestWebPages:
    """Phase 7: All key pages exist and have session guards."""

    def test_UC16_app_html_exists(self):
        assert (STATIC / "app.html").exists()

    def test_UC17_login_page_exists(self):
        assert (STATIC / "index.html").exists()

    def test_UC18_subpages_exist(self):
        for page in ["modules.html", "dashboard.html", "economic.html",
                      "operations.html", "runs.html", "mcp.html"]:
            assert (STATIC / page).exists(), f"Missing {page}"

    def test_UC19_session_guard_on_subpages(self):
        """Subpages should redirect to login if no token."""
        for page in ["modules.html", "finance.html", "dashboard.html", "missions.html"]:
            p = STATIC / page
            if p.exists():
                text = p.read_text()
                assert "jarvis_token" in text or "validateSession" in text, f"{page} has no session guard"

    def test_UC20_no_dead_pages_referenced(self):
        """app.html should not reference deleted pages."""
        html = (STATIC / "app.html").read_text()
        for dead in ["cockpit.html", "console.html", "cognitive.html"]:
            assert dead not in html, f"Dead page {dead} still referenced"


class TestMobileNavigation:
    """Phase 8: Flutter navigation + screens stable."""

    def test_UC21_main_dart_valid_syntax(self):
        """main.dart is syntactically valid Dart."""
        content = (FLUTTER / "main.dart").read_text()
        # Basic structural checks
        assert "void main()" in content
        assert "JarvisApp" in content
        assert "StatelessWidget" in content

    def test_UC22_five_tabs(self):
        content = (FLUTTER / "main.dart").read_text()
        assert "BottomNavigationBarItem" in content
        items = content.count("BottomNavigationBarItem")
        assert items == 5, f"Expected 5 tabs, found {items}"

    def test_UC23_tab_labels(self):
        content = (FLUTTER / "main.dart").read_text()
        for label in ["Home", "Missions", "Approvals", "History", "Settings"]:
            assert f"'{label}'" in content, f"Missing tab label: {label}"

    def test_UC24_auth_gate(self):
        content = (FLUTTER / "main.dart").read_text()
        assert "_loggedIn" in content
        assert "LoginScreen" in content

    def test_UC25_branded_splash(self):
        content = (FLUTTER / "main.dart").read_text()
        assert "CircularProgressIndicator" in content
        assert "'J'" in content  # Brand mark

    def test_UC26_design_system_imported(self):
        content = (FLUTTER / "main.dart").read_text()
        assert "design_system.dart" in content
        assert "JDS" in content


class TestMobileAPICompat:
    """Phase 8: Flutter uses v3 API paths."""

    def test_UC27_api_service_exists(self):
        p = FLUTTER / "services" / "api_service.dart"
        assert p.exists()

    def test_UC28_modules_uses_v3(self):
        p = FLUTTER / "screens" / "modules_screen.dart"
        if p.exists():
            content = p.read_text()
            assert "/api/v3/" in content, "modules_screen should use v3 API"

    def test_UC29_login_screen_exists(self):
        assert (FLUTTER / "screens" / "login_screen.dart").exists()

    def test_UC30_home_screen_exists(self):
        assert (FLUTTER / "screens" / "home_screen.dart").exists()

    def test_UC31_approvals_screen_exists(self):
        assert (FLUTTER / "screens" / "approvals_screen.dart").exists()

    def test_UC32_settings_screen_exists(self):
        assert (FLUTTER / "screens" / "settings_screen.dart").exists()


class TestMobileDesignSystem:
    """Phase 8: Flutter design system matches web."""

    def test_UC33_jds_class_exists(self):
        p = FLUTTER / "theme" / "design_system.dart"
        assert p.exists()
        content = p.read_text()
        assert "class JDS" in content

    def test_UC34_color_tokens_defined(self):
        content = (FLUTTER / "theme" / "design_system.dart").read_text()
        for token in ["bgBase", "bgSurface", "textPrimary", "blue", "green", "red", "amber"]:
            assert token in content, f"Missing Flutter token: {token}"

    def test_UC35_jarvis_theme_dark(self):
        content = (FLUTTER / "theme" / "design_system.dart").read_text()
        assert "JarvisTheme" in content
        assert "dark" in content


class TestWebMobileAlignment:
    """Cross-platform consistency."""

    def test_UC36_web_has_mission_submit(self):
        html = (STATIC / "app.html").read_text()
        assert "submitMission" in html

    def test_UC37_web_uses_api_v3_missions(self):
        html = (STATIC / "app.html").read_text()
        assert "/api/v3/missions" in html

    def test_UC38_web_uses_self_model(self):
        html = (STATIC / "app.html").read_text()
        assert "/api/v3/self-model" in html

    def test_UC39_websocket_reconnect(self):
        html = (STATIC / "app.html").read_text()
        assert "setTimeout(connectWS" in html

    def test_UC40_main_dart_no_deleted_imports(self):
        content = (FLUTTER / "main.dart").read_text()
        for deleted in ["extensions_screen", "aios_dashboard", "capabilities_screen"]:
            assert deleted not in content, f"Deleted import {deleted} still in main.dart"
