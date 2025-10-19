"""Unit tests for MCP server registration.

Tests the server initialization, tool registration, and routing
without requiring actual MCP protocol communication.
"""

import json

import pytest

from patch_mcp.server import call_tool, list_tools, server


class TestServerInitialization:
    """Test server initialization and metadata."""

    def test_server_name(self):
        """Server has correct name."""
        assert server.name == "patch-mcp"

    def test_server_instance(self):
        """Server is a valid MCP Server instance."""
        from mcp.server import Server

        assert isinstance(server, Server)


class TestToolRegistration:
    """Test tool registration and schemas."""

    @pytest.mark.asyncio
    async def test_list_tools_count(self):
        """All 5 core tools are registered."""
        tools = await list_tools()
        assert len(tools) == 5

    @pytest.mark.asyncio
    async def test_tool_names(self):
        """All expected tool names are present."""
        tools = await list_tools()
        tool_names = {tool.name for tool in tools}

        expected_names = {
            "apply_patch",
            "validate_patch",
            "backup_file",
            "restore_backup",
            "update_content",
        }

        assert tool_names == expected_names
        assert tool_names == expected_names

    @pytest.mark.asyncio
    async def test_all_tools_have_descriptions(self):
        """All tools have descriptions."""
        tools = await list_tools()

        for tool in tools:
            assert tool.description
            assert len(tool.description) > 0

    @pytest.mark.asyncio
    async def test_all_tools_have_schemas(self):
        """All tools have proper input schemas."""
        tools = await list_tools()

        for tool in tools:
            tool_dict = tool.model_dump()
            assert "inputSchema" in tool_dict
            schema = tool_dict["inputSchema"]
            assert "type" in schema
            assert schema["type"] == "object"
            assert "properties" in schema
            assert "required" in schema


class TestToolSchemas:
    """Test individual tool schemas."""

    @pytest.mark.asyncio
    async def test_apply_patch_schema(self):
        """apply_patch has correct schema."""
        tools = await list_tools()
        apply_tool = next(t for t in tools if t.name == "apply_patch")

        schema = apply_tool.inputSchema
        assert "file_path" in schema["properties"]
        assert "patch" in schema["properties"]
        assert "dry_run" in schema["properties"]
        assert set(schema["required"]) == {"file_path", "patch"}

        # Check dry_run has default
        assert schema["properties"]["dry_run"]["default"] is False

    @pytest.mark.asyncio
    async def test_validate_patch_schema(self):
        """validate_patch has correct schema."""
        tools = await list_tools()
        validate_tool = next(t for t in tools if t.name == "validate_patch")

        schema = validate_tool.inputSchema
        assert "file_path" in schema["properties"]
        assert "patch" in schema["properties"]
        assert set(schema["required"]) == {"file_path", "patch"}

    @pytest.mark.asyncio
    async def test_backup_file_schema(self):
        """backup_file has correct schema."""
        tools = await list_tools()
        backup_tool = next(t for t in tools if t.name == "backup_file")

        schema = backup_tool.inputSchema
        assert "file_path" in schema["properties"]
        assert schema["required"] == ["file_path"]

    @pytest.mark.asyncio
    async def test_restore_backup_schema(self):
        """restore_backup has correct schema."""
        tools = await list_tools()
        restore_tool = next(t for t in tools if t.name == "restore_backup")

        schema = restore_tool.inputSchema
        assert "backup_file" in schema["properties"]
        assert "target_file" in schema["properties"]
        assert "force" in schema["properties"]
        assert schema["required"] == ["backup_file"]

        # Check force has default
        assert schema["properties"]["force"]["default"] is False


class TestToolRouting:
    """Test tool routing and execution."""

    @pytest.mark.asyncio
    async def test_call_unknown_tool(self):
        """Unknown tool raises ValueError."""
        with pytest.raises(ValueError, match="Unknown tool"):
            await call_tool("unknown_tool", {})

    @pytest.mark.asyncio
    async def test_call_tool_returns_text_content(self, tmp_path):
        """Tool calls return TextContent with JSON."""
        # Create a test file
        test_file = tmp_path / "test.txt"
        test_file.write_text("line1\nline2\n")

        # Create a patch
        patch = """--- test.txt
+++ test.txt
@@ -1,2 +1,2 @@
-line1
+line1_modified
 line2
"""

        # Call validate_patch (safe, read-only)
        result = await call_tool(
            "validate_patch",
            {
                "file_path": str(test_file),
                "patch": patch,
            },
        )

        # Check return type
        assert isinstance(result, list)
        assert len(result) == 1
        assert result[0].type == "text"

        # Check JSON is valid
        parsed = json.loads(result[0].text)
        assert "success" in parsed

    @pytest.mark.asyncio
    async def test_backup_file_routing(self, tmp_path):
        """backup_file routes correctly."""
        test_file = tmp_path / "backup_test.txt"
        test_file.write_text("content")

        result = await call_tool("backup_file", {"file_path": str(test_file)})

        parsed = json.loads(result[0].text)
        assert parsed["success"] is True
        assert "backup_file" in parsed


class TestToolIntegration:
    """Test tool integration and data flow."""

    @pytest.mark.asyncio
    async def test_validate_then_apply_flow(self, tmp_path):
        """Test validate followed by apply workflow."""
        # Setup
        test_file = tmp_path / "flow_test.txt"
        test_file.write_text("line1\nline2\n")

        patch = """--- flow_test.txt
+++ flow_test.txt
@@ -1,2 +1,2 @@
 line1
-line2
+line2_modified
"""

        # Step 1: Validate
        validate_result = await call_tool(
            "validate_patch",
            {
                "file_path": str(test_file),
                "patch": patch,
            },
        )

        validate_data = json.loads(validate_result[0].text)
        assert validate_data["success"] is True
        assert validate_data["can_apply"] is True

        # Step 2: Apply
        apply_result = await call_tool(
            "apply_patch",
            {
                "file_path": str(test_file),
                "patch": patch,
            },
        )

        apply_data = json.loads(apply_result[0].text)
        assert apply_data["success"] is True
        assert apply_data["applied"] is True

    @pytest.mark.asyncio
    async def test_backup_and_restore_flow(self, tmp_path):
        """Test backup followed by restore workflow."""
        # Setup
        test_file = tmp_path / "backup_restore_test.txt"
        original_content = "original content\n"
        test_file.write_text(original_content)

        # Step 1: Backup
        backup_result = await call_tool(
            "backup_file",
            {"file_path": str(test_file)},
        )

        backup_data = json.loads(backup_result[0].text)
        assert backup_data["success"] is True
        backup_file_path = backup_data["backup_file"]

        # Step 2: Modify file
        test_file.write_text("modified content\n")

        # Step 3: Restore
        restore_result = await call_tool(
            "restore_backup",
            {"backup_file": backup_file_path},
        )

        restore_data = json.loads(restore_result[0].text)
        assert restore_data["success"] is True

        # Verify content restored
        assert test_file.read_text() == original_content
