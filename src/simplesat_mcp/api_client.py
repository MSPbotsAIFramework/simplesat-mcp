import httpx


class SimplesatError(Exception):
    def __init__(self, message: str):
        super().__init__(f"Simplesat API error: {message}")


class SimplesatClient:
    """Async httpx client wrapping the Simplesat V1 API.

    Auth is a single static header — no login/token exchange:
    "X-Simplesat-Token: <api key>". Already fully stateless by the
    vendor's own design; nothing is cached across calls.
    """

    def __init__(self, api_key: str, base_url: str):
        self._api_key = api_key.strip()
        self._base_url = base_url.rstrip("/")

    def _clean(self, params: dict | None) -> dict:
        if not params:
            return {}
        return {k: v for k, v in params.items() if v is not None}

    async def search_answers(
        self,
        page: int | None = None,
        page_size: int | None = None,
        start_date: str | None = None,
        end_date: str | None = None,
        filters: list[dict] | None = None,
    ) -> dict:
        headers = {
            "X-Simplesat-Token": self._api_key,
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        body = self._clean({"start_date": start_date, "end_date": end_date, "filters": filters})
        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                resp = await client.post(
                    f"{self._base_url}/api/v1/answers/search",
                    headers=headers,
                    params=self._clean({"page": page, "page_size": page_size}),
                    json=body,
                )
            except httpx.RequestError as e:
                raise SimplesatError(f"{e or type(e).__name__} (answers/search)") from e
            if resp.status_code >= 400:
                raise SimplesatError(f"HTTP {resp.status_code}: {resp.text}")
            return resp.json()
