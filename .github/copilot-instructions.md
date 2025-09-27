# GitHub Copilot Instructions for GeoToolKit

## Project Overview
GeoToolKit is an automated security scanner for Git repositories that runs various open source security tools to scan packages and code.

## Technology Stack
- **Language**: Python 3.11+
- **Framework**: FastAPI for web services
- **Package Management**: UV (modern Python package installer)
- **Testing**: pytest
- **Linting**: ruff, mypy
- **Containerization**: Docker with Podman support
- **Security Tools**: Semgrep, Trivy, and other security scanners

## Project Structure
- `src/`: Main application code
  - `main.py`: FastAPI application entry point
  - `models/`: Data models and schemas
  - `orchestration/`: Scanning orchestration logic
  - `reporting/`: Report generation and templates
- `tests/`: Test suites
- `scripts/`: Utility scripts for validation and testing
- `mcp/`: Model Context Protocol server implementation

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

## Dependencies Management
- Use pyproject.toml for dependency management
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
- Support both Docker and Podman
- Use multi-stage builds for efficiency
- Follow container security best practices
- Keep images lightweight and secure