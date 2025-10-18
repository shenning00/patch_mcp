"""CLI entry point for patch-mcp server.

This module enables running the server as a Python module:
    python -m patch_mcp

The server will start and communicate via stdio transport.
"""

import asyncio

from .server import main

if __name__ == "__main__":
    asyncio.run(main())
