"""JWT authentication helpers."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

import jwt
import structlog
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.config import get_settings

logger = structlog.get_logger(__name__)
security = HTTPBearer()


def create_access_token(client_id: str) -> str:
    """Create a JWT for the given client."""
    try:
        settings = get_settings()
        expire = datetime.now(timezone.utc) + timedelta(minutes=settings.jwt_expire_minutes)
        payload = {"sub": client_id, "exp": expire}
        return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)
    except Exception as exc:
        logger.error("token_create_failed", error=str(exc))
        raise RuntimeError(f"Failed to create token: {exc}") from exc


async def get_current_client(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> str:
    """Validate JWT and return the client_id."""
    try:
        settings = get_settings()
        payload: dict[str, Any] = jwt.decode(
            credentials.credentials,
            settings.jwt_secret,
            algorithms=[settings.jwt_algorithm],
        )
        client_id = payload.get("sub")
        if not client_id:
            raise ValueError("Missing client_id in token")
        return str(client_id)
    except jwt.PyJWTError as exc:
        logger.error("jwt_decode_failed", error=str(exc))
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        ) from exc
    except Exception as exc:
        logger.error("auth_failed", error=str(exc))
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication failed",
        ) from exc
