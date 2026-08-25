"""Client-IP-Kontext für den Remote-MCP-Server (Owner-Wunsch 2026-07-16).

Der ntfy-Push je MCP-Tool-Aufruf (``ops/firstseen.note_mcp_action``) zeigte bisher
weder HTTP-Status noch Absender: die API sieht bei MCP-Aufrufen nur die interne
Compose-IP des MCP-Containers. Diese Middleware merkt sich die ECHTE Client-IP des
eingehenden MCP-Requests (CF-Connecting-IP -> X-Forwarded-For[0] -> Peer, gleiche
Quelle wie das MCP-Rate-Limit) in einer ContextVar. Der Loopback-Client
(``mcp/client.py``) liest sie beim API-Aufruf und reicht sie als Header
``X-Infranode-Mcp-Client`` weiter, damit sie im ntfy-Push sichtbar wird.

Zur ContextVar-Vererbung im streamable-http-Transport: im stateful Betrieb
(unser Default) entsteht die Session-Task beim ERSTEN Request einer Session und
erbt dessen Async-Kontext, spaetere Tool-Calls derselben Session sehen also die
IP des Session-Starts. Da eine MCP-Session immer genau einem Client gehoert, ist
das fuer den Info-Push korrekt genug; nur ein Client-IP-Wechsel INNERHALB einer
laufenden Session (Roaming) wuerde erst mit neuer Session sichtbar. Reines ASGI
(kein BaseHTTPMiddleware), damit der SSE-/Streaming-Pfad unangetastet bleibt
(gleiches Muster wie MCPRateLimitMiddleware). Best-effort, KEIN Auth-Mechanismus.
"""

from __future__ import annotations

from contextvars import ContextVar

from starlette.requests import Request
from starlette.types import ASGIApp, Receive, Scope, Send

from infranode.mcp.ratelimit import client_ip

# Aktuelle Client-IP des laufenden MCP-Requests; None ausserhalb eines
# HTTP-Requests (z.B. lokaler stdio-Betrieb: dort gibt es keinen Absender).
current_client_ip: ContextVar[str | None] = ContextVar(
    "infranode_mcp_client_ip", default=None
)


class ClientIpMiddleware:
    """ASGI-Middleware: setzt ``current_client_ip`` fuer die Dauer des Requests."""

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        token = current_client_ip.set(client_ip(Request(scope)))
        try:
            await self.app(scope, receive, send)
        finally:
            current_client_ip.reset(token)
