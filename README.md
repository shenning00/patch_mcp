# File Patch MCP Server

[![CI](https://github.com/shenning00/patch_mcp/workflows/CI/badge.svg)](https://github.com/shenning00/patch_mcp/actions)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![Coverage](https://img.shields.io/badge/coverage-83%25-brightgreen.svg)](https://github.com/shenning00/patch_mcp)

**Version**: 2.0.0
**Status**: Phase 5 Complete - Production Ready
**Coverage**: 83% overall (244 tests passing)

## Overview

A Model Context Protocol (MCP) server for applying unified diff patches to files with comprehensive security validation and error recovery workflows. This server provides 7 tools for patch management with automatic backup, rollback, and atomic operations.

## Features

- **7 Powerful Tools**: Complete patch lifecycle management
- **4 Error Recovery Patterns**: Safe workflows with automatic rollback
- **Comprehensive Security**: Symlink, binary file, disk space, and size validation
- **Atomic Operations**: All-or-nothing multi-file patch application
- **Dry Run Support**: Test patches without modification
- **Multi-file Support**: Handle patches affecting multiple files
- **Automatic Backup & Restore**: Safe experimentation with rollback

## Quick Start

### Installation

```bash
# Clone the repository
git clone https://github.com/shenning00/patch_mcp.git
cd patch-ng-mcp
python3 -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install in development mode
pip install -e ".[dev]"
```

### Basic Usage

```python
from patch_mcp.tools.apply import apply_patch
from patch_mcp.tools.validate import validate_patch
from patch_mcp.tools.backup import backup_file, restore_backup

# Validate a patch first
result = validate_patch("config.py", patch)
if result["can_apply"]:
    # Create backup before applying
    backup = backup_file("config.py")

    # Apply the patch
    result = apply_patch("config.py", patch)

    if not result["success"]:
        # Restore from backup if failed
        restore_backup(backup["backup_file"])
```

### Using Workflow Patterns

```python
from patch_mcp.workflows import (
    apply_patches_with_revert,
    apply_patch_with_backup,
    apply_patches_atomic,
    apply_patch_progressive,
)

# Pattern 1: Sequential patches with automatic revert
result = apply_patches_with_revert("app.py", [patch1, patch2, patch3])

# Pattern 2: Safe experimentation with backup
result = apply_patch_with_backup("critical.py", patch, keep_backup=True)

# Pattern 3: Atomic multi-file application
pairs = [("file1.py", patch1), ("file2.py", patch2)]
result = apply_patches_atomic(pairs)

# Pattern 4: Progressive validation with detailed reporting
result = apply_patch_progressive("module.py", patch)
```

## Available Tools

### Core Patch Tools

1. **apply_patch** - Apply a patch to a file (supports dry_run)
2. **validate_patch** - Check if a patch can be applied (read-only)
3. **revert_patch** - Reverse a previously applied patch
4. **generate_patch** - Create a patch from two files

### Analysis Tools

5. **inspect_patch** - Analyze patch content (supports multi-file patches)

### Backup Tools

6. **backup_file** - Create a timestamped backup
7. **restore_backup** - Restore a file from backup

## Error Recovery Patterns

The server provides 4 workflow patterns for safe patch operations:

### Pattern 1: Try-Revert (Sequential Patches)
Apply multiple patches sequentially with automatic revert on failure.

```python
from patch_mcp.workflows import apply_patches_with_revert

result = apply_patches_with_revert("config.py", [patch1, patch2, patch3])
# If patch2 fails, patch1 is automatically reverted
```

**Use cases**: Multi-step refactoring, dependent patches

### Pattern 2: Backup-Restore (Safe Experimentation)
Apply patch with automatic backup and restore on failure.

```python
from patch_mcp.workflows import apply_patch_with_backup

result = apply_patch_with_backup("app.py", patch, keep_backup=True)
# Automatically restores from backup if patch fails
```

**Use cases**: Critical files, experimental changes, production updates

### Pattern 3: Validate-All-Then-Apply (Atomic Batch)
Apply multiple patches atomically - all succeed or all rollback.

```python
from patch_mcp.workflows import apply_patches_atomic

pairs = [
    ("src/config.py", config_patch),
    ("src/utils.py", utils_patch),
    ("src/main.py", main_patch),
]
result = apply_patches_atomic(pairs)
# All patches applied atomically or all rolled back
```

**Use cases**: Multi-file refactoring, coordinated changes, consistency requirements

### Pattern 4: Progressive Validation
Step-by-step validation with detailed error reporting.

```python
from patch_mcp.workflows import apply_patch_progressive

result = apply_patch_progressive("module.py", patch)
# Returns detailed information about each step:
# - safety_check, validation, backup, apply, restore
```

**Use cases**: Debugging, troubleshooting, learning

For detailed documentation, see [WORKFLOWS.md](WORKFLOWS.md).

## Security Features

All file operations include comprehensive security checks:

- ✅ **Symlink Detection**: Symlinks rejected (security policy)
- ✅ **Binary File Detection**: Binary files not supported
- ✅ **File Size Limits**: 10MB maximum file size
- ✅ **Disk Space Validation**: 100MB minimum free space required
- ✅ **Path Traversal Protection**: Prevents directory escaping
- ✅ **Permission Checks**: Read/write permissions validated
- ✅ **Atomic Operations**: File replacements use atomic rename

### Configuration Constants

```python
MAX_FILE_SIZE = 10 * 1024 * 1024   # 10MB
MIN_FREE_SPACE = 100 * 1024 * 1024  # 100MB
BINARY_CHECK_BYTES = 8192           # First 8KB checked
NON_TEXT_THRESHOLD = 0.3            # 30% non-text = binary
```

## Testing

### Run All Tests

```bash
# Run all tests with coverage
pytest tests/ -v --cov=src/patch_mcp --cov-report=term --cov-report=html

# Run specific test suites
pytest tests/test_apply.py -v
pytest tests/integration/test_workflows.py -v
pytest tests/integration/test_example_workflows.py -v

# View coverage report
# Open htmlcov/index.html in browser
```

### Test Statistics

- **Total Tests**: 244 (all passing)
- **Overall Coverage**: 83%
- **Unit Tests**: 209 tests
- **Integration Tests**: 35 tests
- **Workflow Tests**: 21 tests
- **Example Workflow Tests**: 14 tests

### Coverage Breakdown

| Module | Coverage |
|--------|----------|
| models.py | 100% |
| inspect.py | 99% |
| validate.py | 92% |
| revert.py | 91% |
| utils.py | 88% |
| apply.py | 87% |
| server.py | 86% |
| generate.py | 81% |
| backup.py | 70% |
| workflows.py | 70% |

## Project Structure

```
patch-ng-mcp/
├── src/
│   └── patch_mcp/
│       ├── __init__.py           # Package initialization
│       ├── models.py             # Pydantic data models (100% coverage)
│       ├── utils.py              # Security utilities (88% coverage)
│       ├── workflows.py          # Error recovery patterns (70% coverage)
│       ├── server.py             # MCP server (86% coverage)
│       └── tools/
│           ├── __init__.py
│           ├── apply.py          # apply_patch (87% coverage)
│           ├── validate.py       # validate_patch (92% coverage)
│           ├── revert.py         # revert_patch (91% coverage)
│           ├── generate.py       # generate_patch (81% coverage)
│           ├── inspect.py        # inspect_patch (99% coverage)
│           └── backup.py         # backup_file, restore_backup (70% coverage)
├── tests/
│   ├── test_models.py            # Model tests (33 tests)
│   ├── test_security.py          # Security tests (40 tests)
│   ├── test_apply.py             # Apply tests (17 tests)
│   ├── test_validate.py          # Validate tests (17 tests)
│   ├── test_revert.py            # Revert tests (12 tests)
│   ├── test_generate.py          # Generate tests (11 tests)
│   ├── test_inspect.py           # Inspect tests (14 tests)
│   ├── test_backup.py            # Backup tests (32 tests)
│   ├── test_server.py            # Server tests (20 tests)
│   ├── test_api_semantics.py     # API correctness tests (13 tests)
│   └── integration/
│       ├── test_workflows.py     # Workflow tests (21 tests)
│       └── test_example_workflows.py # Example workflows (14 tests)
├── pyproject.toml                # Project configuration
├── README.md                     # This file
├── WORKFLOWS.md                  # Workflow patterns documentation
├── project_design.md             # Complete design specification (2,409 lines)
└── AI_IMPLEMENTATION_GUIDE.md    # Implementation guide (970 lines)
```

## Implementation Phases

### Phase 1: Foundation ✅
- Data models (Pydantic)
- Security utilities
- Test infrastructure

### Phase 2: Core Tools ✅
- apply_patch (with dry_run)
- validate_patch
- revert_patch
- generate_patch
- inspect_patch (multi-file support)

### Phase 3: Backup Tools ✅
- backup_file
- restore_backup

### Phase 4: MCP Server ✅
- Server implementation
- Tool registration
- MCP protocol integration

### Phase 5: Error Recovery Patterns ✅
- Try-Revert pattern
- Backup-Restore pattern
- Atomic Batch pattern
- Progressive Validation pattern
- Comprehensive integration tests
- Example workflow tests

## API Correctness

All tools follow consistent API semantics:

### validate_patch Return Values

**Can apply** (success):
```python
{
    "success": True,
    "can_apply": True,
    "valid": True,
    "preview": {...}
}
```

**Cannot apply** (failure):
```python
{
    "success": False,  # Note: False when can't apply
    "can_apply": False,
    "valid": True,
    "reason": "Context mismatch...",
    "error_type": "context_mismatch"
}
```

### inspect_patch Return Values

Always returns array of files (multi-file support):
```python
{
    "success": True,
    "files": [  # Always an array
        {"source": "config.py", "target": "config.py", ...}
    ],
    "summary": {
        "total_files": 1,
        "total_hunks": 2,
        ...
    }
}
```

## Error Types

The server provides 10 distinct error types:

**Standard Errors**:
- `file_not_found` - File doesn't exist
- `permission_denied` - Cannot read/write file
- `invalid_patch` - Patch format is malformed
- `context_mismatch` - Patch context doesn't match file content
- `encoding_error` - File encoding issue
- `io_error` - General I/O error

**Security Errors**:
- `symlink_error` - Target is a symlink (security policy)
- `binary_file` - Target is a binary file (not supported)
- `disk_space_error` - Insufficient disk space
- `resource_limit` - File too large or operation timed out

## Code Quality

```bash
# Format code
black src/patch_mcp tests/

# Run linting
ruff check src/patch_mcp tests/

# Type checking
mypy src/patch_mcp --strict
```

## MCP Server Usage

Run the MCP server:

```bash
python -m patch_mcp
```

Or use with Claude Desktop by adding to your MCP configuration.

## Documentation

- **[WORKFLOWS.md](WORKFLOWS.md)** - Complete guide to error recovery patterns
- **[project_design.md](project_design.md)** - Full design specification
- **[AI_IMPLEMENTATION_GUIDE.md](AI_IMPLEMENTATION_GUIDE.md)** - Implementation details

## Example Workflows

### Safe Single Patch Application

```python
from patch_mcp.tools.validate import validate_patch
from patch_mcp.tools.backup import backup_file, restore_backup
from patch_mcp.tools.apply import apply_patch

# Step 1: Validate
validation = validate_patch("config.py", patch)
if not validation["can_apply"]:
    print(f"Cannot apply: {validation['reason']}")
    exit(1)

# Step 2: Backup
backup = backup_file("config.py")

# Step 3: Apply
result = apply_patch("config.py", patch)

if not result["success"]:
    # Restore on failure
    restore_backup(backup["backup_file"])
```

### Dry Run Test Before Apply

```python
from patch_mcp.tools.apply import apply_patch
from patch_mcp.tools.backup import backup_file

# Test without modifying
dry_result = apply_patch("app.py", patch, dry_run=True)

if dry_result["success"]:
    print(f"Would change {dry_result['changes']['lines_added']} lines")

    # Apply for real
    backup = backup_file("app.py")
    real_result = apply_patch("app.py", patch)
```

### Multi-file Atomic Application

```python
from patch_mcp.workflows import apply_patches_atomic

patches = [
    ("file1.py", patch1),
    ("file2.py", patch2),
    ("file3.py", patch3),
]

result = apply_patches_atomic(patches)

if result["success"]:
    print(f"Applied {result['applied']} patches atomically")
else:
    print(f"Failed at {result.get('failed_at')}, rolled back")
```


This project follows strict type checking, comprehensive testing, and security-first design principles.

## License

This project is part of the File Patch MCP Server implementation.
This project is part of the File Patch MCP Server implementation.

---

**Last Updated**: 2025-10-17
**Phase**: 5 of 5 (Complete - Production Ready)
**Tools Implemented**: 7/7
**Workflow Patterns**: 4/4
**Test Coverage**: 83% (244 tests passing)
