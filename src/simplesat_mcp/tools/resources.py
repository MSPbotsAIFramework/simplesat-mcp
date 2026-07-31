import json
from collections.abc import Callable

from mcp.server.fastmcp import FastMCP

from ..api_client import SimplesatClient, SimplesatError
from ._common import NO_TOKEN


def register(mcp: FastMCP, client_factory: Callable[[], SimplesatClient | None]) -> None:

    @mcp.tool()
    async def simplesat_search_answers(
        page: int | None = None,
        page_size: int | None = None,
        start_date: str | None = None,
        end_date: str | None = None,
        filter_key: str | None = None,
        filter_values: list[str] | None = None,
        filter_comparison: str | None = None,
    ) -> str:
        """Search survey answers (CSAT/NPS ratings and comments).

        API: POST /api/v1/answers/search

        No required parameters (matches MSPbots' own usage, which calls
        this with no date range or filters).

        Args:
            page: Optional. Page number to retrieve.
            page_size: Optional. Records per page.
            start_date: Optional. Range start, ISO 8601 (e.g.
                "2024-01-01T00:00:00Z").
            end_date: Optional. Range end, ISO 8601.
            filter_key: Optional. One of "choice_value", "comment",
                "metric", "sentiment", "survey" (token). Requires
                filter_values and filter_comparison to also be set.
            filter_values: Optional. Values to compare against, e.g.
                ["positive"].
            filter_comparison: Optional. One of "is", "is_not",
                "contains", "does_not_contain", "is_unknown",
                "has_any_value".
        """
        client = client_factory()
        if client is None:
            return NO_TOKEN
        filters = None
        if filter_key is not None:
            filters = [
                {"key": filter_key, "values": filter_values or [], "comparison": filter_comparison}
            ]
        try:
            result = await client.search_answers(
                page=page,
                page_size=page_size,
                start_date=start_date,
                end_date=end_date,
                filters=filters,
            )
            return json.dumps(result, indent=2)
        except SimplesatError as e:
            return f"Error: {e}"
