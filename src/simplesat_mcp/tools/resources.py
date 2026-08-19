from collections.abc import Callable
from typing import Annotated

from mcp.server.fastmcp import FastMCP
from mcp.types import ToolAnnotations
from pydantic import Field

from .._json import dump_json_capped
from ..api_client import SimplesatClient, SimplesatError
from ._common import NO_TOKEN

# Simplesat's documented pagination ceiling is 100 records per page (stricter
# than the SOP's generic <=200 fallback hard-cap), so we clamp to the
# vendor's real maximum instead of the generic one.
_MAX_PAGE_SIZE = 100


def register(mcp: FastMCP, client_factory: Callable[[], SimplesatClient | None]) -> None:

    @mcp.tool(annotations=ToolAnnotations(readOnlyHint=True, idempotentHint=True))
    async def simplesat_search_answers(
        page: Annotated[int | None, Field(description="Page number (default 1).")] = None,
        page_size: Annotated[
            int | None, Field(description="Records per page (default/max 100).")
        ] = None,
        start_date: Annotated[
            str | None, Field(description='Range start, ISO 8601, e.g. "2024-01-01T00:00:00Z".')
        ] = None,
        end_date: Annotated[str | None, Field(description="Range end, ISO 8601.")] = None,
        filter_key: Annotated[
            str | None,
            Field(
                description=(
                    'One of "choice_value", "comment", "metric", "sentiment", "survey". '
                    "Requires filter_values and filter_comparison to also be set."
                )
            ),
        ] = None,
        filter_values: Annotated[
            list[str] | None,
            Field(description='Values to compare against, e.g. ["positive"].'),
        ] = None,
        filter_comparison: Annotated[
            str | None,
            Field(
                description=(
                    'One of "is", "is_not", "contains", "does_not_contain", '
                    '"is_unknown", "has_any_value".'
                )
            ),
        ] = None,
    ) -> str:
        """Search survey answers (CSAT/NPS ratings and comments).

        No required parameters — omit all filters to list recent answers.
        """
        client = client_factory()
        if client is None:
            return NO_TOKEN
        if page_size is not None:
            page_size = min(page_size, _MAX_PAGE_SIZE)
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
            return dump_json_capped(result)
        except SimplesatError as e:
            return e.to_envelope()
