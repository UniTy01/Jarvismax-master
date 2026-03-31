"""
JARVIS MAX — Token Management API Routes
==========================================
Admin-only endpoints for managing access tokens.

POST   /api/v3/tokens          — Create new token
GET    /api/v3/tokens          — List all tokens
GET    /api/v3/tokens/stats    — Token system stats
DELETE /api/v3/tokens/{id}     — Delete token
POST   /api/v3/tokens/{id}/revoke  — Revoke token
POST   /api/v3/tokens/{id}/enable  — Re-enable token
POST   /api/v3/tokens/validate     — Validate a token (any role)
"""
from __future__ import annotations

from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel
from typing import Optional

from api.auth import verify_token, has_permission
from api.access_tokens import get_token_manager

router = APIRouter(prefix="/api/v3/tokens", tags=["tokens"])


# ── Request models ──

class CreateTokenRequest(BaseModel):
    name: str
    role: str = "user"
    expires_days: int = 0
    max_uses: int = 0
    metadata: dict = {}


class ValidateTokenRequest(BaseModel):
    token: str


# ── Auth helper ──

def _require_admin(x_jarvis_token: Optional[str]) -> dict:
    """Require admin role for token management."""
    if not x_jarvis_token:
        raise HTTPException(status_code=401, detail="Authentication required")
    user = verify_token(x_jarvis_token)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid token")
    if not has_permission(user.get("role", ""), "manage_tokens"):
        raise HTTPException(status_code=403, detail="Admin access required")
    return user


def _require_auth(x_jarvis_token: Optional[str]) -> dict:
    """Require any valid auth."""
    if not x_jarvis_token:
        raise HTTPException(status_code=401, detail="Authentication required")
    user = verify_token(x_jarvis_token)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid token")
    return user


# ── Routes ──

@router.post("")
async def create_token(req: CreateTokenRequest,
                       x_jarvis_token: Optional[str] = Header(None)):
    """Create a new access token (admin only). Returns raw token ONCE."""
    _require_admin(x_jarvis_token)
    manager = get_token_manager()
    try:
        raw_token, token = manager.create_token(
            name=req.name,
            role=req.role,
            expires_days=req.expires_days,
            max_uses=req.max_uses,
            metadata=req.metadata,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return {
        "token": raw_token,
        "token_id": token.id,
        "name": token.name,
        "role": token.role,
        "expires_at": token.expires_at,
        "max_uses": token.max_uses,
        "message": "Save this token now — it will not be shown again.",
    }


@router.get("")
async def list_tokens(include_expired: bool = False,
                      x_jarvis_token: Optional[str] = Header(None)):
    """List all tokens (admin only). Never returns raw tokens."""
    _require_admin(x_jarvis_token)
    manager = get_token_manager()
    return {"tokens": manager.list_tokens(include_expired=include_expired)}


@router.get("/stats")
async def token_stats(x_jarvis_token: Optional[str] = Header(None)):
    """Token system statistics (admin only)."""
    _require_admin(x_jarvis_token)
    manager = get_token_manager()
    return manager.get_stats()


@router.delete("/{token_id}")
async def delete_token(token_id: str,
                       x_jarvis_token: Optional[str] = Header(None)):
    """Permanently delete a token (admin only)."""
    _require_admin(x_jarvis_token)
    manager = get_token_manager()
    if manager.delete_token(token_id):
        return {"status": "deleted", "token_id": token_id}
    raise HTTPException(status_code=404, detail="Token not found")


@router.post("/{token_id}/revoke")
async def revoke_token(token_id: str,
                       x_jarvis_token: Optional[str] = Header(None)):
    """Revoke (disable) a token (admin only)."""
    _require_admin(x_jarvis_token)
    manager = get_token_manager()
    if manager.revoke_token(token_id):
        return {"status": "revoked", "token_id": token_id}
    raise HTTPException(status_code=404, detail="Token not found")


@router.post("/{token_id}/enable")
async def enable_token(token_id: str,
                       x_jarvis_token: Optional[str] = Header(None)):
    """Re-enable a revoked token (admin only)."""
    _require_admin(x_jarvis_token)
    manager = get_token_manager()
    if manager.enable_token(token_id):
        return {"status": "enabled", "token_id": token_id}
    raise HTTPException(status_code=404, detail="Token not found")


@router.post("/validate")
async def validate_token_endpoint(req: ValidateTokenRequest,
                                  x_jarvis_token: Optional[str] = Header(None)):
    """Validate a token (any authenticated user)."""
    _require_auth(x_jarvis_token)
    manager = get_token_manager()
    token = manager.validate_token(req.token)
    if token:
        return {"valid": True, "role": token.role, "name": token.name}
    return {"valid": False}
