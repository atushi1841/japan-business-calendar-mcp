"""stdio entry point — run the MCP server on stdin/stdout.

Usage:
  uv run --directory . src/stdio_main.py
"""

from __future__ import annotations

import asyncio

from src.server import get_server


def main() -> None:
    server = get_server()
    asyncio.run(server.run_stdio_async())


if __name__ == "__main__":
    main()