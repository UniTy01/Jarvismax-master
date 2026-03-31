"""Edge case tests for core/execution_policy.py."""


def test_all_action_types_covered():
    """Every defined action type should produce a valid decision."""
    from core.execution_policy import ExecutionPolicy, ActionContext, ACTION_TYPES
    ep = ExecutionPolicy()
    for action in ACTION_TYPES:
        for mode in ["MANUAL", "SUPERVISED", "AUTO"]:
            ctx = ActionContext(
                mission_type="test", risk_score=5, complexity="medium",
                agent="test", action_type=action, estimated_impact="medium",
                mode=mode,
            )
            result = ep.evaluate(ctx)
            assert result.decision in ("AUTO_APPROVED", "REQUIRES_APPROVAL", "BLOCKED")
            assert isinstance(result.approved, bool)
            assert isinstance(result.reason, str)


def test_risk_score_boundary_supervised():
    """Risk score 3 should be auto-approved, 4 should require approval in SUPERVISED."""
    from core.execution_policy import ExecutionPolicy, ActionContext
    ep = ExecutionPolicy()
    # Risk 3 + safe action = approved
    ctx3 = ActionContext(
        mission_type="test", risk_score=3, complexity="low",
        agent="test", action_type="read", estimated_impact="low",
        mode="SUPERVISED",
    )
    assert ep.evaluate(ctx3).approved is True
    # Risk 4 + safe action = requires approval
    ctx4 = ActionContext(
        mission_type="test", risk_score=4, complexity="low",
        agent="test", action_type="read", estimated_impact="low",
        mode="SUPERVISED",
    )
    assert ep.evaluate(ctx4).approved is False


def test_auto_risk_thresholds():
    """Verify each action type respects its specific risk threshold in AUTO."""
    from core.execution_policy import ExecutionPolicy, ActionContext, _AUTO_RISK_THRESHOLD
    ep = ExecutionPolicy()
    for action, threshold in _AUTO_RISK_THRESHOLD.items():
        if threshold == 0:
            continue  # critical actions — tested separately
        # At threshold: should be approved (if not high impact)
        ctx_at = ActionContext(
            mission_type="test", risk_score=threshold, complexity="low",
            agent="test", action_type=action, estimated_impact="low",
            mode="AUTO",
        )
        result_at = ep.evaluate(ctx_at)
        assert result_at.approved is True, f"{action} at threshold {threshold} should be approved"
        # Above threshold: should require approval
        ctx_above = ActionContext(
            mission_type="test", risk_score=threshold + 1, complexity="low",
            agent="test", action_type=action, estimated_impact="low",
            mode="AUTO",
        )
        result_above = ep.evaluate(ctx_above)
        assert result_above.approved is False, f"{action} above threshold should need approval"


def test_fail_open_on_internal_error():
    """If evaluate() has an internal error, it should return REQUIRES_APPROVAL, not crash."""
    from core.execution_policy import ExecutionPolicy
    ep = ExecutionPolicy()
    # Pass None as ctx — should trigger internal error path
    # The fail-open wraps _evaluate, so let's test with a broken context
    class BrokenContext:
        risk_score = None  # will cause TypeError in comparison
        action_type = "read"
        mode = "AUTO"
        estimated_impact = "low"
    result = ep.evaluate(BrokenContext())
    assert not result.approved
    assert result.decision == "REQUIRES_APPROVAL"
    assert "internal_error" in result.reason


def test_risk_score_extremes():
    """Risk scores at 0 and 10 should work correctly."""
    from core.execution_policy import ExecutionPolicy, ActionContext
    ep = ExecutionPolicy()
    # Risk 0, AUTO, read = definitely approved
    ctx0 = ActionContext(
        mission_type="test", risk_score=0, complexity="low",
        agent="test", action_type="read", estimated_impact="low",
        mode="AUTO",
    )
    assert ep.evaluate(ctx0).approved is True
    # Risk 10, AUTO, write = definitely not approved
    ctx10 = ActionContext(
        mission_type="test", risk_score=10, complexity="high",
        agent="test", action_type="write", estimated_impact="high",
        mode="AUTO",
    )
    assert ep.evaluate(ctx10).approved is False
