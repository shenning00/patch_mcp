"""MCP Server for File Patch operations.

This module implements the Model Context Protocol (MCP) server that registers
and routes all 7 patch tools.

Tools provided:
    1. apply_patch - Apply a patch to a file (supports dry_run)
    2. validate_patch - Check if a patch can be applied
    3. revert_patch - Reverse a previously applied patch
    4. generate_patch - Create a patch from two files
    5. inspect_patch - Analyze patch content
    6. backup_file - Create a timestamped backup
    7. restore_backup - Restore a file from backup
"""

import asyncio
import json
from typing import Any

from mcp.server import Server
from mcp.types import Resource, TextContent, Tool

# Import all tool implementations
from .tools import apply, backup, generate, inspect, revert, validate

# Create MCP server instance
server = Server("patch-mcp")


@server.list_tools()  # type: ignore[misc,no-untyped-call]
async def list_tools() -> list[Tool]:
    """List all 7 available tools with their schemas.

    Returns:
        List of Tool objects with proper input schemas
    """
    return [
        Tool(
            name="apply_patch",
            description="""Apply a unified diff patch to a file using standard unified diff format (like git diff).

WHEN TO USE: Prefer this over Edit tool for:
- Multiple changes in one file (multi-hunk patches = atomic)
- Changes that need to be reviewable (standard diff format)
- Token-efficient edits (~50% less context than Edit)
- Changes requiring dry-run testing first

Supports multi-hunk patches for atomic application of multiple changes to different parts of the same file.
Also supports dry_run mode for validation without modification.""",
            inputSchema={
                "type": "object",
                "properties": {
                    "file_path": {
                        "type": "string",
                        "description": "Path to the file to patch",
                    },
                    "patch": {
                        "type": "string",
                        "description": "Unified diff patch content. Can include multiple hunks (@@) to apply multiple changes atomically to different parts of the file.",
                    },
                    "dry_run": {
                        "type": "boolean",
                        "description": "Validate without modifying (default: false)",
                        "default": False,
                    },
                },
                "required": ["file_path", "patch"],
            },
        ),
        Tool(
            name="validate_patch",
            description="Check if a patch can be applied (read-only)",
            inputSchema={
                "type": "object",
                "properties": {
                    "file_path": {
                        "type": "string",
                        "description": "Path to the file to validate against",
                    },
                    "patch": {
                        "type": "string",
                        "description": "Unified diff patch content to validate",
                    },
                },
                "required": ["file_path", "patch"],
            },
        ),
        Tool(
            name="revert_patch",
            description="Reverse a previously applied patch. For multi-hunk patches, atomically reverts all changes that were applied together.",
            inputSchema={
                "type": "object",
                "properties": {
                    "file_path": {
                        "type": "string",
                        "description": "Path to the file to revert",
                    },
                    "patch": {
                        "type": "string",
                        "description": "The same patch that was previously applied (including all hunks if it was a multi-hunk patch)",
                    },
                },
                "required": ["file_path", "patch"],
            },
        ),
        Tool(
            name="generate_patch",
            description="Generate a patch from two files",
            inputSchema={
                "type": "object",
                "properties": {
                    "original_file": {
                        "type": "string",
                        "description": "Path to the original/old version of the file",
                    },
                    "modified_file": {
                        "type": "string",
                        "description": "Path to the modified/new version of the file",
                    },
                    "context_lines": {
                        "type": "integer",
                        "description": "Number of context lines (default: 3)",
                        "default": 3,
                    },
                },
                "required": ["original_file", "modified_file"],
            },
        ),
        Tool(
            name="inspect_patch",
            description="Analyze patch content (supports multi-file patches)",
            inputSchema={
                "type": "object",
                "properties": {
                    "patch": {
                        "type": "string",
                        "description": "Unified diff patch content to analyze",
                    },
                },
                "required": ["patch"],
            },
        ),
        Tool(
            name="backup_file",
            description="Create a timestamped backup",
            inputSchema={
                "type": "object",
                "properties": {
                    "file_path": {
                        "type": "string",
                        "description": "Path to the file to backup",
                    },
                },
                "required": ["file_path"],
            },
        ),
        Tool(
            name="restore_backup",
            description="Restore a file from backup",
            inputSchema={
                "type": "object",
                "properties": {
                    "backup_file": {
                        "type": "string",
                        "description": "Path to the backup file to restore from",
                    },
                    "target_file": {
                        "type": "string",
                        "description": "Path where the backup should be restored (optional, "
                        "defaults to original location)",
                    },
                    "force": {
                        "type": "boolean",
                        "description": "Overwrite target even if it has been modified (default: false)",
                        "default": False,
                    },
                },
                "required": ["backup_file"],
            },
        ),
    ]


@server.list_resources()  # type: ignore[misc,no-untyped-call]
async def list_resources() -> list[Resource]:
    """List available documentation resources.

    Returns:
        List of Resource objects providing usage guidance
    """
    return [
        Resource(
            uri="patch://guide/when-to-use",  # type: ignore[arg-type]
            name="When to Use Patch Tools vs Edit",
            description="Decision guide for choosing between apply_patch and Edit tool",
            mimeType="text/markdown",
        )
    ]


@server.read_resource()  # type: ignore[misc,no-untyped-call]
async def read_resource(uri: str) -> str:
    """Read a documentation resource.

    Args:
        uri: Resource URI to read

    Returns:
        Resource content as string
    """
    if uri == "patch://guide/when-to-use":
        return """# When to Use apply_patch vs Edit

## Use apply_patch When:
✅ Making multiple changes to one file (atomic multi-hunk)
✅ Changes should be reviewable (standard diff format)
✅ Need to test first (dry_run mode)
✅ Want token efficiency (~50% less than Edit)

## Use Edit When:
- Single simple substitution
- Don't have file in context yet
- Quick one-line changes

## Example: Multiple Changes
Instead of 3 Edit calls:

❌ 3 separate operations, no atomicity, partial updates possible

Use 1 apply_patch with 3 hunks:

✅ 1 atomic operation, clear diff view, token efficient
"""
    raise ValueError(f"Unknown resource URI: {uri}")


@server.call_tool()  # type: ignore[misc]
async def call_tool(name: str, arguments: dict[str, Any]) -> list[TextContent]:
    """Route tool calls to appropriate implementations.

    Args:
        name: Name of the tool to call
        arguments: Dictionary of tool arguments

    Returns:
        List containing a single TextContent with JSON-formatted result

    Raises:
        ValueError: If tool name is unknown
    """
    result = None

    if name == "apply_patch":
        result = apply.apply_patch(
            arguments["file_path"],
            arguments["patch"],
            arguments.get("dry_run", False),
        )
    elif name == "validate_patch":
        result = validate.validate_patch(
            arguments["file_path"],
            arguments["patch"],
        )
    elif name == "revert_patch":
        result = revert.revert_patch(
            arguments["file_path"],
            arguments["patch"],
        )
    elif name == "generate_patch":
        result = generate.generate_patch(
            arguments["original_file"],
            arguments["modified_file"],
            arguments.get("context_lines", 3),
        )
    elif name == "inspect_patch":
        result = inspect.inspect_patch(arguments["patch"])
    elif name == "backup_file":
        result = backup.backup_file(arguments["file_path"])
    elif name == "restore_backup":
        result = backup.restore_backup(
            arguments["backup_file"],
            arguments.get("target_file"),
            arguments.get("force", False),
        )
    else:
        raise ValueError(f"Unknown tool: {name}")

    return [TextContent(type="text", text=json.dumps(result, indent=2))]


async def main() -> None:
    """Run the MCP server using stdio transport.

    This is the main entry point for the server. It sets up the stdio
    communication channel and runs the server event loop.
    """
    from mcp.server.stdio import stdio_server

    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            server.create_initialization_options(),
        )


if __name__ == "__main__":
    asyncio.run(main())
