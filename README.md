# Patch MCP Server

[![CI](https://github.com/shenning00/patch_mcp/workflows/CI/badge.svg)](https://github.com/shenning00/patch_mcp/actions)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![Coverage](https://img.shields.io/badge/coverage-83%25-brightgreen.svg)](https://github.com/shenning00/patch_mcp)

A [Model Context Protocol (MCP)](https://modelcontextprotocol.io) server that enables AI assistants to safely apply unified diff patches to files with comprehensive security validation and error recovery workflows.

**Version**: 2.0.0 | **Status**: Production Ready | **Tools**: 7 | **Test Coverage**: 83% (244 tests)

---

## Why Patch MCP Server?

Enable your AI assistant to:
- ✅ **Apply code changes** using standard unified diff format
- ✅ **Validate patches** before applying them
- ✅ **Create and restore backups** automatically
- ✅ **Revert changes** safely if something goes wrong
- ✅ **Handle multi-file changes** atomically
- ✅ **Test changes** with dry-run mode before committing

All with **built-in security** (no symlinks, binary files, or directory traversal) and **automatic rollback** on failures.

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

The server provides 7 tools for comprehensive patch management:

### Core Patch Operations

1. **`apply_patch`** - Apply a unified diff patch to a file
   - Supports multi-hunk patches (apply multiple changes atomically)
   - Dry-run mode for testing without modification
   - Automatic validation before application

2. **`validate_patch`** - Check if a patch can be applied (read-only)
   - Preview changes before applying
   - Detect context mismatches
   - See affected line ranges

3. **`revert_patch`** - Reverse a previously applied patch
   - Undo changes safely
   - Works with multi-hunk patches
   - Requires exact original patch

4. **`generate_patch`** - Create a patch from two file versions
   - Compare original and modified files
   - Generate standard unified diff format
   - Configurable context lines

### Analysis & Inspection

5. **`inspect_patch`** - Analyze patch content without files
   - See what files are affected
   - Count hunks and line changes
   - Supports multi-file patches

### Backup & Recovery

6. **`backup_file`** - Create timestamped backups
   - Format: `filename.backup.YYYYMMDD_HHMMSS`
   - Preserves file metadata
   - Automatic disk space checks

7. **`restore_backup`** - Restore from backups
   - Auto-detect original location
   - Safety checks before overwriting
   - Force option available

---

## Example: How an AI Assistant Uses This Server

### Scenario 1: Simple Code Modification

**AI Assistant's thought process:**
> "The user wants to change the timeout from 30 to 60 seconds in config.py. I'll use the patch server to do this safely."

**AI uses tools:**

1. **Generate the patch:**
```
Tool: generate_patch
Args: {
  "original_file": "config.py",
  "modified_file": "config_new.py"
}
```

2. **Validate it can be applied:**
```
Tool: validate_patch
Args: {
  "file_path": "config.py",
  "patch": "--- config.py\n+++ config.py\n@@ -10,3 +10,3 @@\n-timeout = 30\n+timeout = 60"
}
Result: {"can_apply": true, "preview": {"lines_to_add": 1, "lines_to_remove": 1}}
```

3. **Create backup before applying:**
```
Tool: backup_file
Args: {"file_path": "config.py"}
Result: {"backup_file": "config.py.backup.20250118_143052"}
```

4. **Apply the patch:**
```
Tool: apply_patch
Args: {
  "file_path": "config.py",
  "patch": "--- config.py\n+++ config.py\n@@ -10,3 +10,3 @@\n-timeout = 30\n+timeout = 60"
}
Result: {"success": true, "applied": true}
```

**AI reports to user:**
> "I've updated the timeout from 30 to 60 seconds in config.py. A backup was created at config.py.backup.20250118_143052 in case you need to revert."

---

### Scenario 2: Multi-file Refactoring with Dry Run

**AI Assistant's thought process:**
> "The user wants to rename a function across 3 files. I should test this first with dry-run, then apply atomically."

**AI uses tools:**

1. **Test each patch with dry-run:**
```
Tool: apply_patch
Args: {
  "file_path": "utils.py",
  "patch": "...",
  "dry_run": true
}
Result: {"success": true, "changes": {"lines_added": 5, "lines_removed": 5}}
```

2. **Apply all patches atomically:**
```
Uses workflow pattern (if available) or applies each patch with backups
```

**AI reports to user:**
> "I've renamed the function across utils.py, handlers.py, and tests.py. All changes were validated first and applied atomically."

---

### Scenario 3: Something Goes Wrong

**AI Assistant's thought process:**
> "The patch failed to apply. I should revert to the backup."

**AI uses tools:**

```
Tool: restore_backup
Args: {
  "backup_file": "config.py.backup.20250118_143052"
}
Result: {"success": true, "restored_to": "config.py"}
```

**AI reports to user:**
> "The patch couldn't be applied because the file content didn't match. I've restored the original file from backup. The file may have been modified since we discussed the change."

---

## Security Features

All operations include comprehensive security checks:

- 🔒 **Symlink Protection** - Symlinks are rejected (security policy)
- 🔒 **Binary File Detection** - Binary files automatically detected and rejected
- 🔒 **Size Limits** - Maximum 10MB file size
- 🔒 **Disk Space Validation** - Ensures 100MB+ free space before operations
- 🔒 **Path Traversal Protection** - Prevents directory escaping
- 🔒 **Permission Checks** - Validates read/write permissions
- 🔒 **Atomic Operations** - File replacements use atomic rename

See [SECURITY.md](SECURITY.md) for detailed security information.

---

## Error Recovery Workflows

The server includes 4 built-in error recovery patterns accessible via the workflows module:

1. **Try-Revert** - Apply patches sequentially, auto-revert on failure
2. **Backup-Restore** - Automatic backup and restore on failure
3. **Atomic Batch** - All patches succeed or all roll back
4. **Progressive Validation** - Step-by-step with detailed error reporting

See [WORKFLOWS.md](WORKFLOWS.md) for detailed workflow documentation.

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

- **[API.md](docs/API.md)** - Complete API reference for all tools
- **[WORKFLOWS.md](WORKFLOWS.md)** - Error recovery workflow patterns
- **[SECURITY.md](SECURITY.md)** - Security policy and best practices
- **[CONTRIBUTING.md](CONTRIBUTING.md)** - Contributing guidelines
- **[CHANGELOG.md](CHANGELOG.md)** - Version history and changes

### Design Documentation

- **[Project Design](docs/project_design.md)** - Complete design specification
- **[Implementation Guide](docs/AI_IMPLEMENTATION_GUIDE.md)** - Implementation details

---

## Error Types

The server provides 10 distinct error types for precise error handling:

**Standard Errors:**
- `file_not_found`, `permission_denied`, `invalid_patch`, `context_mismatch`, `encoding_error`, `io_error`

**Security Errors:**
- `symlink_error`, `binary_file`, `disk_space_error`, `resource_limit`

See [API.md](docs/API.md) for complete error type documentation.

---

## Testing & Quality

- **244 tests** (all passing)
- **83% code coverage** across all modules
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

**Last Updated**: 2025-01-18 | **Phase**: 5 of 5 (Production Ready) | **Tools**: 7/7 | **Workflow Patterns**: 4/4
