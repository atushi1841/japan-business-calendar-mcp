# Japan Business Day & Holiday Calculator MCP

MCP server exposing **Japan's official national holidays and business-day
arithmetic** to AI agents. Data is the Cabinet Office (内閣府) official
国民の祝日・休日 list — deterministic, offline-safe, no network at runtime.

## What it does

| Tool | Description |
|------|-------------|
| `analyze_date` | Is a date a business day, a national holiday, or a weekend? Nearest business days. |
| `count_business_days` | Inclusive business-day count over a date range. |
| `next_business_day` | n-th business day before/after a date. |
| `list_holidays` | Full national holiday list, optionally filtered by year. |
| `list_business_days` | All business days in a Japanese calendar month. |
| `data_summary` | Seed metadata: source, license, coverage. |

REST mirror (OpenAPI): `/rest/analyze`, `/rest/count`, `/rest/next`,
`/rest/holidays`, `/rest/business-days`, `/rest/summary`, `/health`, `/openapi.json`.

## Data & attribution

- **Source**: Cabinet Office (内閣府) 国民の祝日・休日 —
  https://www8.cao.go.jp/chosei/shukujitsu/syukujitsu.csv
- **License**: Government Standard Terms of Use (出典明示で商用利用可)
- **Coverage**: 1955-01-01 → 2027-11-23 (1,067 holidays), bundled as
  `data/japan_holidays.json` (~63 KB).
- **Business-day rule**: not a national holiday and not Saturday/Sunday.

## Local run

```bash
uv run --directory . src/stdio_main.py        # stdio MCP (Claude Desktop / Cursor)
JBC_DATA_DIR=. python3 tests/test_jbc.py       # smoke: 6 MCP tools + 8 REST endpoints
```

## Deployment

Apify Actor `japan-business-calendar-mcp` (Standby mode,
`webServerMcpPath=/mcp`, `Dockerfile CMD ["python", "-m", "src.main"]`):
`https://fruitful-quintessence--japan-business-calendar-mcp.apify.actor/mcp`

## Apify Store

This MCP server is also available as a managed Apify Actor (PPE课金):

- **[Apify Store: japan-business-calendar-mcp](https://apify.com/fruitful_quintessence/japan-business-calendar-mcp)** — Japanese business days & national holidays from the Cabinet Office official list. Run from the Apify Store (Run button), then point your MCP client at the endpoint.

## Install via Smithery

Connect this MCP server to your AI client (Claude Desktop, Cursor, VS Code) in one command:

```bash
npx @smithery/cli install atushi1841/japan-business-calendar-mcp --client claude
```

Replace `claude` with `cursor`, `vscode`, or `cline` for other clients.

Alternatively, install directly from the [Smithery registry](https://smithery.ai/server/atushi1841/japan-business-calendar-mcp).

## MCP Registry

This server is registered on the official [MCP Registry](https://registry.modelcontextprotocol.io).
Find it via search: [japan-business-calendar-mcp](https://registry.modelcontextprotocol.io/v0/servers?search=io.github.japan-business-calendar-mcp)