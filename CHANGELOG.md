# Changelog

All notable changes to DocsPort will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/).

## [2.0.0] - 2026-02-27

### Added
- Monaco-powered code editor with syntax highlighting and autocomplete
- AST-based code analysis (classes, functions, methods, dependencies)
- Mermaid.js flowcharts and D3.js interactive visualizations
- Secure Python code execution with sandbox and timeout protection
- Comment system with SQLite persistence
- Code metrics (cyclomatic complexity, maintainability index)
- Multilingual UI: English (default), German, Spanish
- Auto port discovery (8500-9500 range)
- `--port` CLI flag and `DOCSPORT_PORT` environment variable
- Execution timeout selector in UI (5s / 10s / 30s / 60s)
- Toast notifications (replaced blocking alert dialogs)
- Unsaved changes indicator in file selector
- Execution history display with click-to-load
- Comment filtering by file and type
- `pyproject.toml` for pip installation (`pip install .`)
- Pytest test suite (22 tests)
- GitHub Actions CI (Python 3.9 + 3.12, pytest + ruff)
- Dockerfile and docker-compose.yml
- Path traversal protection on all file endpoints
- CORS restricted to localhost origins only
- Code execution blacklist with dunder attribute blocking

### Security
- File access restricted to project directory (403 on path traversal)
- CORS locked to `localhost` / `127.0.0.1` only
- Execution sandbox blocks dangerous imports, builtins, and sandbox escape patterns
- Execution timeout capped at 60 seconds
- Removed `InteractiveCodeExecutor` (used unsandboxed `exec()`)
