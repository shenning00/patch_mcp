# apply_patch Tool Usage Guide

A comprehensive guide for using the `apply_patch` MCP tool effectively in this project.

## Overview

The `apply_patch` tool is the **preferred method** for making file modifications in this project. It provides better change visibility, atomicity, and auditability compared to traditional Edit tools.

---

## Core Principles

### 1. Always Read Before Patching

```markdown
✅ CORRECT:
1. Read the file
2. Generate the patch
3. Apply with apply_patch

❌ INCORRECT:
1. Apply patch without reading
```

The tool will error if you haven't read the file first in the conversation.

### 2. Prefer Patches Over Direct Edits

Use `apply_patch` instead of `Edit` or `Write` for all file modifications except:
- Creating brand new files (use `Write`)
- The change is so massive it's essentially a complete rewrite

**Why?**
- ✅ Shows exactly what changed (unified diff format)
- ✅ Standard format used in version control
- ✅ Reviewable and auditable
- ✅ Can handle any size change (1 line to entire file)

---

## Key Features

### Feature 1: Multi-Hunk Patches (Atomic Multiple Changes)

**Apply multiple changes to different parts of a file atomically in a single operation.**

#### Example: Update Multiple Configuration Values

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

**Result:** All three changes applied together or none are applied.

#### When to Use Multi-Hunk

- ✅ Multiple related changes in one file
- ✅ Refactoring that touches several functions
- ✅ Configuration updates across different sections
- ✅ When changes must be applied atomically

#### Benefits

1. **Atomicity**: All hunks succeed or all fail together
2. **Efficiency**: Single tool call instead of multiple
3. **Context Efficiency**: Only sends changed lines + minimal context
4. **Clarity**: Shows all related changes in one view

---

### Feature 2: Selective Revert (Manual Reversal)

**You can manually reverse specific changes without using revert_patch.**

#### Scenario: Revert Only Part of a Multi-Hunk Patch

**Original patch applied:**
```diff
--- config.py
+++ config.py
@@ -10,3 +10,3 @@
-timeout = 30
+timeout = 60
@@ -25,3 +25,3 @@
-retries = 3
+retries = 5
```

**Want to keep timeout=60 but revert retries back to 3:**

Create a new patch with only the change you want to reverse:
```diff
--- config.py
+++ config.py
@@ -25,3 +25,3 @@
-retries = 5
+retries = 3
```

Apply this selective revert patch:
```
apply_patch("config.py", selective_revert_patch)
```

#### Use Cases

- ✅ Partial rollback of changes
- ✅ Cherry-picking specific reverts
- ✅ Iterative refinement (apply, test, revert some, keep others)
- ✅ When you don't have the original patch

---

### Feature 3: Dry-Run Mode

**Test patches before applying them.**

```python
# Test without modifying the file
result = apply_patch("config.py", patch, dry_run=True)

# Check if it would succeed
if result["success"]:
    print(f"Would add {result['changes']['lines_added']} lines")
    # Now apply for real
    apply_patch("config.py", patch)
```

#### When to Use Dry-Run

- ✅ Uncertain if patch will apply cleanly
- ✅ Want to preview changes first
- ✅ Testing patch generation logic
- ✅ Automating patch workflows

---

## Output Formatting Best Practices

### Raw JSON Output (What the Tool Returns)

```json
{
  "success": true,
  "file_path": "/path/to/file.py",
  "applied": true,
  "changes": {
    "lines_added": 6,
    "lines_removed": 2,
    "hunks_applied": 3
  },
  "message": "Successfully applied patch to file.py"
}
```

### Formatted Response (What You Should Present)

**Option 1: Concise Summary**
```
✅ Applied patch to config.py
   • Added 6 lines
   • Removed 2 lines
   • 3 hunks applied
```

**Option 2: Detailed with Context**
```
🔧 apply_patch → config.py
   ├─ +6 lines added
   ├─ -2 lines removed
   └─ 3 hunks applied

✓ Successfully updated timeout, retries, and debug settings
```

**Option 3: Box Format**
```
┌─ apply_patch ─────────────────────────────┐
│ File: config.py                            │
│ Status: ✅ Success                         │
├────────────────────────────────────────────┤
│ Changes:                                   │
│   • Lines added:    +6                     │
│   • Lines removed:  -2                     │
│   • Hunks applied:   3                     │
└────────────────────────────────────────────┘
```

### Error Formatting

**Raw error:**
```json
{
  "success": false,
  "applied": false,
  "error": "Context mismatch at line 10...",
  "error_type": "context_mismatch"
}
```

**Formatted error:**
```
❌ Failed to apply patch to config.py
   Error: context_mismatch

   The file content doesn't match the expected context at line 10.
   The file may have been modified since the patch was created.
```

---

## Common Patterns

### Pattern 1: Safe Single File Update

```markdown
1. Read the file
2. Generate the patch
3. Apply with apply_patch
4. Format the output for the user
```

**Example:**
```
I'll update the timeout value in config.py:

[reads file]
[generates patch]
[calls apply_patch]

✅ Applied patch to config.py
   • Changed timeout from 30 to 60 seconds
   • 1 hunk applied
```

### Pattern 2: Multi-Hunk Atomic Update

```markdown
1. Read the file
2. Identify all changes needed
3. Create a single multi-hunk patch
4. Apply atomically
5. Report all changes made
```

**Example:**
```
I'll update three configuration values atomically:

[reads file]
[creates multi-hunk patch]
[calls apply_patch]

✅ Applied patch to config.py
   • Updated timeout: 30 → 60
   • Updated retries: 3 → 5
   • Updated debug: False → True
   • 3 hunks applied atomically
```

### Pattern 3: Test Then Apply

```markdown
1. Read the file
2. Generate the patch
3. Test with dry_run=True
4. If successful, apply for real
5. Report results
```

**Example:**
```
I'll test the patch first:

[calls apply_patch with dry_run=True]

✓ Dry run successful - patch can be applied cleanly
  Would add 5 lines and remove 3 lines

Applying the patch now:

[calls apply_patch with dry_run=False]

✅ Applied patch to utils.py
   • Added 5 lines
   • Removed 3 lines
   • 2 hunks applied
```

---

## Comparison: apply_patch vs Edit

### Context Size Efficiency

**Edit Tool:**
```python
Edit(
    file_path="config.py",
    old_string="""
    # Must include enough context for uniqueness
    # Often 10-30 lines to ensure unique match
    def get_config():
        timeout = 30
        retries = 3
        debug = False
        return Config(...)
    """,
    new_string="""
    # Same context repeated
    def get_config():
        timeout = 60
        retries = 5
        debug = True
        return Config(...)
    """
)
```
**Context sent:** ~20-30 lines (full old + new strings)

**apply_patch Tool:**
```python
apply_patch(
    file_path="config.py",
    patch="""--- config.py
+++ config.py
@@ -10,3 +10,3 @@
-timeout = 30
+timeout = 60
@@ -12,3 +12,3 @@
-retries = 3
+retries = 5
@@ -14,3 +14,3 @@
-debug = False
+debug = True
"""
)
```
**Context sent:** ~12 lines (only changes + 3 lines context each)

**Winner:** `apply_patch` uses ~40-60% less context for typical changes.

### Multiple Changes

**Edit Tool:**
- ❌ Requires separate calls for each change
- ❌ No atomicity - partial updates possible
- ❌ 3 file read/write cycles for 3 changes

**apply_patch Tool:**
- ✅ Single call with multi-hunk patch
- ✅ Atomic - all changes or none
- ✅ 1 file read/write cycle for 3 changes

**Winner:** `apply_patch` for multiple changes.

### Change Visibility

**Edit Tool:**
- Shows old_string and new_string
- Harder to scan differences
- Not standard format

**apply_patch Tool:**
- Shows unified diff format
- Easy to scan (-, +, context)
- Standard format used everywhere

**Winner:** `apply_patch` for visibility and review.

---

## Troubleshooting

### Problem: "Context mismatch" Error

**Cause:** File content doesn't match the patch expectations.

**Solutions:**
1. Re-read the file to get current content
2. Regenerate the patch from current state
3. Check if file was modified externally
4. Verify line endings and whitespace

### Problem: Patch Too Large

**Symptom:** Creating a patch with 100+ hunks seems unwieldy.

**Guidance:**
- This is fine! Patches can be large.
- Git regularly handles patches with 1000+ lines
- The size doesn't affect performance significantly
- Still better than multiple Edit calls

**When to consider Write instead:**
- Complete file rewrite (>80% of lines changed)
- Renaming/restructuring makes diff unreadable
- Brand new file

### Problem: Can't Undo Specific Changes

**Solution:** Use selective revert (manual reversal)
1. Create a patch with only the changes to reverse
2. Swap the - and + lines
3. Apply this selective revert patch

---

## Advanced Techniques

### Technique 1: Chaining Patches

Apply multiple patches sequentially to the same file:

```markdown
1. Apply patch A (adds feature)
2. Apply patch B (refines feature)
3. Apply patch C (adds tests)
```

Each patch builds on the previous state.

### Technique 2: Patch + Validate Pattern

```markdown
1. Read file
2. Generate patch
3. Use validate_patch to check applicability
4. If valid, apply with apply_patch
5. If invalid, regenerate or adjust
```

**When to use:**
- Critical files
- Automated workflows
- When file might have changed

### Technique 3: Backup Before Major Changes

```markdown
1. Read file
2. Create backup with backup_file
3. Apply patch with apply_patch
4. If failed, restore_backup
```

**When to use:**
- Large multi-hunk patches
- Production files
- Uncertain about patch correctness

---

## Quick Reference

### When to Use apply_patch

- ✅ All file modifications (except new files)
- ✅ Single line changes
- ✅ Multi-line changes
- ✅ Multiple changes in one file (multi-hunk)
- ✅ Changes needing atomicity
- ✅ Changes that should be reviewable

### When NOT to Use apply_patch

- ❌ Creating brand new files (use Write)
- ❌ Complete file rewrite (>80% changed) - consider Write
- ❌ You don't have/can't generate unified diff

### Remember

1. **Always read first** - Tool requires prior read
2. **Multi-hunk is powerful** - Use for multiple changes
3. **Format the output** - Make results readable for users
4. **Unified diff is standard** - Same format as git, diff, patch
5. **Context efficient** - Uses less token context than Edit
6. **Atomic operations** - All hunks succeed or all fail

---

## Integration with CLAUDE.md

Add this to your CLAUDE.md file in the "File Editing" or "Tools" section:

```markdown
## File Editing: apply_patch Tool

Use the `apply_patch` MCP tool for all file modifications.

See [apply_patch_tool_use.md](apply_patch_tool_use.md) for:
- Multi-hunk patches (atomic multiple changes)
- Selective revert techniques
- Output formatting guidelines
- Comparison with Edit tool
- Common patterns and examples
```

---

## Examples Library

### Example 1: Single Line Change

```diff
--- config.py
+++ config.py
@@ -10,3 +10,3 @@
 def get_timeout():
-    return 30
+    return 60
```

**Formatted output:**
```
✅ Updated timeout in config.py
   • Changed return value from 30 to 60
   • 1 line modified
```

### Example 2: Multi-Line Addition

```diff
--- utils.py
+++ utils.py
@@ -15,2 +15,6 @@
 def process_data(data):
+    # Validate input
+    if not data:
+        raise ValueError("Data cannot be empty")
+
     result = transform(data)
```

**Formatted output:**
```
✅ Added input validation to process_data()
   • Added 4 lines (validation check)
   • 1 hunk applied
```

### Example 3: Multi-Hunk Refactoring

```diff
--- handlers.py
+++ handlers.py
@@ -10,3 +10,3 @@
 def handle_request(req):
-    result = old_handler(req)
+    result = new_handler(req)
     return result
@@ -25,5 +25,8 @@
 def process(data):
-    # Old processing
-    return legacy_process(data)
+    # New processing with validation
+    validated = validate(data)
+    transformed = transform(validated)
+    return transformed
@@ -50,2 +53,3 @@
 def cleanup():
+    log.info("Cleanup started")
     remove_temp_files()
```

**Formatted output:**
```
✅ Refactored handlers.py
   • Updated handle_request to use new_handler
   • Modernized process() with validation
   • Added logging to cleanup()
   • 3 hunks applied atomically
```

---

**Version:** 1.0
**Last Updated:** 2025-01-18
**Author:** Generated from lessons learned in patch_mcp development
