# Contributing to Patch MCP Server

Thank you for your interest in contributing to the Patch MCP Server! This document provides guidelines and instructions for contributing.

## Table of Contents

- [Code of Conduct](#code-of-conduct)
- [Getting Started](#getting-started)
- [Development Setup](#development-setup)
- [Running Tests](#running-tests)
- [Code Quality](#code-quality)
- [Submitting Changes](#submitting-changes)
- [Reporting Bugs](#reporting-bugs)
- [Feature Requests](#feature-requests)

## Code of Conduct

This project is committed to providing a welcoming and inclusive environment for all contributors. Please be respectful and constructive in all interactions.

## Getting Started

1. Fork the repository on GitHub
2. Clone your fork locally:
   ```bash
   git clone git@github.com:YOUR_USERNAME/patch_mcp.git
   cd patch_mcp
   ```
3. Add the upstream repository:
   ```bash
   git remote add upstream git@github.com:shenning00/patch_mcp.git
   ```

## Development Setup

1. **Create a virtual environment:**
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   ```

2. **Install in development mode:**
   ```bash
   pip install -e ".[dev]"
   ```

3. **Verify installation:**
   ```bash
   pytest tests/ -v
   ```

## Running Tests

### Run all tests
```bash
pytest tests/ -v
```

### Run with coverage
```bash
pytest tests/ --cov=src/patch_mcp --cov-report=term --cov-report=html
```

### Run specific test file
```bash
pytest tests/test_apply.py -v
```

### Run specific test
```bash
pytest tests/test_apply.py::TestApplyPatch::test_basic_patch -v
```

### View coverage report
```bash
# Open htmlcov/index.html in your browser
open htmlcov/index.html  # macOS
xdg-open htmlcov/index.html  # Linux
start htmlcov/index.html  # Windows
```

## Code Quality

This project maintains high code quality standards. Before submitting a PR, ensure your code passes all checks:

### Format code with Black
```bash
black src/patch_mcp tests/
```

### Lint with Ruff
```bash
ruff check src/patch_mcp tests/
```

### Type check with mypy
```bash
mypy src/patch_mcp --strict
```

### Run all checks at once
```bash
black src/patch_mcp tests/ && \
ruff check src/patch_mcp tests/ && \
mypy src/patch_mcp --strict && \
pytest tests/ --cov=src/patch_mcp
```

## Submitting Changes

1. **Create a new branch:**
   ```bash
   git checkout -b feature/your-feature-name
   # or
   git checkout -b fix/bug-description
   ```

2. **Make your changes:**
   - Write clear, concise commit messages
   - Follow existing code style and conventions
   - Add tests for new functionality
   - Update documentation as needed

3. **Ensure tests pass:**
   ```bash
   pytest tests/ -v
   ```

4. **Commit your changes:**
   ```bash
   git add .
   git commit -m "Add feature: description of changes"
   ```

5. **Push to your fork:**
   ```bash
   git push origin feature/your-feature-name
   ```

6. **Create a Pull Request:**
   - Go to the repository on GitHub
   - Click "New Pull Request"
   - Select your branch
   - Fill out the PR template with details about your changes
   - Link any related issues

### Pull Request Guidelines

- **Title:** Use a clear, descriptive title
- **Description:** Explain what changes you made and why
- **Tests:** Include tests for new functionality
- **Documentation:** Update README or docs if needed
- **Code Quality:** Ensure all checks pass (black, ruff, mypy, pytest)
- **Scope:** Keep PRs focused on a single feature or fix
- **Breaking Changes:** Clearly mark any breaking changes

## Reporting Bugs

When reporting bugs, please include:

1. **Description:** Clear description of the bug
2. **Steps to Reproduce:** Minimal steps to reproduce the issue
3. **Expected Behavior:** What you expected to happen
4. **Actual Behavior:** What actually happened
5. **Environment:**
   - OS (Linux, macOS, Windows)
   - Python version
   - Package version
6. **Error Messages:** Full error messages and tracebacks
7. **Additional Context:** Any other relevant information

**Create a bug report:** [New Issue](https://github.com/shenning00/patch_mcp/issues/new)

## Feature Requests

We welcome feature requests! When suggesting a new feature:

1. **Use Case:** Explain the problem you're trying to solve
2. **Proposed Solution:** Describe your proposed solution
3. **Alternatives:** Mention any alternative solutions you've considered
4. **Additional Context:** Any other relevant information

**Request a feature:** [New Issue](https://github.com/shenning00/patch_mcp/issues/new)

## Development Guidelines

### Code Style

- Follow PEP 8 style guidelines
- Use type hints for all functions
- Write docstrings for all public functions and classes
- Keep functions focused and single-purpose
- Maximum line length: 100 characters

### Testing

- Write tests for all new functionality
- Aim for >80% code coverage
- Test both success and failure cases
- Include edge cases in tests
- Use descriptive test names

### Documentation

- Update README.md for user-facing changes
- Update WORKFLOWS.md for new error recovery workflow patterns
- Add docstrings to all public APIs
- Include code examples where helpful
### Commit Messages

Follow conventional commit format:

```
type(scope): subject

body (optional)

footer (optional)
```

**Types:**
- `feat:` New feature
- `fix:` Bug fix
- `docs:` Documentation changes
- `test:` Test changes
- `refactor:` Code refactoring
- `chore:` Maintenance tasks

**Example:**
```
feat(apply): add support for multi-hunk patches

Added ability to apply multiple hunks atomically in a single patch.
This allows for more efficient file modifications.

Closes #123
```

## Questions?

If you have questions, feel free to:
- Open a [GitHub Discussion](https://github.com/shenning00/patch_mcp/discussions)
- Create an [Issue](https://github.com/shenning00/patch_mcp/issues)

Thank you for contributing! 🎉
