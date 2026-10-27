"""MCP server factory — Japan Business Day & Holiday Calculator MCP.

Exposes the Cabinet Office official Japanese holiday list plus business-day
arithmetic as MCP tools for AI agents (Claude Desktop, Cursor, VS Code, …).

Data is deterministic and offline-safe: the bundled seed cache
(data/japan_holidays.json) is a snapshot of the official
国民の祝日・休日 CSV from the Cabinet Office. No network call is made at tool
time, so answers are reproducible and free of IP-gating.
"""

from __future__ import annotations

import os

from fastmcp import FastMCP

from src import jbc

if os.environ.get("JBC_CONTAINER_PORT"):
    from apify import Actor
else:
    from src.apify_shim import Actor  # type: ignore[assignment]

_READ_ONLY_ANNOTATIONS = {
    "readOnlyHint": True,
    "destructiveHint": False,
    "idempotentHint": True,
    "openWorldHint": False,
}

_ATTRIBUTION = (
    "Source: Cabinet Office (内閣府) 国民の祝日・休日 — "
    "https://www8.cao.go.jp/chosei/shukujitsu/syukujitsu.csv. "
    "Government Standard Terms of Use (出典明示で商用利用可)."
)


def get_server() -> FastMCP:
    try:
        server = FastMCP("japan-business-calendar-mcp", version="0.1.0")
    except TypeError:  # old FastMCP without version kwarg
        server = FastMCP("japan-business-calendar-mcp")

    # ── Tool 1: day analysis ──────────────────────────────
    @server.tool(annotations=_READ_ONLY_ANNOTATIONS)
    async def analyze_date(date: str = "") -> dict:
        """Analyze one Japanese calendar date: is it a business day, a national
        holiday, or a weekend — and give the nearest business days.

        Args:
            date: YYYY-MM-DD (or YYYY/MM/DD). Empty = today (UTC).
        """
        await Actor.charge("jbc-0analyze")
        d = jbc._parse_date(date) if date.strip() else _today()
        return {"type": "text", "text": _fmt(jbc.analyze(d)),
                "structuredContent": jbc.analyze(d), "attribution": _ATTRIBUTION}

    # ── Tool 2: business-day count over a range ───────────
    @server.tool(annotations=_READ_ONLY_ANNOTATIONS)
    async def count_business_days(start: str, end: str) -> dict:
        """Count business days (and non-business days) in an inclusive range.

        Args:
            start: range start, YYYY-MM-DD.
            end:   range end, YYYY-MM-DD.
        """
        await Actor.charge("jbc-0count")
        s, e = jbc._parse_date(start), jbc._parse_date(end)
        r = jbc.count_business_days(s, e)
        return {"type": "text", "text": _fmt(r), "structuredContent": r,
                "attribution": _ATTRIBUTION}

    # ── Tool 3: next / previous business day ──────────────
    @server.tool(annotations=_READ_ONLY_ANNOTATIONS)
    async def next_business_day(date: str = "", n: int = 1) -> dict:
        """Find the n-th business day after (n>0) or before (n<0) a date.

        Args:
            date: YYYY-MM-DD. Empty = today.
            n:    steps; 1 = next business day, -1 = previous, 3 = 3rd next.
        """
        await Actor.charge("jbc-0next")
        d = jbc._parse_date(date) if date.strip() else _today()
        index = jbc._holiday_index()
        step = 1 if n >= 0 else -1
        cur = d
        for _ in range(abs(n)):
            cur = jbc._step(cur, index, step)
        return {"type": "text", "text": _fmt({"date": jbc._fmt(cur),
                "weekday": jbc._WEEKDAY[cur.weekday()], "steps": n,
                "from": jbc._fmt(d)}),
                "structuredContent": {"date": jbc._fmt(cur),
                "weekday": jbc._WEEKDAY[cur.weekday()], "steps": n,
                "from": jbc._fmt(d)}, "attribution": _ATTRIBUTION}

    # ── Tool 4: holiday list for a year ───────────────────
    @server.tool(annotations=_READ_ONLY_ANNOTATIONS)
    async def list_holidays(year: int = 0) -> dict:
        """List national holidays. Args: year (0 = all years in the seed)."""
        await Actor.charge("jbc-0hol")
        items = jbc.list_holidays(year or None)
        return {"type": "text", "text": _fmt({"count": len(items), "holidays": items[:200]}),
                "structuredContent": {"count": len(items), "holidays": items[:200]},
                "attribution": _ATTRIBUTION}

    # ── Tool 5: business days in a month ──────────────────
    @server.tool(annotations=_READ_ONLY_ANNOTATIONS)
    async def list_business_days(year: int, month: int) -> dict:
        """List all business days in a Japanese calendar month.

        Args: year (e.g. 2026), month (1-12).
        """
        await Actor.charge("jbc-0bdays")
        items = jbc.list_business_days_in_month(year, month)
        return {"type": "text", "text": _fmt({"year": year, "month": month,
                "count": len(items), "business_days": items}),
                "structuredContent": {"year": year, "month": month,
                "count": len(items), "business_days": items},
                "attribution": _ATTRIBUTION}

    # ── Tool 6: seed summary ──────────────────────────────
    @server.tool(annotations=_READ_ONLY_ANNOTATIONS)
    async def data_summary() -> dict:
        """Metadata about the bundled holiday seed: source, license, coverage."""
        await Actor.charge("jbc-0summary")
        s = jbc.summary()
        return {"type": "text", "text": _fmt(s), "structuredContent": s,
                "attribution": _ATTRIBUTION}

    return server


def _today():
    from datetime import date as _d
    return _d.today()


def _fmt(obj) -> str:
    import json
    return json.dumps(obj, ensure_ascii=False, indent=2)