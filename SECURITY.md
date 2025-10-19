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
- **Secure Temporary Files**: Uses `tempfile.mkstemp()` for secure temp file creation
- **No Code Execution**: Server does not execute arbitrary code
- **Input Validation**: All inputs validated using Pydantic models
- **Error Type Classification**: 10 distinct error types for precise error handling

### NEW: Information Disclosure Protection (v1.1.0)

**Sensitive Content Detection** (`utils.py:detect_sensitive_content`)
- Automatically scans patches for secrets and credentials
- Detects: private keys, API keys, tokens, passwords, AWS credentials, JWT tokens, database connection strings
- Returns security warnings when sensitive content is found
- Helps prevent accidental credential leakage

**Error Message Sanitization** (`utils.py:sanitize_error_message`)
- Sanitizes error messages to prevent information disclosure
- Truncates long content snippets (>50 characters) to `[CONTENT]`
- Removes absolute filesystem paths (keeps only filenames)
- Mitigates prompt injection attacks via file content reflection

Example security warning from `generate_patch`:
```json
{
  "success": true,
  "patch": "...",
  "security_warning": {
    "has_sensitive_content": true,
    "findings": ["API key pattern detected"],
    "recommendation": "SECURITY WARNING: Sensitive content detected..."
  }
}
```

### Security Constants

```python
MAX_FILE_SIZE = 10 * 1024 * 1024   # 10MB
MIN_FREE_SPACE = 100 * 1024 * 1024  # 100MB
BINARY_CHECK_BYTES = 8192           # First 8KB checked
NON_TEXT_THRESHOLD = 0.3            # 30% non-text = binary
```

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

| Date       | Auditor | Scope                | Status | Report |
|------------|---------|----------------------|--------|--------|
| 2025-10-19 | Internal| Security code review | ⚠️ Issues Found | See SECURITY_ISSUES.md |
| 2025-01-18 | Internal| Full codebase review | ✅ Pass | - |

**Latest Findings (2025-10-19)**:
- 2 CRITICAL vulnerabilities identified (data exfiltration, path traversal)
- 3 HIGH severity issues (info disclosure, prompt injection, no auth)
- 4 MEDIUM severity issues (resource limits, race conditions)
- See [SECURITY_ISSUES.md](./SECURITY_ISSUES.md) for full details and remediation

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

---

Thank you for helping keep Patch MCP Server secure! 🔒
