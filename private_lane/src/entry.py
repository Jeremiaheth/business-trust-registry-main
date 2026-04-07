"""Cloudflare Python Worker entrypoint for the private-lane skeleton."""

from __future__ import annotations

from dataclasses import dataclass
from urllib.parse import urlparse

from app import handle_http_request

try:
    from workers import Response, WorkerEntrypoint
except ImportError:
    @dataclass
    class Response:
        """Fallback Response shape for local tests without the Workers SDK."""

        body: str
        status: int = 200
        headers: dict[str, str] | None = None

    class WorkerEntrypoint:
        """Fallback WorkerEntrypoint for local tests without the Workers SDK."""


class Default(WorkerEntrypoint):
    """Minimal Worker that exposes health and intake validation only."""

    async def fetch(self, request: object) -> Response:
        request_url = getattr(request, "url", "")
        request_method = str(getattr(request, "method", "GET")).upper()
        body_text = None

        if request_method == "POST":
            text_method = getattr(request, "text", None)
            if callable(text_method):
                body_text = str(await text_method())

        route = urlparse(str(request_url)).path or "/"
        result = handle_http_request(
            method=request_method,
            path=route,
            body_text=body_text,
        )
        return Response(
            result.body,
            status=result.status,
            headers=result.headers,
        )
