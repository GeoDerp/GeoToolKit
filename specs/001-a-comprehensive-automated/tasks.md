# Tasks: Automated Malicious Code Scanner

**Input**: Design documents from `/specs/001-a-comprehensive-automated/`
**Prerequisites**: plan.md (required), research.md, data-model.md, contracts/

## Phase 3.1: Setup
- [ ] T001 [P] Create project structure in `src/` and `tests/`
- [ ] T002 [P] Initialize Python project with `pyproject.toml` and install dependencies: `semgrep`, `trivy`, `osv-scanner`, `owasp-zap`
- [ ] T003 [P] Configure linting and formatting tools (`ruff`, `black`)

## Phase 3.2: Core Data Models
- [ ] T004 [P] Implement `Project` model in `src/models/project.py`
- [ ] T005 [P] Implement `Scan` model in `src/models/scan.py`
- [ ] T006 [P] Implement `Finding` model in `src/models/finding.py`

## Phase 3.3: Tool Orchestration
- [ ] T007 Implement main workflow script in `src/orchestration/workflow.py` to manage scan lifecycle
- [ ] T008 [P] Implement Semgrep runner in `src/orchestration/runners/semgrep_runner.py`
- [ ] T009 [P] Implement Trivy runner in `src/orchestration/runners/trivy_runner.py`
- [ ] T010 [P] Implement OSV-Scanner runner in `src/orchestration/runners/osv_runner.py`
- [ ] T011 [P] Implement OWASP ZAP runner in `src/orchestration/runners/zap_runner.py`
- [ ] T012 Implement results parser in `src/orchestration/parser.py` to standardize tool outputs

## Phase 3.4: Sandbox Environment
- [ ] T013 [P] Create Podman sandbox setup script in `scripts/sandbox/setup.sh`
- [ ] T014 [P] Create Podman sandbox teardown script in `scripts/sandbox/teardown.sh`
- [ ] T015 Implement network allow-list configuration in `src/orchestration/network.py`

## Phase 3.5: Reporting
- [ ] T016 Implement report generator in `src/reporting/generator.py`
- [ ] T017 Create Markdown report template in `src/reporting/templates/report.md`

## Phase 3.6: CLI
- [ ] T018 Implement CLI in `src/main.py` using `argparse` or `click`
- [ ] T019 Add `--input` argument for `projects.json`
- [ ] T020 Add `--output` argument for report file
- [ ] T021 Add `--database-path` argument for offline database
- [ ] T022 Add `--network-allowlist` argument

## Phase 3.7: Testing
- [ ] T023 [P] Unit tests for `Project` model in `tests/unit/test_project.py`
- [ ] T024 [P] Unit tests for `Scan` model in `tests/unit/test_scan.py`
- [ ] T025 [P] Unit tests for `Finding` model in `tests/unit/test_finding.py`
- [ ] T026 [P] Unit tests for results parser in `tests/unit/test_parser.py`
- [ ] T027 Integration test for main workflow in `tests/integration/test_workflow.py`

## Dependencies
- Models (T004-T006) before orchestration (T007-T012) and testing (T023-T025)
- Tool runners (T008-T011) block parser (T012)
- Parser (T012) blocks report generator (T016)
- Main workflow (T007) blocks integration test (T027)

## Parallel Example
```
# Launch T004-T006 and T008-T011 together:
Task: "Implement Project model in src/models/project.py"
Task: "Implement Scan model in src/models/scan.py"
Task: "Implement Finding model in src/models/finding.py"
Task: "Implement Semgrep runner in src/orchestration/runners/semgrep_runner.py"
Task: "Implement Trivy runner in src/orchestration/runners/trivy_runner.py"
Task: "Implement OSV-Scanner runner in src/orchestration/runners/osv_runner.py"
Task: "Implement OWASP ZAP runner in src/orchestration/runners/zap_runner.py"
```
