# Using Edit vs apply_patch: Decision Guide for LLMs

## Quick Decision Tree

```
Need to modify a file?
├─ File doesn't exist yet? → Use Write
├─ Rewriting >80% of file? → Use Edit or Write
└─ Making targeted changes? → Use apply_patch ✅
```

---

## Why apply_patch is Preferred

### 1. Better Change Visibility

**Edit Tool:**
```python
old_string = """def calculate(x, y):
    result = x + y
    return result"""

new_string = """def calculate(x, y):
    result = x * y  # Changed to multiplication
    return result"""
```
Hard to spot the difference at a glance.

**apply_patch Tool:**
```diff
--- math_utils.py
+++ math_utils.py
@@ -10,3 +10,3 @@
 def calculate(x, y):
-    result = x + y
+    result = x * y  # Changed to multiplication
     return result
```
Immediately clear: one line changed from `+` to `*`.

### 2. Multiple Changes in One Operation (Atomic)

**Edit Tool:** Requires 3 separate calls
```python
Edit(file, old_timeout, new_timeout)    # Call 1
Edit(file, old_retries, new_retries)    # Call 2
Edit(file, old_debug, new_debug)        # Call 3
```
❌ If call 2 fails, you have partial updates (file in inconsistent state)

**apply_patch Tool:** Single atomic operation
```diff
--- config.py
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
```
✅ All three changes succeed together or all fail (atomicity guaranteed)

### 3. Uses Less Context (More Token Efficient)

**Edit:** Must send full old_string and new_string (often 20-30 lines each)
**apply_patch:** Only sends changed lines + 3 lines context (~50% less tokens)

This matters for:
- Large files with small changes
- Multiple changes in one file
- Token budget optimization

---

## When to Use Each Tool

### Use apply_patch When:

✅ **Making targeted changes to existing files**
```diff
# Change one line
-API_KEY = "old_key"
+API_KEY = "new_key"
```

✅ **Multiple changes in one file**
```diff
# Three changes atomically
@@ -10 +10 @@ timeout = 30 → timeout = 60
@@ -25 +25 @@ retries = 3 → retries = 5
@@ -50 +50 @@ debug = False → debug = True
```

✅ **Changes that should be reviewable**
- Standard unified diff format (like git diff)
- Easy to review what changed
- Audit trail friendly

✅ **When you need atomicity**
- All changes must succeed together
- Can't risk partial updates

### Use Edit When:

✅ **Small, simple substitutions**
```python
Edit(file, old="version = 1.0", new="version = 2.0")
```

✅ **You don't have the file content in context**
- Edit can work without reading the file first
- apply_patch requires you to have read the file

✅ **Working with non-text formats where diff doesn't make sense**
- Binary files (though patches don't support these anyway)
- Files where line-based diff is confusing

### Use Write When:

✅ **Creating new files**
```python
Write(file_path, content)
```

✅ **Complete file rewrites (>80% changed)**
- Diff would be longer than just showing new content
- Essentially a new file

---

## Practical Examples

### Example 1: Single Line Change

**Task:** Update timeout from 30 to 60

**With Edit:**
```python
Edit(
    "config.py",
    old_string="timeout = 30",
    new_string="timeout = 60"
)
```

**With apply_patch:**
```python
patch = """--- config.py
+++ config.py
@@ -10,3 +10,3 @@
 # Connection settings
-timeout = 30
+timeout = 60
"""
apply_patch("config.py", patch)
```

**Verdict:** For single lines, both work equally well. apply_patch shows more context.

### Example 2: Multiple Related Changes

**Task:** Update 3 configuration values

**With Edit (3 separate calls):**
```python
Edit("config.py", "timeout = 30", "timeout = 60")
Edit("config.py", "retries = 3", "retries = 5")
Edit("config.py", "debug = False", "debug = True")
```
❌ 3 file operations, no atomicity

**With apply_patch (1 call):**
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
✅ 1 atomic operation, clear diff view

**Verdict:** apply_patch is superior for multiple changes.

### Example 3: Refactoring a Function

**Task:** Add input validation to a function

**With Edit:**
```python
Edit(
    file_path="utils.py",
    old_string="""def process_data(data):
    result = transform(data)
    return result""",
    new_string="""def process_data(data):
    # Validate input
    if not data:
        raise ValueError("Data cannot be empty")
    if not isinstance(data, dict):
        raise TypeError("Data must be a dictionary")

    result = transform(data)
    return result"""
)
```

**With apply_patch:**
```diff
--- utils.py
+++ utils.py
@@ -15,2 +15,7 @@
 def process_data(data):
+    # Validate input
+    if not data:
+        raise ValueError("Data cannot be empty")
+    if not isinstance(data, dict):
+        raise TypeError("Data must be a dictionary")
+
     result = transform(data)
```

**Verdict:** apply_patch shows exactly what was added (+) with clear context.

---

## Security Considerations (NEW in v1.1.0)

### Sensitive Content Detection

The `generate_patch` tool automatically scans for credentials:

```python
result = generate_patch("old_config.py", "new_config.py")

# Check for security warnings
if "security_warning" in result:
    print(f"⚠️  {result['security_warning']['recommendation']}")
    for finding in result['security_warning']['findings']:
        print(f"   - {finding}")
```

**Detected patterns:**
- Private keys (RSA, SSH, PGP)
- API keys and tokens
- Passwords
- AWS credentials
- JWT tokens
- Database connection strings

**Best practice:** Always check for and report security warnings before applying patches.

### Error Message Sanitization

Error messages from `validate_patch` and `apply_patch` are sanitized to prevent:
- Information disclosure (file paths reduced to filenames)
- Content leakage (long strings truncated to `[CONTENT]`)
- Prompt injection attacks

---

## Common Workflow Patterns

### Pattern 1: Safe Apply with Validation

```markdown
1. Read the file
2. Generate/create the patch
3. Validate it will apply cleanly (optional but recommended)
4. Apply with apply_patch
5. Check for security warnings
```

**Code:**
```python
# 1. Read file (already done in conversation)

# 2. Create patch
patch = """--- config.py
+++ config.py
@@ -10,3 +10,3 @@
-timeout = 30
+timeout = 60
"""

# 3. Validate (optional)
validation = validate_patch("config.py", patch)
if not validation["success"]:
    print(f"❌ Patch won't apply: {validation['reason']}")
    return

# 4. Apply
result = apply_patch("config.py", patch)

# 5. Check security (if using generate_patch)
if "security_warning" in result:
    print(f"⚠️  Security warning: {result['security_warning']}")
```

### Pattern 2: Multi-File Changes

For changes across multiple files, use apply_patch for each:

```python
# Atomic per file, sequential across files
apply_patch("config.py", config_patch)
apply_patch("utils.py", utils_patch)
apply_patch("handlers.py", handlers_patch)
```

Each file change is atomic. If handlers.py fails, config.py and utils.py are already updated.

### Pattern 3: Dry-Run Before Apply

```python
# Test first
result = apply_patch("critical.py", patch, dry_run=True)

if result["success"]:
    print(f"✓ Dry run passed - would change {result['changes']['lines_added']} lines")
    # Now apply for real
    apply_patch("critical.py", patch)
else:
    print(f"✗ Dry run failed: {result['error']}")
```

---

## How to Present Results to Users

### DON'T: Show Raw JSON

```json
{"success": true, "file_path": "/path/to/config.py", "applied": true, "changes": {"lines_added": 6, "lines_removed": 2, "hunks_applied": 3}}
```

### DO: Format for Readability

**Option 1: Concise**
```
✅ Applied patch to config.py
   • Added 6 lines
   • Removed 2 lines
   • 3 hunks applied
```

**Option 2: Detailed**
```
Updated config.py with 3 configuration changes:
   • timeout: 30 → 60 seconds
   • retries: 3 → 5 attempts
   • debug mode: enabled

Changes: +6 lines, -2 lines (3 hunks applied)
```

**For errors:**
```
❌ Failed to apply patch to config.py
   Error: context_mismatch

The file content doesn't match the expected context at line 10.
The file may have been modified since the patch was created.

Suggestion: Re-read the file and regenerate the patch.
```

---

## Limitations and Gotchas

### apply_patch Limitations

❌ **Must read file first in conversation**
- Tool will error if you haven't read the file
- Ensures you're working with current content

❌ **Context must match exactly**
- If file changed, patch won't apply
- Whitespace sensitive by default
- Solution: Re-read and regenerate patch

❌ **Not for binary files**
- Only text files supported
- Binary files are rejected

### Edit Limitations

❌ **No atomicity for multiple changes**
- Each Edit is separate
- Partial updates possible

❌ **Must find unique old_string**
- If old_string appears multiple times, Edit fails
- Need lots of context for uniqueness

❌ **Less reviewable**
- Not a standard format
- Harder to see what changed

---

## Decision Matrix

| Scenario | Tool | Reason |
|----------|------|--------|
| Update 1 config value | Either | Both work fine |
| Update 3 config values | **apply_patch** | Atomicity + efficiency |
| Add validation to function | **apply_patch** | Clear diff view |
| Create new file | **Write** | File doesn't exist |
| Rewrite entire file | **Write** or **Edit** | >80% changed |
| Change in multiple locations | **apply_patch** | Multi-hunk atomic |
| Quick variable rename | **Edit** | Simple substitution |
| Refactoring with review | **apply_patch** | Reviewable format |
| Adding security checks | **apply_patch** | See security warnings |

---

## Key Takeaways

1. **Default to apply_patch** for file modifications
   - Better visibility (unified diff format)
   - Atomic multi-hunk changes
   - More token efficient
   - Standard format (like git diff)

2. **Use Edit for simple cases**
   - Single simple substitutions
   - When you don't have file in context

3. **Use Write for new files**
   - File creation only

4. **Always format output for users**
   - Don't show raw JSON
   - Summarize changes clearly
   - Report security warnings

5. **Check security warnings** (v1.1.0+)
   - Scan for sensitive content
   - Review before sharing patches
   - Report findings to users

---

## Quick Reference Commands

```python
# Read first (required for apply_patch)
Read("config.py")

# Create and apply patch
patch = """--- config.py
+++ config.py
@@ -10,3 +10,3 @@
-old_value = 1
+new_value = 2
"""
result = apply_patch("config.py", patch)

# Validate before applying (optional)
validation = validate_patch("config.py", patch)

# Dry run (optional)
result = apply_patch("config.py", patch, dry_run=True)

# Generate patch from two files
result = generate_patch("old_config.py", "new_config.py")
if "security_warning" in result:
    # Handle security warning
    pass

# Revert a patch
result = revert_patch("config.py", original_patch)
```

---

**Version:** 1.1.0
**Last Updated:** 2025-10-19
**Related:** See `apply_patch_tool_use.md` for comprehensive guide
