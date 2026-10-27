"""Minimal Apify Actor shim used when running outside an Apify container.

The real apify.Actor is only available inside the Apify Python runtime; in
local/stdio runs we expose a no-op stand-in so the server can import and run
without the Apify SDK installed. Charge calls are silently ignored (PPE is
configured on the Apify side, not locally).
"""

from __future__ import annotations


class _Actor:
    """No-op stand-in for apify.Actor."""

    @staticmethod
    async def charge(event_name: str, count: int = 1) -> None:  # noqa: D401
        return None

    @staticmethod
    async def init() -> None:  # noqa: D401
        return None

    @staticmethod
    async def exit() -> None:  # noqa: D401
        return None


Actor = _Actor