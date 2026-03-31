"""Tests for core/env_validator.py — environment validation."""


def test_import():
    from core.env_validator import (
        validate_environment, get_env_report,
        CheckResult, EnvReport,
        check_python_version, check_required_imports,
        check_optional_imports, check_requirements_file,
    )


# ── CheckResult ───────────────────────────────────────────────

def test_check_result_to_dict():
    from core.env_validator import CheckResult
    c = CheckResult(name="test", passed=True, detail="ok")
    d = c.to_dict()
    assert d["name"] == "test"
    assert d["passed"] is True


# ── EnvReport ─────────────────────────────────────────────────

def test_report_passed_no_errors():
    from core.env_validator import EnvReport, CheckResult
    r = EnvReport(checks=[CheckResult("a", True)], warnings=["warn"])
    assert r.passed is True  # warnings don't fail


def test_report_failed_with_errors():
    from core.env_validator import EnvReport
    r = EnvReport(errors=["critical issue"])
    assert r.passed is False


def test_report_summary():
    from core.env_validator import EnvReport, CheckResult
    r = EnvReport(checks=[CheckResult("a", True), CheckResult("b", False)])
    assert "1/2" in r.summary


def test_report_to_dict():
    from core.env_validator import EnvReport
    r = EnvReport()
    d = r.to_dict()
    assert "passed" in d
    assert "summary" in d
    assert "checks" in d


# ── Individual checks ─────────────────────────────────────────

def test_python_version_passes():
    from core.env_validator import check_python_version
    result = check_python_version()
    assert result.passed  # we're running Python 3.10+


def test_required_imports_all_pass():
    from core.env_validator import check_required_imports
    results = check_required_imports()
    # All stdlib modules should be available
    for r in results:
        assert r.passed, f"Required module failed: {r.detail}"


def test_optional_imports_never_fail():
    from core.env_validator import check_optional_imports
    results = check_optional_imports()
    # Optional imports should always "pass" (warnings, not errors)
    for r in results:
        assert r.passed, f"Optional import should not fail: {r.name}"
        assert r.severity in ("info", "warning")


def test_requirements_file():
    from core.env_validator import check_requirements_file
    result = check_requirements_file()
    # Should not error even if file doesn't exist
    assert result.passed or result.severity == "warning"


# ── Full validation ───────────────────────────────────────────

def test_validate_environment_returns_report():
    from core.env_validator import validate_environment
    report = validate_environment()
    assert hasattr(report, "checks")
    assert hasattr(report, "warnings")
    assert hasattr(report, "errors")
    assert len(report.checks) > 0


def test_validate_environment_never_raises():
    """validate_environment must never raise, even in broken environments."""
    from core.env_validator import validate_environment
    # This should always succeed
    report = validate_environment()
    assert report is not None


def test_get_env_report_returns_dict():
    from core.env_validator import get_env_report
    d = get_env_report()
    assert isinstance(d, dict)
    assert "passed" in d
    assert "summary" in d
