"""Apify Standby entry point — host the REST/MCP gateway inside the container.

The Apify Actor runs `python -m src.main` (see Dockerfile). In Standby mode the
actor exposes a web server; we serve the REST app on the container port and
proxy /mcp to the FastMCP stdio bridge.
"""

from __future__ import annotations

import os

from src.rest import app


def main() -> None:
    port = int(os.environ.get("APIFY_CONTAINER_PORT", "8080"))
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=port)


if __name__ == "__main__":
    main()