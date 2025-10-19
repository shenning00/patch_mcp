# Patch MCP Server Usage Guidelines

## When to Use apply_patch Instead of Edit Tool

When modifying files in this project or any codebase, **prefer `apply_patch` over the `Edit` tool** because it provides significant advantages:

### Key Advantages

1. **Better Visibility**: Uses standard unified diff format (like `git diff`)
   - Changes are immediately clear
   - Easy to review what's being modified
   - Familiar format for developers

2. **Atomic Multi-Hunk Patches**: Apply multiple changes in ONE operation
   - All changes succeed together or all fail
   - No partial updates that leave files in inconsistent state
   - More reliable than separate Edit calls

3. **More Token Efficient**: Uses approximately 50% less tokens than Edit
   - Only sends changed lines + 3 lines of context
   - Edit requires full old_string and new_string
   - Matters for large files or multiple changes

4. **Safer with Dry-Run**: Test changes before applying
   - `dry_run: true` validates without modifying
   - Preview exactly what will change
   - Edit has no dry-run capability

## Quick Decision Guide

### Use apply_patch When:
- ✅ Making 2+ changes in one file → Use multi-hunk patch (atomic)
- ✅ Change needs to be reviewable → Standard diff format
- ✅ Working with large files → Token efficient
- ✅ Want to test first → dry_run mode available
- ✅ Applying code review feedback → Matches review format

### Use Edit When:
- Single simple string substitution
- Don't have file in conversation context yet
- Very quick one-line change

### Example Comparison

**Scenario**: Update 3 configuration values in config.py

**With Edit (3 separate calls)**:
```python
Edit("config.py", "timeout = 30", "timeout = 60")     # Call 1
Edit("config.py", "retries = 3", "retries = 5")       # Call 2
Edit("config.py", "debug = False", "debug = True")    # Call 3
```
❌ **Issues**:
- 3 file operations
- No atomicity (if call 2 fails, call 1 already applied)
- Partial updates possible
- Hard to see overall change

**With apply_patch (1 call)**:
```python
patch = """--- config.py
+++ config.py
@@ -10,3 +10,3 @@
-timeout = 30
+timeout = 60
@@ -25,3 +25,3 @@
-retries = 3
+retries = 5
@@ -50,3 +50,3 @@
-debug = False
+debug = True
"""
apply_patch("config.py", patch)
```
✅ **Benefits**:
- 1 atomic operation
- All 3 changes visible at once
- Clear diff format
- All changes succeed or all fail

## Best Practices

1. **Always use dry_run for critical files**:
   ```python
   # Test first
   result = apply_patch("critical.py", patch, dry_run=True)
   if result["success"]:
       # Now apply for real
       apply_patch("critical.py", patch)
   ```

2. **Create backups before major changes**:
   ```python
   backup_file("important.py")
   result = apply_patch("important.py", patch)
   if not result["success"]:
       restore_backup("important.py.backup.YYYYMMDD_HHMMSS")
   ```

3. **Validate patches before applying**:
   ```python
   validation = validate_patch("config.py", patch)
   if validation["can_apply"]:
       apply_patch("config.py", patch)
   ```

## Integration with This Codebase

This patch-mcp project is designed to make it easy for LLMs to apply code changes safely:

- **7 tools available**: apply_patch, validate_patch, revert_patch, generate_patch, inspect_patch, backup_file, restore_backup
- **Security built-in**: No symlinks, no binary files, size limits, disk space checks
- **Well-tested**: 286 tests with 84% coverage
- **Production-ready**: Used by Claude Desktop and other MCP clients

## Resources

- See `patch://guide/when-to-use` resource for decision guide
- Tool descriptions include "WHEN TO USE" guidance
- README.md has comparison table

---

**Remember**: Default to `apply_patch` for file modifications. Only use `Edit` for simple single substitutions where apply_patch would be overkill.
