"""
api/routes/security_audit.py — Security governance observability endpoints (Pass 31).

R3/R10: security is native, not decorative.
These endpoints expose the SecurityLayer audit trail and active policy rules
so operators can verify governance without direct file access.

Routes:
    GET  /api/v3/security/rules          — active PolicyRules (first-match list)
    GET  /api/v3/security/audit          — recent audit entries (n last)
    GET  /api/v3/security/audit/mission/{mission_id} — audit for a mission
    GET  /api/v3/security/status         — SecurityLayer health snapshot
    POST /api/v3/security/check          — ad-hoc action check (dry-run)

All endpoints are fail-open: return degraded response on SecurityLayer error.
"""
from __future__ import annotations

import structlog
from fastapi import APIRouter, Depends, Query

log = structlog.get_logger("api.security_audit")

router = APIRouter(prefix="/api/v3/security", tags=["security"])


def _auth():
    try:
        from api._deps import require_auth
        return require_auth
    except Exception:
        return lambda: None


# ── Policy Rules (R3) ─────────────────────────────────────────────────────────

@router.get("/rules")
async def list_security_rules(user=Depends(_auth())):
    """
    List all active PolicyRules (first-match semantics, R3).

    Returns each rule's id, trigger conditions, enforcement action, and enabled status.
    """
    try:
        from security import get_security_layer
        layer = get_security_layer()
        rules = []
        # BLOC 4 fix: PolicyRule fields are action_types, min_risk_level, modes.
        # The original code used nonexistent attributes (action_pattern, risk_level,
        # applies_to_mode, priority), causing AttributeError on every call.
        for rule in layer.active_rules():
            rules.append({
                "rule_id":        rule.rule_id,
                "description":    rule.description,
                "action_types":   rule.action_types,     # list[str], empty = all
                "min_risk_level": rule.min_risk_level,   # "low"|"medium"|"high"|"critical"
                "modes":          rule.modes,            # list[str], empty = all
                "enforcement":    rule.enforcement.value,
                "enabled":        rule.enabled,
            })
        return {"rules": rules, "count": len(rules), "semantics": "first-match"}
    except Exception as e:
        log.warning("security_rules_api_error", err=str(e)[:100])
        return {"error": str(e)[:200], "rules": [], "count": 0}


# ── Audit Trail (R10) ─────────────────────────────────────────────────────────

@router.get("/audit")
async def recent_audit_entries(
    n: int = Query(default=50, ge=1, le=500),
    user=Depends(_auth()),
):
    """
    Return the N most recent immutable audit entries (R10).

    AuditEntry fields: entry_id, timestamp, mission_id, action_type,
    action_target, risk_level, decision, reason, decided_by.
    """
    try:
        from security.audit.trail import get_audit_trail
        trail = get_audit_trail()
        entries = []
        for e in trail.recent(n=n):
            entries.append({
                "entry_id":     e.entry_id,
                "timestamp":    e.timestamp,
                "mission_id":   e.mission_id,
                "action_type":  e.action_type,
                "action_target": e.action_target,
                "risk_level":   e.risk_level,
                "decision":     e.decision.value if hasattr(e.decision, "value") else str(e.decision),
                "reason":       e.reason,
                "decided_by":   e.decided_by,
            })
        return {"entries": entries, "count": len(entries), "requested": n}
    except Exception as e:
        log.warning("security_audit_api_error", err=str(e)[:100])
        return {"error": str(e)[:200], "entries": [], "count": 0}


@router.get("/audit/mission/{mission_id}")
async def audit_by_mission(mission_id: str, user=Depends(_auth())):
    """
    Return all audit entries for a specific mission (R10).

    Useful for post-execution audit: what security decisions were taken?
    """
    try:
        from security.audit.trail import get_audit_trail
        trail = get_audit_trail()
        entries = []
        for e in trail.by_mission(mission_id):
            entries.append({
                "entry_id":     e.entry_id,
                "timestamp":    e.timestamp,
                "action_type":  e.action_type,
                "action_target": e.action_target,
                "risk_level":   e.risk_level,
                "decision":     e.decision.value if hasattr(e.decision, "value") else str(e.decision),
                "reason":       e.reason,
                "decided_by":   e.decided_by,
            })
        return {"mission_id": mission_id, "entries": entries, "count": len(entries)}
    except Exception as e:
        log.warning("security_audit_mission_api_error", err=str(e)[:100])
        return {"error": str(e)[:200], "entries": [], "count": 0}


# ── SecurityLayer Status ──────────────────────────────────────────────────────

@router.get("/status")
async def security_status(user=Depends(_auth())):
    """
    SecurityLayer health snapshot.

    Returns: active_rules count, audit_trail_size, last_check details.
    """
    try:
        from security import get_security_layer
        from security.audit.trail import get_audit_trail
        layer = get_security_layer()
        trail = get_audit_trail()

        recent = trail.recent(n=1)
        last_entry = None
        if recent:
            e = recent[0]
            last_entry = {
                "timestamp":   e.timestamp,
                "action_type": e.action_type,
                "decision":    e.decision.value if hasattr(e.decision, "value") else str(e.decision),
            }

        return {
            "active_rules":     len(layer.active_rules()),
            "audit_trail_size": len(trail.recent(n=10000)),  # full count approximation
            "last_audit_entry": last_entry,
            "security_layer":   "SecurityLayer",
            "status":           "operational",
        }
    except Exception as e:
        log.warning("security_status_api_error", err=str(e)[:100])
        return {"error": str(e)[:200], "status": "degraded"}


# ── Ad-hoc Security Check (dry-run) ──────────────────────────────────────────

@router.post("/check")
async def security_check(
    action_type: str,
    mission_id: str = "",
    risk_level: str = "low",
    mode: str = "auto",
    action_target: str = "",
    user=Depends(_auth()),
):
    """
    Perform an ad-hoc security check (R3/R10).

    This DOES create an audit entry — it is not a pure dry-run.
    Use for testing policy rules or pre-validating actions.
    """
    try:
        from security import get_security_layer
        layer = get_security_layer()
        result = layer.check_action(
            action_type=action_type,
            mission_id=mission_id or "api-check",
            mode=mode,
            risk_level=risk_level,
            action_target=action_target,
        )
        return {
            "allowed":    result.allowed,
            "reason":     result.reason,
            "escalated":  result.escalated,
            "risk_level": result.risk_level,
            "action_type": action_type,
        }
    except Exception as e:
        log.warning("security_check_api_error", err=str(e)[:100])
        return {"error": str(e)[:200], "allowed": True, "reason": "security_layer_error_fail_open"}
