"""MCP Server for File Patch operations.

This module implements the Model Context Protocol (MCP) server that registers
and routes all 5 core patch tools.

Tools provided:
    1. apply_patch - Apply a patch to a file (supports dry_run)
    2. validate_patch - Check if a patch can be applied
    3. backup_file - Create a timestamped backup
    4. restore_backup - Restore a file from backup
    5. update_content - Update file content from original and new content

BREAKING CHANGE (v3.0.0):
    Removed tools: revert_patch, generate_patch, inspect_patch
    Rationale: These tools provided minimal value over core functionality.
    - revert_patch: Just apply reversed patch with apply_patch
    - generate_patch: LLMs generate patches mentally; git diff exists for files
    - inspect_patch: LLMs can parse unified diff format natively
    See DEPRECATION.md for migration guide.
"""

import asyncio
import json
from typing import Any

from mcp.server import Server
from mcp.types import Resource, TextContent, Tool

# Import core tool implementations
from .tools import apply, backup, update, validate

# Create MCP server instance
server = Server("patch-mcp")


@server.list_tools()  # type: ignore[misc,no-untyped-call]
async def list_tools() -> list[Tool]:
    """List all 5 core tools with their schemas.

    Returns:
        List of Tool objects with proper input schemas
    """
    return [
        Tool(
            name="apply_patch",
            description="""⚠️ DEFAULT TOOL FOR FILE EDITS - Use apply_patch instead of Edit for almost all file modifications.

Applies unified diff patches (git diff format). 50% more token-efficient than Edit, atomic multi-hunk support, dry-run mode, and reviewable diffs.

CRITICAL: Only use Edit for trivial single-string substitutions. For everything else, use apply_patch because:
• Token savings: ~50% less tokens (Edit sends full old+new strings, patches send only changes)
• Atomicity: Multi-hunk patches apply 2+ changes in ONE operation (all succeed or all fail together)
• Safety: dry_run mode tests changes before applying (Edit has no preview capability)
• Reliability: Context-based matching (Edit requires exact string match - fragile)
• Reviewability: Standard unified diff format developers understand

WHEN TO USE (recommended for 90%+ of edits):
✓ Any file modification where you've already read the file
✓ Multiple changes in one file (use multi-hunk patches)
✓ Large files (token efficiency matters)
✓ Critical changes (dry_run validation available)

FEATURES:
- Multi-hunk: Apply changes to different parts of file atomically (all or nothing)
- Dry-run: Preview with dry_run: true before applying
- Security: Built-in validation, symlink protection, size limits""",
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
        Tool(
            name="update_content",
            description="""⭐ RECOMMENDED FOR LLMs - Update file content when you have read the file.

Simplest way to modify files when you have the file content in memory. Verifies original content matches file (prevents race conditions), generates unified diff, and applies changes atomically.

WHEN TO USE (recommended for LLMs):
✓ You have read the file and want to modify it
✓ You have both original and new content in memory
✓ You want to see a diff of your changes (for review)
✓ You want safety verification (prevents overwriting unexpected changes)

ADVANTAGES:
• Simple API: Just provide original_content and new_content
• Safety: Verifies file hasn't changed since you read it
• Reviewable: Returns unified diff showing exactly what changed
• Dry-run: Preview changes before applying
• No manual patch creation: Tool generates the diff for you

COMPARISON:
• update_content: When you have the content in memory (easiest for LLMs)
• apply_patch: When you have a pre-generated patch from git/tools
• Edit: When you need simple string find/replace""",
            inputSchema={
                "type": "object",
                "properties": {
                    "file_path": {"type": "string", "description": "Path to the file to update"},
                    "original_content": {
                        "type": "string",
                        "description": "Expected current file content (for verification)",
                    },
                    "new_content": {"type": "string", "description": "Desired new file content"},
                    "dry_run": {
                        "type": "boolean",
                        "description": "Preview changes without applying (default: false)",
                        "default": False,
                    },
                },
                "required": ["file_path", "original_content", "new_content"],
            },
        ),
    ]


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
    elif name == "backup_file":
        result = backup.backup_file(arguments["file_path"])
    elif name == "restore_backup":
        result = backup.restore_backup(
            arguments["backup_file"],
            arguments.get("target_file"),
            arguments.get("force", False),
        )
    elif name == "update_content":
        result = update.update_content(
            arguments["file_path"],
            arguments["original_content"],
            arguments.get("dry_run", False),
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
