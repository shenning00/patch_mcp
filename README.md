# Patch MCP Server

[![CI](https://github.com/shenning00/patch_mcp/workflows/CI/badge.svg)](https://github.com/shenning00/patch_mcp/actions)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![Coverage](https://img.shields.io/badge/coverage-79%25-green.svg)](https://github.com/shenning00/patch_mcp)

A [Model Context Protocol (MCP)](https://modelcontextprotocol.io) server that enables AI assistants to safely apply unified diff patches to files with comprehensive security validation.

**Version**: 3.0.0 | **Status**: Beta | **Tools**: 5 | **Test Coverage**: 79%

---

## Why Patch MCP Server?

Enable your AI assistant to:
- ✅ **Update files** with content you have in memory (easiest for LLMs!)
- ✅ **Apply code changes** using standard unified diff format
- ✅ **Validate patches** before applying them
- ✅ **Create and restore backups** automatically
- ✅ **Apply multiple changes atomically** via multi-hunk patches
- ✅ **Test changes** with dry-run mode before committing

All with **built-in security** (no symlinks, binary files, or directory traversal) and **comprehensive safety features**.

**v3.0.1 enhancement**: Added `update_content` - the simplest way for LLMs to modify files when you have the content in memory!

---

## Quick Start

### Installation

```bash
# Clone the repository
git clone https://github.com/shenning00/patch_mcp.git
cd patch_mcp

# Create virtual environment and install
python3 -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
pip install -e ".[dev]"
```

### Configure with Claude Desktop

Add to your Claude Desktop MCP configuration (`~/Library/Application Support/Claude/claude_desktop_config.json` on macOS):

```json
{
  "mcpServers": {
    "patch": {
      "command": "python",
      "args": ["-m", "patch_mcp"],
      "cwd": "/path/to/patch_mcp"
    }
  }
}
```

Restart Claude Desktop and the patch tools will be available.

### Run Standalone

```bash
python -m patch_mcp
```

The server runs in stdio mode and communicates via the Model Context Protocol.

---

## Available Tools

The server provides 5 tools for safe, efficient patch management:

### Recommended for LLMs

**⭐ `update_content`** - Update file when you have the content in memory
   - **Simplest API**: Just provide original and new content
   - **Safety verification**: Confirms file hasn't changed since you read it
   - **Auto-generates diff**: No manual patch creation needed
   - **Reviewable**: Returns unified diff showing changes
   - **Dry-run support**: Preview before applying

   **When to use**: You've read a file and want to modify it (most common LLM use case!)

### Core Patch Operations

1. **`apply_patch`** - Apply a unified diff patch to a file
   - Supports multi-hunk patches (apply multiple changes atomically)
   - Dry-run mode for testing without modification
   - Automatic validation before application
   - ~50% more token-efficient than Edit operations

   **When to use**: You have a pre-generated patch from git or other tools

2. **`validate_patch`** - Check if a patch can be applied (read-only)
   - Preview changes before applying
   - Detect context mismatches
   - See affected line ranges
   - No file modification

### Backup & Recovery

3. **`backup_file`** - Create timestamped backups
   - Format: `filename.backup.YYYYMMDD_HHMMSS`
   - Preserves file metadata
   - Automatic disk space checks

4. **`restore_backup`** - Restore from backups
   - Auto-detect original location
   - Safety checks before overwriting
   - Force option available

---

## Tool Comparison: When to Use Which Tool?

| Tool | Use When | Input Required | Generates Diff? |
|------|----------|----------------|-----------------|
| **update_content** | You have file content in memory | original_content + new_content | ✅ Yes |
| **apply_patch** | You have a pre-made patch | unified diff patch | ❌ No (patch provided) |
| **Edit (Claude's built-in)** | Simple string find/replace | old_string + new_string | ❌ No |

**Recommendation for LLMs**: Use `update_content` for most file modifications - it's the simplest and safest option!

---

## Example: How an AI Assistant Uses This Server

### Scenario 1: Simple Code Modification (with update_content)

**AI Assistant's thought process:**
> "The user wants to change the timeout from 30 to 60 seconds in config.py. I'll use update_content since I have the file in memory."

**AI uses tools:**

1. **Read the file** (using built-in Read tool):
```python
original_content = """
timeout = 30
retries = 3
debug = False
"""
```

2. **Construct new content in memory**:
```python
new_content = """
timeout = 60
retries = 3
debug = False
"""
```

3. **Update with safety verification**:
```
Tool: update_content
Args: {
  "file_path": "config.py",
  "original_content": "timeout = 30\nretries = 3\ndebug = False\n",
  "new_content": "timeout = 60\nretries = 3\ndebug = False\n",
  "dry_run": false
}
Result: {
  "success": true,
  "applied": true,
  "diff": "--- config.py\n+++ config.py\n@@ -1,3 +1,3 @@\n-timeout = 30\n+timeout = 60\n retries = 3\n debug = False",
  "changes": {"lines_added": 1, "lines_removed": 1, "hunks": 1}
}
```

**AI reports to user:**
> "I've updated the timeout from 30 to 60 seconds in config.py."

**Advantages of update_content:**
- ✅ No manual patch creation
- ✅ Verifies file hasn't changed
- ✅ Returns diff for review
- ✅ Single tool call

---

### Scenario 2: Using apply_patch with Pre-Generated Patch

**When to use apply_patch instead of update_content:**
- You have a patch from `git diff`
- You're applying patches from a patch file
- You want maximum token efficiency (patch is smaller than full content)

**AI uses tools:**

1. **Validate it can be applied:**
```
Tool: validate_patch
Args: {
  "file_path": "config.py",
  "patch": "--- config.py\n+++ config.py\n@@ -10,3 +10,3 @@\n-timeout = 30\n+timeout = 60"
}
Result: {
  "success": true,
  "can_apply": true
}
```

2. **Apply the patch:**
```
Tool: apply_patch
Args: {
  "file_path": "config.py",
  "patch": "--- config.py\n+++ config.py\n@@ -10,3 +10,3 @@\n-timeout = 30\n+timeout = 60"
}
Result: {"success": true, "applied": true}
```

---

## Security Features

All operations include comprehensive security checks:

- 🔒 **Symlink Protection** - Symlinks are rejected (security policy)
- 🔒 **Binary File Detection** - Binary files automatically detected and rejected
- 🔒 **Size Limits** - Maximum 10MB file size
- 🔒 **Disk Space Validation** - Ensures 100MB+ free space before operations
- 🔒 **Permission Checks** - Validates read/write permissions
- 🔒 **Atomic Operations** - File replacements use atomic rename
- 🔒 **Content Verification** - update_content verifies file hasn't changed

See [SECURITY.md](SECURITY.md) for detailed security information.

---

## Multi-Hunk Patches

A powerful feature: apply multiple changes to different parts of a file **atomically** in a single patch:

```diff
--- config.py
+++ config.py
@@ -10,3 +10,3 @@
 # Connection settings
-timeout = 30
+timeout = 60

@@ -25,3 +25,3 @@
 # Retry settings
-retries = 3
+retries = 5

@@ -50,3 +50,3 @@
 # Debug settings
-debug = False
+debug = True
```

All three changes are applied together or none are applied. If any hunk fails, the entire patch is rejected.

---

## Documentation

- **[DEPRECATION.md](DEPRECATION.md)** - v3.0 migration guide
- **[SECURITY.md](SECURITY.md)** - Security policy and best practices
- **[WORKFLOWS.md](WORKFLOWS.md)** - Error recovery workflow patterns
- **[CONTRIBUTING.md](CONTRIBUTING.md)** - Contributing guidelines
- **[CHANGELOG.md](CHANGELOG.md)** - Version history and changes

## Error Types

The server provides 10 distinct error types for precise error handling:

**Standard Errors:**
- `file_not_found`, `permission_denied`, `invalid_patch`, `context_mismatch`, `encoding_error`, `io_error`

**Security Errors:**
- `symlink_error`, `binary_file`, `disk_space_error`, `resource_limit`

**Special Errors (update_content):**
- `content_mismatch` - File has changed since you read it

---

## Testing & Quality

- **113 tests** (all passing)
- **79% code coverage** across all modules
- **Strict type checking** with mypy
- **Code formatting** with black
- **Linting** with ruff
- **CI/CD** via GitHub Actions (Linux, macOS, Windows)

```bash
# Run tests
pytest tests/ -v --cov=src/patch_mcp

# Check code quality
black src/patch_mcp tests/
ruff check src/patch_mcp tests/
mypy src/patch_mcp --strict
```

---

## Contributing

Contributions are welcome! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for:
- Development setup
- Testing guidelines
- Code quality standards
- Commit message conventions

---

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

**Author**: Scott Henning

---

## Support

- **Issues**: [GitHub Issues](https://github.com/shenning00/patch_mcp/issues)
- **Discussions**: [GitHub Discussions](https://github.com/shenning00/patch_mcp/discussions)
- **Security**: See [SECURITY.md](SECURITY.md) for vulnerability reporting

---

## Model Context Protocol

This server implements the [Model Context Protocol (MCP)](https://modelcontextprotocol.io), an open protocol that enables AI assistants to securely interact with local tools and data sources.

**Learn more:**
- [MCP Documentation](https://modelcontextprotocol.io/docs)
- [MCP Specification](https://spec.modelcontextprotocol.io/)
- [Claude Desktop Integration](https://modelcontextprotocol.io/docs/tools/claude-desktop)

---

**Last Updated**: 2025-01-19 | **Phase**: 5 of 5 (Beta) | **Tools**: 5 core tools | **Version**: 3.0.1
