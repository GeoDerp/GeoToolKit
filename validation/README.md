# Validation Artifacts

This folder holds configuration and outputs for end-to-end validation.

- configs/
  - enhanced-projects.json: Example projects with network_config for allowlist derivation
  - container-projects.json: Example DAST simulation targets
- logs/: runtime logs from validation runs
- reports/: generated reports from validation runs

Use scripts:
- python scripts/quick_validation.py
- python scripts/validation_executor.py
