"""Local smoke test — REST + MCP, offline, seed-backed.

Covers every tool and REST endpoint. Run:
  JBC_DATA_DIR=. python3 tests/test_jbc.py
"""

from __future__ import annotations

import os
import sys

os.environ.setdefault("JBC_DATA_DIR", os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data"))

from src import jbc  # noqa: E402
from src.server import get_server  # noqa: E402


def _tool_names(server):
    """Best-effort list of the FastMCP server's exposed tool names (fastmcp 3.x)."""
    import asyncio
    try:
        res = server.list_tools()
        if asyncio.iscoroutine(res):
            loop = asyncio.new_event_loop()
            try:
                res = loop.run_until_complete(res)
            finally:
                loop.close()
        return [t.name for t in res]
    except Exception as e:  # noqa: BLE001
        print("list_tools failed:", e)
        return []


def _run(coro):
    import asyncio
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


def main() -> None:
    # ── core logic ────────────────────────────────────────
    tue = jbc._parse_date("2026-10-27")
    assert jbc.analyze(tue)["is_business_day"] is True, "2026-10-27 must be a business day"
    assert jbc.analyze(tue)["is_holiday"] is False

    fri = jbc._parse_date("2026-11-23")  # 勤労感謝の日
    a = jbc.analyze(fri)
    assert a["is_holiday"] is True and a["holiday_name"] == "勤労感謝の日", a
    assert a["is_business_day"] is False

    sat = jbc._parse_date("2026-10-31")  # Saturday
    assert jbc.analyze(sat)["is_business_day"] is False
    assert jbc.analyze(sat)["is_holiday"] is False

    # next/prev business day from a Monday holiday the 23rd -> next is Tue the 24th
    nxt = jbc._step(fri, jbc._holiday_index(), +1)
    assert nxt.isoformat() == "2026-11-24", nxt
    prv = jbc._step(fri, jbc._holiday_index(), -1)
    assert prv.isoformat() == "2026-11-20", prv

    # count over a week straddling the weekend: 23(holiday)+24,25(weekend)+26,27
    c = jbc.count_business_days(jbc._parse_date("2026-11-23"), jbc._parse_date("2026-11-27"))
    assert c["total_days"] == 5 and c["business_days"] == 4, c

    # year list
    hol2027 = jbc.list_holidays(2027)
    assert any(h["date"] == "2027-11-23" and h["name"] == "勤労感謝の日" for h in hol2027), hol2027

    # month list
    nov2026 = jbc.list_business_days_in_month(2026, 11)
    assert 23 not in {h["date"] for h in nov2026}
    assert "2026-11-26" in {h["date"] for h in nov2026}
    assert len(nov2026) == 19, len(nov2026)  # 30 days - 4 sun - 4 sat - 3 holidays(23,24,25? no) -> compute below

    s = jbc.summary()
    assert s["total_holidays_in_seed"] == 1067, s
    assert s["last_holiday"] == "2027-11-23"

    print("CORE_LOGIC_OK")

    # ── MCP server surface ────────────────────────────────
    server = get_server()
    tools = _tool_names(server)
    print("MCP tools:", tools)
    expected = {
        "analyze_date", "count_business_days", "next_business_day",
        "list_holidays", "list_business_days", "data_summary",
    }
    assert expected.issubset(set(tools)), f"missing tools: {expected - set(tools)}"
    assert len(tools) == 6, tools

    # actually invoke a tool end-to-end via the MCP server
    res = _run(server.call_tool("analyze_date", {"date": "2026-11-23"}))
    payload = res[0].text if isinstance(res, list) and hasattr(res[0], "text") else str(res)
    assert "勤労感謝の日" in payload, payload
    res2 = _run(server.call_tool("count_business_days",
                                 {"start": "2026-11-23", "end": "2026-11-27"}))
    assert "4" in (res2[0].text if isinstance(res2, list) else str(res2))
    print("MCP_TOOL_CALL_OK")

    # ── REST layer ────────────────────────────────────────
    try:
        from starlette.testclient import TestClient
    except Exception as e:
        print("TestClient unavailable:", e)
        sys.exit(0)
    from src.rest import app
    with TestClient(app) as client:
        r = client.get("/health"); assert r.status_code == 200, r.text
        r = client.get("/rest/analyze?date=2026-11-23")
        assert r.status_code == 200, r.text
        d = r.json()
        assert d["is_business_day"] is False and d["holiday_name"] == "勤労感謝の日", d
        r = client.get("/rest/analyze?date=2026-10-27")
        assert r.json()["is_business_day"] is True
        r = client.get("/rest/count?start=2026-11-23&end=2026-11-27")
        assert r.json()["business_days"] == 4, r.json()
        r = client.get("/rest/next?date=2026-11-23&n=1")
        assert r.json()["date"] == "2026-11-24", r.json()
        r = client.get("/rest/next?date=2026-11-23&n=-1")
        assert r.json()["date"] == "2026-11-20", r.json()
        r = client.get("/rest/holidays?year=2027")
        assert r.json()["count"] >= 15, r.json()
        r = client.get("/rest/business-days?year=2026&month=11")
        bd = r.json()
        assert bd["count"] == 19, bd
        assert "2026-11-23" not in {x["date"] for x in bd["business_days"]}
        r = client.get("/rest/summary")
        assert r.json()["total_holidays_in_seed"] == 1067
        r = client.get("/openapi.json")
        paths = sorted(r.json()["paths"].keys())
        assert "/rest/analyze" in paths and "/rest/count" in paths, paths
        print("REST paths:", paths)

    print("REST_SMOKE_OK")
    print("ALL_SMOKE_PASS")


if __name__ == "__main__":
    main()
    sys.exit(0)