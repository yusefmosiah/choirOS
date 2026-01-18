"""Attach auth session context to FastAPI requests when present."""

from __future__ import annotations

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

from .auth import extract_session_token, get_auth_store


class AuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        token = extract_session_token(request.headers)
        if token:
            session = get_auth_store().verify_session(token)
            if session:
                request.state.auth = session
        return await call_next(request)
