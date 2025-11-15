# Contributing to GeoToolKit

Thanks for your interest in contributing to GeoToolKit! This document explains the project's development workflow, testing guidelines, and how to prepare offline artifacts.

Development environment
- Linux host (recommended)
- Python 3.11+
- Podman (rootless mode recommended)
- `uv` for creating the virtual environment and installing dependencies

Quick start (fish shell)
```fish
# create venv and activate
uv venv
source .venv/bin/activate.fish
# install dependencies
uv sync
# run tests
python3 -m pytest tests/unit/
```

Coding standards
- Follow PEP 8 and use type hints
- Run `ruff` and `mypy` before opening a PR

Testing guidelines
- Add unit tests for new behavior and edge cases under `tests/unit/`
- Mock external calls (Podman, network) where appropriate
- Keep unit tests fast and deterministic

Offline artifacts
- To prepare Trivy and OSV artifacts on a networked machine, use `scripts/prepare_offline_artifacts.sh`.
- Upload the produced `trivy-cache.tgz` and optional `osv_offline.db` to your CI storage and set the env vars described in README.md before running scans.

Running a scan locally
- Example (fish-compatible):
```fish
set -x TRIVY_CACHE_DIR /workspace/trivy-cache
set -x GEOTOOLKIT_TRIVY_OFFLINE 1
python3 -m src.main --input projects.json --output report.md --database-path data/offline-db.tar.gz
```

Reporting issues and pull requests
- Open issues on GitHub for bugs and enhancements
- Create a topic branch for changes and open a PR with a clear description, tests, and changelog notes

Thank you for improving GeoToolKit!
