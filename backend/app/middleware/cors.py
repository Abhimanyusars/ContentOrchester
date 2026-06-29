"""CORS middleware — explicit Vercel + configured origin support."""

from __future__ import annotations

from collections.abc import Awaitable, Callable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from app.config import get_settings

RequestResponseEndpoint = Callable[[Request], Awaitable[Response]]


def _origin_allowed(origin: str | None, allowed: list[str]) -> bool:
    if not origin:
        return False
    if origin in allowed:
        return True
    return origin.startswith("https://") and ".vercel.app" in origin


class VercelCORSMiddleware(BaseHTTPMiddleware):
    """Echo Access-Control-Allow-Origin for Vercel and configured origins."""

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        origin = request.headers.get("origin")
        settings = get_settings()
        allowed = settings.cors_origin_list

        if _origin_allowed(origin, allowed):
            if request.method == "OPTIONS":
                return Response(
                    status_code=204,
                    headers={
                        "Access-Control-Allow-Origin": origin or "",
                        "Access-Control-Allow-Credentials": "true",
                        "Access-Control-Allow-Methods": "GET, POST, PUT, PATCH, DELETE, OPTIONS",
                        "Access-Control-Allow-Headers": request.headers.get(
                            "access-control-request-headers", "*"
                        ),
                        "Access-Control-Max-Age": "600",
                        "Vary": "Origin",
                    },
                )

            response = await call_next(request)
            response.headers["Access-Control-Allow-Origin"] = origin or ""
            response.headers["Access-Control-Allow-Credentials"] = "true"
            response.headers["Vary"] = "Origin"
            return response

        return await call_next(request)
