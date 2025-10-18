"""Manual test for MCP server functionality.

This script demonstrates how to test the MCP server by calling all tools
through the MCP protocol using the stdio client.

NOTE: This is for manual/integration testing. The automated unit tests
are in test_server.py.

Usage:
    python tests/manual_test_server.py
"""

import asyncio
import json
import tempfile
from pathlib import Path

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


async def test_server() -> None:
    """Test MCP server by calling all tools."""

    print("Starting MCP Server Manual Test")
    print("=" * 60)

    # Configure server
    server_params = StdioServerParameters(
        command="python",
        args=["-m", "patch_mcp"],
    )

    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            # Initialize
            await session.initialize()
            print("\nServer initialized successfully")

            # Test 1: List tools
            print("\n1. LISTING TOOLS")
            print("-" * 60)
            tools = await session.list_tools()
            print(f"Available tools: {len(tools.tools)}")
            for tool in tools.tools:
                print(f"  - {tool.name}: {tool.description}")

            # Test 2: inspect_patch (no file needed)
            print("\n2. TESTING inspect_patch")
            print("-" * 60)
            test_patch = """--- test.txt
+++ test.txt
@@ -1,3 +1,4 @@
 line1
+line1.5
 line2
 line3
"""
            result = await session.call_tool("inspect_patch", arguments={"patch": test_patch})
            data = json.loads(result.content[0].text)
            print(f"Success: {data['success']}")
            print(f"Files affected: {data['summary']['total_files']}")
            print(f"Lines added: {data['summary']['total_lines_added']}")
            print(f"Lines removed: {data['summary']['total_lines_removed']}")

            # Create temporary test files
            with tempfile.TemporaryDirectory() as tmpdir:
                tmp_path = Path(tmpdir)

                # Test 3: generate_patch
                print("\n3. TESTING generate_patch")
                print("-" * 60)
                original = tmp_path / "original.txt"
                modified = tmp_path / "modified.txt"
                original.write_text("line1\nline2\nline3\n")
                modified.write_text("line1\nline2_modified\nline3\n")

                result = await session.call_tool(
                    "generate_patch",
                    arguments={
                        "original_file": str(original),
                        "modified_file": str(modified),
                    },
                )
                data = json.loads(result.content[0].text)
                print(f"Success: {data['success']}")
                print(f"Lines added: {data['changes']['lines_added']}")
                print(f"Lines removed: {data['changes']['lines_removed']}")
                generated_patch = data["patch"]

                # Test 4: validate_patch
                print("\n4. TESTING validate_patch")
                print("-" * 60)
                result = await session.call_tool(
                    "validate_patch",
                    arguments={
                        "file_path": str(original),
                        "patch": generated_patch,
                    },
                )
                data = json.loads(result.content[0].text)
                print(f"Success: {data['success']}")
                print(f"Can apply: {data['can_apply']}")
                print(f"Preview lines to add: {data['preview']['lines_to_add']}")

                # Test 5: backup_file
                print("\n5. TESTING backup_file")
                print("-" * 60)
                test_file = tmp_path / "backup_test.txt"
                test_file.write_text("important content\n")

                result = await session.call_tool(
                    "backup_file",
                    arguments={"file_path": str(test_file)},
                )
                data = json.loads(result.content[0].text)
                print(f"Success: {data['success']}")
                print(f"Backup file: {Path(data['backup_file']).name}")
                print(f"Backup size: {data['backup_size']} bytes")
                backup_file = data["backup_file"]

                # Test 6: apply_patch (dry run)
                print("\n6. TESTING apply_patch (dry_run=True)")
                print("-" * 60)
                result = await session.call_tool(
                    "apply_patch",
                    arguments={
                        "file_path": str(original),
                        "patch": generated_patch,
                        "dry_run": True,
                    },
                )
                data = json.loads(result.content[0].text)
                print(f"Success: {data['success']}")
                print(f"Applied (dry run): {data['applied']}")
                print(f"Message: {data['message']}")

                # Test 7: apply_patch (real)
                print("\n7. TESTING apply_patch (real)")
                print("-" * 60)
                result = await session.call_tool(
                    "apply_patch",
                    arguments={
                        "file_path": str(original),
                        "patch": generated_patch,
                    },
                )
                data = json.loads(result.content[0].text)
                print(f"Success: {data['success']}")
                print(f"Applied: {data['applied']}")
                print(f"Lines added: {data['changes']['lines_added']}")

                # Test 8: revert_patch
                print("\n8. TESTING revert_patch")
                print("-" * 60)
                result = await session.call_tool(
                    "revert_patch",
                    arguments={
                        "file_path": str(original),
                        "patch": generated_patch,
                    },
                )
                data = json.loads(result.content[0].text)
                print(f"Success: {data['success']}")
                print(f"Reverted: {data['reverted']}")
                print(f"Lines added (revert): {data['changes']['lines_added']}")

                # Test 9: restore_backup
                print("\n9. TESTING restore_backup")
                print("-" * 60)
                # Modify the file first
                test_file.write_text("modified content\n")

                result = await session.call_tool(
                    "restore_backup",
                    arguments={
                        "backup_file": backup_file,
                        "force": True,
                    },
                )
                data = json.loads(result.content[0].text)
                print(f"Success: {data['success']}")
                print(f"Restored to: {Path(data['restored_to']).name}")
                print(f"Restored size: {data['restored_size']} bytes")

                # Verify restoration
                restored_content = test_file.read_text()
                expected = "important content\n"
                print(f"Content restored correctly: {restored_content == expected}")

            print("\n" + "=" * 60)
            print("ALL TESTS COMPLETED SUCCESSFULLY")
            print("=" * 60)


async def test_error_handling() -> None:
    """Test error handling in the server."""

    print("\n\nTesting Error Handling")
    print("=" * 60)

    server_params = StdioServerParameters(
        command="python",
        args=["-m", "patch_mcp"],
    )

    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()

            # Test 1: Unknown tool
            print("\n1. Testing unknown tool error")
            print("-" * 60)
            try:
                await session.call_tool("unknown_tool", arguments={})
                print("ERROR: Should have raised an exception")
            except Exception as e:
                print(f"Correctly raised error: {type(e).__name__}")

            # Test 2: Invalid patch format
            print("\n2. Testing invalid patch error")
            print("-" * 60)
            result = await session.call_tool(
                "inspect_patch",
                arguments={"patch": "not a valid patch"},
            )
            data = json.loads(result.content[0].text)
            print(f"Success: {data['success']}")
            print(f"Error type: {data.get('error_type', 'N/A')}")

            # Test 3: File not found
            print("\n3. Testing file not found error")
            print("-" * 60)
            result = await session.call_tool(
                "validate_patch",
                arguments={
                    "file_path": "/nonexistent/file.txt",
                    "patch": "--- file\n+++ file\n",
                },
            )
            data = json.loads(result.content[0].text)
            print(f"Success: {data['success']}")
            print(f"Error type: {data.get('error_type', 'N/A')}")

            print("\n" + "=" * 60)
            print("ERROR HANDLING TESTS COMPLETED")
            print("=" * 60)


async def main() -> None:
    """Run all manual tests."""
    try:
        await test_server()
        await test_error_handling()
    except Exception as e:
        print(f"\n\nFATAL ERROR: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    print(__doc__)
    asyncio.run(main())
