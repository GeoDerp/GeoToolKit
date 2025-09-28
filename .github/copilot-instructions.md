# GitHub Copilot Instructions for GeoToolKit

## Project Overview
GeoToolKit is an automated security scanner for Git repositories that runs various open source security tools to scan packages and code. It is designed to be run in a secure, offline environment.

## Technology Stack
- **Language**: Python 3.11+
- **Framework**: FastAPI for web services (in the MCP server)
- **Package Management**: UV (a modern Python package installer)
- **Testing**: pytest
- **Linting**: ruff, mypy
- **Containerization**: Podman
- **Security Tools**: Semgrep, Trivy, OSV-Scanner, OWASP ZAP

## Project Structure
- `src/`: Main application code
  - `main.py`: CLI application entry point
  - `models/`: Data models and schemas
  - `orchestration/`: Scanning orchestration logic, including runners for each tool
  - `reporting/`: Report generation and templates
- `tests/`: Test suites
- `scripts/`: Utility scripts for validation and testing
- `mcp/`: Model Context Protocol server implementation
- `rules/`: Configuration rules for security tools like Semgrep
- `projects.json`: Configuration file for repositories to be scanned

## Coding Standards
- Follow PEP 8 Python style guidelines
- Use type hints for all functions and methods
- Write comprehensive docstrings for classes and functions
- Maintain test coverage for new features
- Use ruff for linting and formatting
- Use mypy for static type checking

## Security Focus
This project is security-focused, so when suggesting code:
- Prioritize secure coding practices
- Validate inputs and handle errors gracefully
- Use secure defaults
- Consider potential security vulnerabilities
- Follow OWASP guidelines where applicable
- Emphasize secure container practices with Podman

## Dependencies Management
- Use `pyproject.toml` for dependency management with `uv`
- Prefer well-maintained, secure packages
- Keep dependencies up to date
- Use optional dependency groups for dev/test tools

## Testing Guidelines
- Write unit tests for all new functionality
- Use pytest fixtures for test setup
- Mock external dependencies
- Test error conditions and edge cases
- Maintain good test coverage

## Docker/Container Guidelines
- Use Podman for running tools in secure, rootless containers
- Use multi-stage builds for efficiency if applicable
- Follow container security best practices (e.g., minimal base images, least privilege)
- Keep images lightweight and secure
- Utilize seccomp profiles for locking down container permissions
- Timeout and resource limits
  - Always set reasonable timeouts for dynamic testing (DAST) and for containerized runners to avoid infinite or excessively long scans.
  - Suggested defaults: per-target DAST = 300s, full scan = 1800s, per-runner = 600s.
  - Prefer configuring these in `projects.json` (example below) and ensure each runner reads and enforces them.

  Example `projects.json` timeouts entry:
  ```json
  "timeouts": {"dast_seconds": 300, "scan_seconds": 1800, "runner_seconds": 600}
  ```

  Implementation note: runners should translate these into container runtime time limits (or use subprocess timeouts) and enforce CPU/memory limits for safety.