# simplesat-mcp

MCP server for **Simplesat** (CSAT/NPS customer feedback survey
platform). Exposes the Simplesat **V1 API**'s answer search as an MCP
tool.

> Naming note: Simplesat has two generations of integration in MSPbots —
> a legacy 2021-era integration (`subjectCode=SIMPLESAT`, `GET
> /api/answers/`, a `token` field) and the current one this server
> targets (`subjectCode=SIMPLESATV1`, `POST /api/v1/answers/search`, an
> `apiKey` field). Only the current V1 API is covered here.

## Overview

- Stateless HTTP service. No credentials are ever persisted — each request
  supplies its own API key via a header, used only for the lifetime of
  that single request.
- Supports concurrent requests; per-request credential isolation is done via
  Python `contextvars`, not a global/shared client instance.
- Entry points: `POST /mcp` (MCP protocol) and `GET /health` (health check).
- Default port: `8080` (configurable via `MCP_HTTP_PORT`).

## Authentication

Simplesat uses a single static API key — no login or token exchange:

```
X-Simplesat-Token: <api key>
```

Already fully stateless by the vendor's own design; nothing is cached
across MCP calls.

### HEADER 授权参数说明

| Header | 类型 | 是否必填 | 默认值 | 枚举值 | 字段描述 | Example |
|---|---|---|---|---|---|---|
| `X-Simplesat-Api-Key` | string | 是 | 无 | 无 | Simplesat API Key（Account Settings -> API Keys 生成），原样转发为上游 `X-Simplesat-Token` 请求头 | `ssat_170927_a1b2c3d4e5f6g7h8i9j0` |

Missing the header returns `401`:
```json
{
  "error": "Missing credentials",
  "message": "This server requires the X-Simplesat-Api-Key header",
  "required_headers": ["X-Simplesat-Api-Key"],
  "optional_headers": []
}
```

An invalid key surfaces as a tool-level error (e.g. `HTTP 403: {"detail":
"Invalid Token."}`), not an HTTP-level error from this server.

## Environment Variables

| Variable | 类型 | 是否必填 | 默认值 | 说明 |
|---|---|---|---|---|
| `MCP_HTTP_PORT` | int | 否 | `8080` | HTTP 监听端口 |
| `MCP_HTTP_HOST` | string | 否 | `0.0.0.0` | HTTP 监听地址 |
| `SIMPLESAT_BASE_URL` | string | 否 | `https://api.simplesat.io` | Simplesat API 基础 URL |

## MCP Endpoint

- `POST /mcp` — MCP protocol (streamable HTTP transport)
- `GET /health` — health check, returns `{"status": "ok", "service": "simplesat-mcp", "transport": "http"}`

## Tool List

| Tool | 功能 | 参数 |
|---|---|---|
| `simplesat_search_answers` | 搜索问卷调查回答（CSAT/NPS 评分与评论） | `page`、`page_size`、`start_date`、`end_date`、`filter_key`、`filter_values`、`filter_comparison`（均可选） |

Responses are the vendor's raw JSON, pretty-printed, returned as-is.

## 测试示例

```bash
# Health check
curl -s http://localhost:8080/health

# Call a tool via the MCP protocol (streamable HTTP) — requires an
# initialize handshake first per the MCP spec; abbreviated example below
# shows the tool-call request body only:
curl -s -X POST http://localhost:8080/mcp \
  -H "X-Simplesat-Api-Key: <your-api-key>" \
  -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" \
  -H "mcp-session-id: <session-id-from-initialize>" \
  -d '{
    "jsonrpc": "2.0",
    "id": 1,
    "method": "tools/call",
    "params": {
      "name": "simplesat_search_answers",
      "arguments": {}
    }
  }'
```

**Live-verified** (2026-07-31) against a real Simplesat account:
`simplesat_search_answers` called end-to-end through this running server
with the real API key returned `200` and the vendor's correctly-shaped
response (`{"next": null, "previous": null, "count": 0, "answers": []}`)
— this particular test account has zero survey answers recorded yet,
confirmed as a genuine empty result (not an auth failure) since the
response shape exactly matches the vendor's documented schema. A
separate test with a deliberately invalid API key correctly surfaced
`Error: Simplesat API error: HTTP 403: {"detail": "Invalid Token."}`,
confirming the auth failure path works as expected.

## API Reference

- Public, no login required: https://developer.simplesat.io/api (full V1
  API reference, including the Search Answers operation used here)

## Known Gaps

- **Scope is exactly the 1 method MSPbots' current integration uses**
  (`Search answers`) — the Simplesat V1 API also covers Customers, Team
  members, Responses, Surveys, and Questions, plus `Get answer by ID` and
  `Update answer by ID`; those are out of scope here.
- **`simplesat_search_answers` could not be verified with non-empty
  results** — the test account has zero recorded survey answers. Auth
  and request-shape correctness were confirmed via (1) a 200 response
  matching the vendor's exact documented response schema, and (2) a
  separate invalid-key test correctly returning a 403 `Invalid Token`
  error.
- **The `filter_key`/`filter_values`/`filter_comparison` parameters
  expose only a single filter object** — the vendor's API technically
  accepts an array of filter objects for compound filtering, but MSPbots'
  own usage of this integration sends no filters at all, so this server
  keeps the tool signature simple rather than exposing arbitrary
  multi-filter arrays.
