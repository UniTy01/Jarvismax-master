"""
JARVIS MAX — Security Headers Middleware
==========================================
Applies security headers to responses.

Policy:
- X-Frame-Options and X-Content-Type-Options: ALL responses
- Cache-Control no-store: auth + API JSON responses
- Strict CSP: API/JSON responses only (NOT /docs, /redoc, /openapi.json, /static, /)
- /docs and /redoc need inline scripts/styles for Swagger/ReDoc to render

This is intentionally scoped. Swagger UI and static HTML require relaxed CSP.
"""
from __future__ import annotations

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

# Paths that must NOT get strict CSP (they need inline JS/CSS)
_CSP_EXEMPT = frozenset({
    "/docs", "/redoc", "/openapi.json",
    "/", "/index.html", "/dashboard.html",
})

_CSP_EXEMPT_PREFIXES = ("/static/", "/docs/")


def _is_csp_exempt(path: str) -> bool:
    """Check if path should skip strict CSP."""
    if path in _CSP_EXEMPT:
        return True
    return any(path.startswith(p) for p in _CSP_EXEMPT_PREFIXES)


# Paths that should get no-store cache control
_NOCACHE_PREFIXES = ("/auth/", "/api/")


def _needs_nocache(path: str) -> bool:
    return any(path.startswith(p) for p in _NOCACHE_PREFIXES)


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Adds security headers to all responses."""

    async def dispatch(self, request: Request, call_next) -> Response:
        response = await call_next(request)
        path = request.url.path

        # Always: clickjacking + MIME sniffing protection
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-Content-Type-Options"] = "nosniff"

        # Auth/API routes: prevent caching of sensitive data
        if _needs_nocache(path):
            response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate"

        # Strict CSP: only for API/JSON responses, not docs/static
        if not _is_csp_exempt(path):
            response.headers["Content-Security-Policy"] = "default-src 'none'; frame-ancestors 'none'"

        return response
