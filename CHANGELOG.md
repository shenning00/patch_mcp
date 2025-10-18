# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [2.0.0] - 2025-01-18

### Added
- **Complete MCP Server Implementation**: 7 tools for comprehensive patch management
  - `apply_patch` - Apply patches with dry-run support and multi-hunk capability
  - `validate_patch` - Validate patches before application
  - `revert_patch` - Reverse previously applied patches
  - `generate_patch` - Generate patches from file comparisons
  - `inspect_patch` - Analyze patch content (supports multi-file patches)
  - `backup_file` - Create timestamped backups
  - `restore_backup` - Restore from backups with safety checks

- **4 Error Recovery Workflow Patterns**:
  - Try-Revert: Sequential patches with automatic rollback
  - Backup-Restore: Safe experimentation with automatic restore
  - Validate-All-Then-Apply: Atomic batch operations
  - Progressive Validation: Step-by-step validation with detailed reporting

- **Comprehensive Security Features**:
  - Symlink detection and rejection (security policy)
  - Binary file detection and rejection
  - File size limits (10MB maximum)
  - Disk space validation (100MB minimum + 110% of file size)
  - Path traversal protection
  - Permission checks
  - Atomic file operations

- **Multi-hunk Patch Support**: Apply multiple changes atomically to different parts of a file
- **Dry-run Mode**: Test patches without modifying files
- **Extensive Test Coverage**: 244 tests with 83% overall coverage
- **Comprehensive Documentation**:
  - Complete README with examples
  - WORKFLOWS.md documenting error recovery patterns
  - API documentation with clear return value semantics

### Features
- Python 3.10+ support
- Cross-platform compatibility (Linux, macOS, Windows)
- Type-safe implementation with Pydantic models
- Strict type checking with mypy
- Code quality enforcement (black, ruff)

### Testing
- 244 passing tests across all components:
  - 33 model tests (100% coverage)
  - 40 security tests (88% coverage)
  - 17 apply tests (87% coverage)
  - 17 validate tests (92% coverage)
  - 12 revert tests (91% coverage)
  - 11 generate tests (81% coverage)
  - 14 inspect tests (99% coverage)
  - 32 backup tests (70% coverage)
  - 20 server tests (86% coverage)
  - 13 API semantics tests
  - 21 workflow integration tests
  - 14 example workflow tests

### Documentation
- README.md with quick start, examples, and complete feature documentation
- WORKFLOWS.md documenting all 4 error recovery patterns
- API correctness documentation with return value semantics
- Inline code documentation with comprehensive docstrings

### Performance
- Atomic file operations using platform-optimized rename
- Efficient patch parsing and application
- Minimal memory footprint

### Security
- 10 distinct error types for precise error handling
- Comprehensive input validation
- Safe file operations with rollback capabilities
- No execution of arbitrary code

## [1.0.0] - 2025-01-17

### Added
- Initial implementation of core patch tools
- Basic security validation
- Test infrastructure

---

## Release Notes

### Version 2.0.0 (Production Ready)

This is the first production-ready release of the Patch MCP Server. All 5 development phases are complete:

- ✅ Phase 1: Foundation (Data models, security utilities, test infrastructure)
- ✅ Phase 2: Core Tools (apply, validate, revert, generate, inspect)
- ✅ Phase 3: Backup Tools (backup_file, restore_backup)
- ✅ Phase 4: MCP Server (Server implementation, tool registration)
- ✅ Phase 5: Error Recovery Patterns (4 workflow patterns with comprehensive tests)

The server is ready for use with MCP clients like Claude Desktop and provides a complete, production-grade solution for applying unified diff patches with comprehensive security and error recovery.

### Known Limitations

- Maximum file size: 10MB
- Binary files not supported
- Requires minimum 100MB free disk space
- UTF-8 encoding required for all files
- Symlinks are rejected (security policy)

### Future Enhancements

Potential areas for future development:
- Support for larger files (configurable limits)
- Binary file support (if safe to do so)
- Additional workflow patterns
- Performance optimizations for large patches
- Enhanced error messages with suggestions

---

[2.0.0]: https://github.com/shenning00/patch_mcp/releases/tag/v2.0.0
[1.0.0]: https://github.com/shenning00/patch_mcp/releases/tag/v1.0.0
