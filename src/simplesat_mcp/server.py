import contextvars
from collections.abc import Callable

from mcp.server.fastmcp import FastMCP
from mcp.server.transport_security import TransportSecuritySettings
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.types import ASGIApp, Receive, Scope, Send

from .api_client import SimplesatClient
from .config import Settings

# Per-request credential isolation via contextvars.
# GatewayTokenMiddleware sets this before the MCP handler runs.
# Python asyncio copies context per task, so concurrent SSE connections are isolated.
_gateway_creds_var: contextvars.ContextVar[str | None] = contextvars.ContextVar(
    "simplesat_gateway_creds", default=None
)


def get_client_from_context(settings: Settings) -> SimplesatClient | None:
    """Resolve the active SimplesatClient for the current request context."""
    api_key = _gateway_creds_var.get()
    if not api_key:
        return None
    return SimplesatClient(api_key, settings.simplesat_base_url)


class GatewayTokenMiddleware:
    """ASGI middleware.

    Reads X-Simplesat-Api-Key (required) from request headers and stores
    it in the contextvar. Returns 401 if missing on /mcp requests.
    """

    def __init__(self, app: ASGIApp, settings: Settings):
        self.app = app
        self.settings = settings

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        path = scope.get("path", "")
        if not path.startswith("/mcp"):
            await self.app(scope, receive, send)
            return

        request = Request(scope)
        api_key = request.headers.get("x-simplesat-api-key")
        if not api_key:
            response = JSONResponse(
                {
                    "error": "Missing credentials",
                    "message": "This server requires the X-Simplesat-Api-Key header",
                    "required_headers": ["X-Simplesat-Api-Key"],
                    "optional_headers": [],
                },
                status_code=401,
            )
            await response(scope, receive, send)
            return

        ctx_token = _gateway_creds_var.set(api_key)
        try:
            await self.app(scope, receive, send)
        finally:
            _gateway_creds_var.reset(ctx_token)


def create_mcp_server(settings: Settings) -> FastMCP:
    """Build the FastMCP server instance and register all Simplesat tools."""
    # DNS-rebinding protection is a browser-oriented safeguard that rejects
    # non-localhost Host headers with 421. Disable it so the server works
    # correctly behind a reverse proxy or docker network.
    mcp = FastMCP(
        name="simplesat-mcp",
        instructions=(
            "Simplesat is a CSAT/NPS customer-satisfaction survey platform MSPs use "
            "to collect and analyze feedback from their own clients — ratings, "
            "sentiment, and free-text comments tied to specific surveys and metrics. "
            "This server exposes one read-only tool, simplesat_search_answers, for "
            "querying submitted survey answers. Call it with no arguments to list "
            "recent answers, or narrow results with a date range (start_date/"
            "end_date) and/or a single filter (filter_key + filter_values + "
            "filter_comparison) on choice_value, comment, metric, sentiment, or "
            "survey. Use this for questions like 'what's our recent CSAT/NPS "
            "feedback', 'show negative-sentiment responses this month', or 'find "
            "comments mentioning X'."
        ),
        transport_security=TransportSecuritySettings(enable_dns_rebinding_protection=False),
    )

    client_factory: Callable[[], SimplesatClient | None] = lambda: get_client_from_context(settings)

    from .tools import resources

    resources.register(mcp, client_factory)

    return mcp
