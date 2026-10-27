"""Japan Business Day & Holiday core logic.

Pure, dependency-free: no network, no Apify runtime. All state comes from the
bundled seed cache (data/japan_holidays.json) which is a snapshot of the Cabinet
Office official 国民の祝日・休日 list (https://www8.cao.go.jp/chosei/shukujitsu/syukujitsu.csv).

Business day rule applied on top of the official holiday list:
  - a day is a business day when it is NOT a national holiday AND not a
    Saturday/Sunday (土日).
  - Japanese corporate practice treats 元日 (Jan 1) and 12/29-12/31 as de-facto
    closures even though 元日 is already a statutory holiday; we keep the rule
    purely "holiday or weekend" and expose the raw facts so callers can layer
    their own 公社日ルール.
"""

from __future__ import annotations

import json
import os
from datetime import date, timedelta
from pathlib import Path

_DATA_DIR = Path(os.environ.get("JBC_DATA_DIR", Path(__file__).resolve().parent.parent / "data"))
_HOLIDAYS_PATH = _DATA_DIR / "japan_holidays.json"

_WEEKDAY = ["月", "火", "水", "木", "金", "土", "日"]


def _load() -> dict:
    with open(_HOLIDAYS_PATH, encoding="utf-8") as fh:
        return json.load(fh)


def _holiday_index() -> dict[str, str]:
    data = _load()
    return {h["date"]: h["name"] for h in data["holidays"]}


def _parse_date(value: str) -> date:
    s = str(value).strip()
    for fmt in ("%Y-%m-%d", "%Y/%m/%d", "%Y%m%d"):
        try:
            return date(*[int(x) for x in s.replace("/", "-").split("-")])
        except ValueError:
            continue
    raise ValueError(f"invalid date: {value!r} (expected YYYY-MM-DD)")


def _fmt(d: date) -> str:
    return d.isoformat()


def is_holiday(d: date, index: dict[str, str] | None = None) -> tuple[bool, str | None]:
    """Return (is_holiday, holiday_name_or_None)."""
    index = index or _holiday_index()
    key = _fmt(d)
    return key in index, index.get(key)


def is_business_day(d: date, index: dict[str, str] | None = None) -> bool:
    """Business day = not a national holiday and not Sat/Sun."""
    if d.weekday() >= 5:  # Sat=5, Sun=6
        return False
    return not is_holiday(d, index)[0]


def _step(d: date, index: dict[str, str], direction: int) -> date:
    cur = d
    while True:
        cur += timedelta(days=direction)
        if is_business_day(cur, index):
            return cur


def analyze(day: date, index: dict[str, str] | None = None) -> dict:
    index = index or _holiday_index()
    hol, name = is_holiday(day, index)
    biz = (not hol) and day.weekday() < 5
    return {
        "date": _fmt(day),
        "weekday": _WEEKDAY[day.weekday()],
        "weekday_en": day.strftime("%A"),
        "is_holiday": hol,
        "holiday_name": name,
        "is_business_day": biz,
        "next_business_day": _fmt(_step(day, index, +1)),
        "previous_business_day": _fmt(_step(day, index, -1)),
    }


def count_business_days(start: date, end: date, index: dict[str, str] | None = None) -> dict:
    """Inclusive count of business days in [start, end]."""
    index = index or _holiday_index()
    if start > end:
        start, end = end, start
    n = 0
    cur = start
    one = timedelta(days=1)
    while cur <= end:
        if is_business_day(cur, index):
            n += 1
        cur += one
    return {
        "start": _fmt(start),
        "end": _fmt(end),
        "total_days": (end - start).days + 1,
        "business_days": n,
        "non_business_days": (end - start).days + 1 - n,
    }


def list_holidays(year: int | None = None, index: dict[str, str] | None = None) -> list[dict]:
    index = index or _holiday_index()
    items = [{"date": k, "name": v} for k, v in index.items()]
    items.sort(key=lambda x: x["date"])
    if year is not None:
        prefix = f"{year:04d}-"
        items = [x for x in items if x["date"].startswith(prefix)]
    return items


def list_business_days_in_month(year: int, month: int, index: dict[str, str] | None = None) -> list[dict]:
    index = index or _holiday_index()
    if month < 1 or month > 12:
        raise ValueError("month must be 1-12")
    # first day of next month, then step back
    if month == 12:
        nxt = date(year + 1, 1, 1)
    else:
        nxt = date(year, month + 1, 1)
    cur = date(year, month, 1)
    out = []
    while cur < nxt:
        if is_business_day(cur, index):
            out.append({"date": _fmt(cur), "weekday": _WEEKDAY[cur.weekday()]})
        cur += timedelta(days=1)
    return out


def summary() -> dict:
    data = _load()
    return {
        "source": data.get("source"),
        "source_name": data.get("source_name"),
        "license": data.get("license"),
        "fetched": data.get("fetched"),
        "total_holidays_in_seed": data.get("count"),
        "first_holiday": data["holidays"][0]["date"] if data.get("holidays") else None,
        "last_holiday": data["holidays"][-1]["date"] if data.get("holidays") else None,
    }