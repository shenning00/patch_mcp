"""File Patch MCP Server - Apply unified diff patches with comprehensive security."""

__version__ = "3.0.0"

from .server import main, server

__all__ = ["server", "main", "__version__"]
