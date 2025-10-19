# Deprecation Guide: v2.0 → v3.0

## Overview

Version 3.0.0 removes 3 tools from the MCP server interface, simplifying from 7 tools to 4 core tools. This document explains the rationale and provides migration guidance.

## Removed Tools

### 1. `revert_patch` - REMOVED

**Rationale**: Redundant with `apply_patch`

- **What it did**: Reversed a previously applied patch by swapping +/- lines
- **Why removed**:
  - Implementation just reverses the patch and calls `apply_patch`
  - LLMs can reverse patches mentally (swap + and -)
  - Git workflows (`git revert`, `git checkout`) are more common for undoing changes
  - Adds 173 lines of code + 355 lines of tests for marginal benefit
  - The backup/restore pattern is safer for undoing changes

**Migration**:

```python
# v2.0 - Using revert_patch
revert_patch(file_path="config.py", patch=original_patch)

# v3.0 - Reverse the patch manually and use apply_patch
reversed_patch = """
--- config.py
+++ config.py
@@ -10,3 +10,3 @@
-timeout = 60
+timeout = 30
"""
apply_patch(file_path="config.py", patch=reversed_patch)

# v3.0 - OR use backup/restore pattern (recommended)
backup_file("config.py")
apply_patch("config.py", patch)
# If you need to undo:
restore_backup("config.py.backup.20250119_143052")
```

---

### 2. `generate_patch` - REMOVED

**Rationale**: Uncommon workflow, LLMs generate patches mentally

- **What it did**: Created a unified diff patch from two existing file versions
- **Why removed**:
  - Requires two existing file versions (uncommon LLM workflow)
  - LLMs generate patches mentally from file content + desired changes
  - Git already provides `git diff` for comparing files
  - Adds 171 lines of code + 254 lines of tests for minimal value
  - Primary use case is LLM editing, which starts from current file state

**Migration**:

```python
# v2.0 - Using generate_patch
generate_patch(
    original_file="config.py",
    modified_file="config_new.py",
    context_lines=3
)

# v3.0 - Use git diff instead
import subprocess
result = subprocess.run(
    ["git", "diff", "--no-index", "config.py", "config_new.py"],
    capture_output=True,
    text=True
)
patch = result.stdout

# v3.0 - Or use Python's difflib
import difflib
from pathlib import Path

original = Path("config.py").read_text().splitlines(keepends=True)
modified = Path("config_new.py").read_text().splitlines(keepends=True)
patch = "".join(difflib.unified_diff(original, modified,
                                      fromfile="config.py",
                                      tofile="config.py",
                                      lineterm=""))
```

**For LLM workflows**:
LLMs don't need this tool - they generate patches directly from understanding the current file content and desired changes.

---

### 3. `inspect_patch` - REMOVED

**Rationale**: LLMs can parse unified diff format natively

- **What it did**: Analyzed patch content to extract affected files, hunks, and line counts
- **Why removed**:
  - LLMs can read and understand unified diff format directly
  - The information is human-readable from the patch itself
  - Adds 218 lines of code + 337 lines of tests for parsing that LLMs do naturally
  - No file system access required - just parsing text
  - Primarily useful for non-LLM programmatic validation

**Migration**:

```python
# v2.0 - Using inspect_patch
inspect_patch(patch=my_patch)
# Returns: {
#   "files": [{"file": "config.py", "hunks": 3, ...}],
#   "total_files": 1,
#   "total_hunks": 3,
#   ...
# }

# v3.0 - Parse manually if needed (or just read the patch)
# For LLMs: Just read the patch, you understand it natively
# For programmatic use: Use a library like unidiff

import re

def parse_patch_files(patch):
    """Simple parser for file names in unified diff."""
    files = []
    for line in patch.split('\n'):
        if line.startswith('---'):
            files.append(line.split()[1])
    return files

def count_hunks(patch):
    """Count hunks in a patch."""
    return patch.count('\n@@')
```

**For LLM workflows**:
LLMs don't need this tool - they can understand patches directly and extract relevant information through natural language processing.

---

## Core Tools (Retained)

### ✅ `apply_patch` - CORE TOOL
**Purpose**: Apply unified diff patches to files
**Why kept**: Primary tool, ~50% more token-efficient than Edit, atomic multi-hunk support, dry-run mode

### ✅ `validate_patch` - CORE TOOL
**Purpose**: Read-only validation before applying
**Why kept**: Safety check, preview changes, detect context mismatches before modification

### ✅ `backup_file` - CORE TOOL
**Purpose**: Create timestamped backups
**Why kept**: Safety mechanism, explicit backup control independent of patching

### ✅ `restore_backup` - CORE TOOL
**Purpose**: Restore files from backups
**Why kept**: Recovery mechanism, necessary complement to backup_file

---

## Workflow Patterns

The workflow patterns documented in WORKFLOWS.md remain valid and recommended. They are implemented as Python library functions in `src/patch_mcp/workflows.py` and `src/patch_mcp/recovery.py`, but are **not exposed as MCP tools**.

**Pattern implementations**:
- `apply_patches_with_revert()` - Sequential patches with rollback
- `apply_patch_with_backup()` - Safe experimentation
- `apply_patches_atomic()` - Multi-file atomic operations
- `apply_patch_progressive()` - Step-by-step validation

These can be used programmatically in Python code, but LLMs should compose these patterns using the 4 core tools.

---

## Benefits of v3.0 Simplification

### For LLMs
- **Simpler mental model**: 4 tools instead of 7
- **Clearer purpose**: Each tool has a distinct, necessary role
- **Better discoverability**: Less clutter in tool listings
- **Faster decisions**: Fewer tools to evaluate

### For Developers
- **Reduced maintenance**: 562 fewer lines of tool code (171+173+218)
- **Reduced test burden**: 946 fewer lines of unit tests (254+355+337)
- **Clearer API surface**: Only essential operations exposed
- **Better focus**: Core patch operations + backup/restore safety

### For the Project
- **Better SRP**: Each tool has a single, clear responsibility
- **Less duplication**: Removed tools that overlapped with core functionality
- **Easier documentation**: Fewer tools to explain and maintain
- **Faster onboarding**: Simpler API for new users

---

## Migration Checklist

If you're upgrading from v2.0 to v3.0:

- [ ] Search codebase for `revert_patch` calls → Replace with manual reversal or backup/restore
- [ ] Search codebase for `generate_patch` calls → Replace with git diff or difflib
- [ ] Search codebase for `inspect_patch` calls → Replace with manual parsing or remove (LLMs don't need it)
- [ ] Update MCP server configuration to use v3.0
- [ ] Test all patch operations with the 4 core tools
- [ ] Review WORKFLOWS.md for recommended patterns using core tools

---

## Feedback

If you have concerns about these deprecations or use cases we haven't considered, please:

1. Open an issue: https://github.com/shenning00/patch_mcp/issues
2. Start a discussion: https://github.com/shenning00/patch_mcp/discussions

We're committed to keeping the essential functionality while simplifying the API surface.

---

**Version**: 3.0.0
**Last Updated**: 2025-01-19
**Migration Support**: Open an issue if you need help upgrading
