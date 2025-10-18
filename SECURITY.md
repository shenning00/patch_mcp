# Security Policy

## Supported Versions

We release security updates for the following versions:

| Version | Supported          |
| ------- | ------------------ |
| 2.0.x   | :white_check_mark: |
| < 2.0   | :x:                |

## Security Features

The Patch MCP Server implements comprehensive security measures:

### File Security
- **Symlink Protection**: Symlinks are automatically rejected (security policy)
- **Binary File Detection**: Binary files are detected and rejected
- **Path Traversal Protection**: Prevents directory escaping attacks
- **File Size Limits**: 10MB maximum file size to prevent resource exhaustion
- **Disk Space Validation**: Ensures sufficient disk space (100MB minimum + 110% file size)

### Operation Security
- **Permission Checks**: Read/write permissions validated before operations
- **Atomic Operations**: File replacements use atomic rename where possible
- **No Code Execution**: Server does not execute arbitrary code
- **Input Validation**: All inputs validated using Pydantic models
- **Error Type Classification**: 10 distinct error types for precise error handling

### Security Constants

```python
MAX_FILE_SIZE = 10 * 1024 * 1024   # 10MB
MIN_FREE_SPACE = 100 * 1024 * 1024  # 100MB
BINARY_CHECK_BYTES = 8192           # First 8KB checked
NON_TEXT_THRESHOLD = 0.3            # 30% non-text = binary
```

## Reporting a Vulnerability

We take security vulnerabilities seriously. If you discover a security vulnerability, please follow these steps:

### 1. **Do NOT** open a public issue

Security vulnerabilities should be reported privately to prevent exploitation.

### 2. Report via GitHub Security Advisories

1. Go to the [Security Advisories](https://github.com/shenning00/patch_mcp/security/advisories) page
2. Click "Report a vulnerability"
3. Fill out the form with:
   - Description of the vulnerability
   - Steps to reproduce
   - Potential impact
   - Suggested fix (if you have one)

### 3. Alternative: Email Report

If you prefer, you can email security reports directly:

**Email:** (Add your email or create security@patch-mcp.dev)

Please include:
- A clear description of the vulnerability
- Steps to reproduce the issue
- Affected versions
- Potential impact assessment
- Any proof-of-concept code (if applicable)
- Your contact information for follow-up

### 4. What to Expect

- **Acknowledgment**: We will acknowledge receipt within 48 hours
- **Assessment**: We will assess the vulnerability and determine its severity
- **Timeline**: We will provide an estimated timeline for a fix
- **Updates**: We will keep you informed of our progress
- **Credit**: We will credit you in the release notes (unless you prefer anonymity)

### Response Timeline

- **Critical vulnerabilities**: Patch within 7 days
- **High severity**: Patch within 14 days
- **Medium severity**: Patch within 30 days
- **Low severity**: Patch in next regular release

## Security Best Practices for Users

When using the Patch MCP Server:

### 1. Validate Input Sources
- Only apply patches from trusted sources
- Review patches before applying them
- Use `validate_patch` before `apply_patch`

### 2. Use Dry-Run Mode
```python
# Test patch without modifying files
result = apply_patch("file.py", patch, dry_run=True)
if result["success"]:
    # Now apply for real
    apply_patch("file.py", patch)
```

### 3. Use Backup Workflows
```python
from patch_mcp.workflows import apply_patch_with_backup

# Automatically creates backup and restores on failure
result = apply_patch_with_backup("critical.py", patch, keep_backup=True)
```

### 4. Limit File Access
- Run the server with minimal file system permissions
- Use path traversal protection in production
- Restrict access to sensitive directories

### 5. Monitor Operations
- Log all patch operations
- Monitor for unusual patterns
- Set up alerts for failed operations

### 6. Keep Updated
- Use the latest version for security patches
- Subscribe to release notifications
- Review CHANGELOG for security updates

## Known Security Limitations

### Intentional Restrictions

1. **Symlinks Rejected**: The server rejects all symlinks as a security policy
2. **Binary Files Rejected**: Binary files are not supported (detected and rejected)
3. **File Size Limit**: 10MB maximum to prevent resource exhaustion
4. **UTF-8 Only**: Only UTF-8 encoded text files are supported

### User Responsibility

The security of your system depends on:
- **Source Trust**: Only apply patches from trusted sources
- **File Permissions**: Set appropriate file system permissions
- **Input Validation**: Validate patch sources before application
- **Monitoring**: Monitor server operations and logs

## Security Audit History

| Date       | Auditor | Scope                | Status |
|------------|---------|----------------------|--------|
| 2025-01-18 | Internal| Full codebase review | ✅ Pass |

## Disclosure Policy

- We follow **coordinated disclosure**
- Security issues are fixed before public disclosure
- We credit security researchers (unless they prefer anonymity)
- We publish security advisories for all confirmed vulnerabilities

## Security Updates

Security updates will be:
- Released as patch versions (e.g., 2.0.1)
- Documented in CHANGELOG.md
- Announced via GitHub Security Advisories
- Tagged with `[SECURITY]` in release notes

## Contact

For security-related questions (non-vulnerabilities):
- Open a [Discussion](https://github.com/shenning00/patch_mcp/discussions)
- Create an [Issue](https://github.com/shenning00/patch_mcp/issues) (for non-sensitive questions)

**For vulnerability reports, use the private reporting methods above.**

---

Thank you for helping keep Patch MCP Server secure! 🔒
