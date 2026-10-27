"""REST layer — OpenAPI gateway over the same jbc core.

Exposes the calculator over HTTP for non-MCP consumers (curl, browser, other
services). Runs under the Apify Standby web server when JBC_CONTAINER_PORT is
set, otherwise via uvicorn locally.

Usage:
  JBC_DATA_DIR=. python3 -m src.rest      # local dev server on :8080
"""

from __future__ import annotations

import os
import json
from datetime import date as _date

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import JSONResponse

from src import jbc

app = FastAPI(
    title="Japan Business Day & Holiday Calculator API",
    version="0.1.0",
    description=(
        "Official Cabinet Office (内閣府) Japanese national holidays plus "
        "business-day arithmetic. Data: deterministic seed cache, no network at "
        "runtime. Government Standard Terms of Use."
    ),
)


@app.get("/health")
def health() -> dict:
    s = jbc.summary()
    return {"status": "ok", "seed": s["total_holidays_in_seed"],
            "source": s["source"]}


@app.get("/rest/analyze")
def rest_analyze(date: str = Query(default="", description="YYYY-MM-DD; empty = today")) -> dict:
    d = jbc._parse_date(date) if date.strip() else _date.today()
    r = jbc.analyze(d)
    r["attribution"] = (
        "Source: Cabinet Office (内閣府) 国民の祝日・休日 — "
        "https://www8.cao.go.jp/chosei/shukujitsu/syukujitsu.csv"
    )
    return r


@app.get("/rest/count")
def rest_count(start: str, end: str) -> dict:
    s, e = jbc._parse_date(start), jbc._parse_date(end)
    r = jbc.count_business_days(s, e)
    r["attribution"] = "Source: Cabinet Office (内閣府) 国民の祝日・休日"
    return r


@app.get("/rest/next")
def rest_next(date: str = Query(default=""), n: int = Query(default=1)) -> dict:
    d = jbc._parse_date(date) if date.strip() else _date.today()
    index = jbc._holiday_index()
    step = 1 if n >= 0 else -1
    cur = d
    for _ in range(abs(n)):
        cur = jbc._step(cur, index, step)
    return {"date": jbc._fmt(cur), "weekday": jbc._WEEKDAY[cur.weekday()],
            "steps": n, "from": jbc._fmt(d),
            "attribution": "Source: Cabinet Office (内閣府) 国民の祝日・休日"}


@app.get("/rest/holidays")
def rest_holidays(year: int = Query(default=0)) -> dict:
    items = jbc.list_holidays(year or None)
    return {"count": len(items), "holidays": items[:500],
            "attribution": "Source: Cabinet Office (内閣府) 国民の祝日・休日"}


@app.get("/rest/business-days")
def rest_business_days(year: int, month: int) -> dict:
    items = jbc.list_business_days_in_month(year, month)
    return {"year": year, "month": month, "count": len(items),
            "business_days": items,
            "attribution": "Source: Cabinet Office (内閣府) 国民の祝日・休日"}


@app.get("/rest/summary")
def rest_summary() -> dict:
    return jbc.summary()


@app.get("/openapi.json")
def openapi() -> dict:
    return app.openapi()


def _err(msg: str, code: int = 400) -> JSONResponse:
    return JSONResponse(status_code=code, content={"error": msg})


# wire HTTPException → clean JSON
@app.exception_handler(HTTPException)
def http_exc_handler(request, exc):  # type: ignore[override]
    return _err(exc.detail, exc.status_code)


if __name__ == "__main__":  # pragma: no cover
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("JBC_PORT", "8080")))