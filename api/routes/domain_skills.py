"""
api/routes/domain_skills.py — Domain skill registry API.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from api._deps import require_auth

router = APIRouter(prefix="/api/v3/skills", tags=["domain-skills"])


@router.get("")
async def list_skills(_user: dict = Depends(require_auth)):
    """List all registered domain skills."""
    from core.skills.domain_loader import get_domain_registry
    skills = get_domain_registry().list_all()
    return {"ok": True, "data": [s.to_dict() for s in skills]}


@router.get("/stats")
async def skill_stats(_user: dict = Depends(require_auth)):
    from core.skills.domain_loader import get_domain_registry
    return {"ok": True, "data": get_domain_registry().stats()}


@router.get("/chains")
async def list_chains(_user: dict = Depends(require_auth)):
    from core.skills.skill_chain import list_chains
    return {"ok": True, "data": list_chains()}


@router.get("/{skill_id}")
async def get_skill(skill_id: str, _user: dict = Depends(require_auth)):
    from core.skills.domain_loader import get_domain_registry
    skill = get_domain_registry().get(skill_id)
    if not skill:
        raise HTTPException(404, f"Skill not found: {skill_id}")
    return {"ok": True, "data": skill.to_dict()}


@router.get("/{skill_id}/feedback")
async def skill_feedback(skill_id: str, _user: dict = Depends(require_auth)):
    from core.skills.skill_feedback import get_feedback_store
    return {"ok": True, "data": get_feedback_store().get_summary(skill_id)}
