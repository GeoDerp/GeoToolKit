# Tasks: Automated Malicious Code Scanner

**Input**: Design documents from `/specs/001-a-comprehensive-automated/`
**Prerequisites**: plan.md (required), research.md, data-model.md, contracts/

## Phase 3.1: Setup
- [x] T001 [P] Create the initial project structure in `src/` and `tests/` as defined in `plan.md`.
- [x] T002 [P] Initialize the Python project using `pyproject.toml` and add initial dependencies.
- [x] T003 [P] Configure linting and formatting tools (e.g., ruff, black).

## Phase 3.2: Core Implementation
- [x] T004 [P] Implement the `Project` data model in `src/models/project.py` based on `data-model.md`.
- [x] T005 [P] Implement the `Scan` data model in `src/models/scan.py` based on `data-model.md`.
- [x] T006 [P] Implement the `Finding` data model in `src/models/finding.py` based on `data-model.md`.

## Phase 3.3: Orchestration
- [x] T007 Implement the main workflow logic in `src/orchestration/workflow.py` to manage the overall scanning process.
- [x] T008 Implement the output parser in `src/orchestration/parser.py` to handle different tool outputs (JSON).
- [x] T009 [P] Implement the Semgrep runner in `src/orchestration/runners/semgrep_runner.py` to execute it within a Podman container.
- [x] T010 [P] Implement the Trivy runner in `src/orchestration/runners/trivy_runner.py` to execute it within a Podman container.
- [x] T011 [P] Implement the OSV-Scanner runner in `src/orchestration/runners/osv_runner.py` to execute it within a Podman container.
- [x] T012 [P] Implement the OWASP ZAP runner in `src/orchestration/runners/zap_runner.py` to execute it within a Podman container.
- [x] T013 Implement the main CLI entrypoint in `src/main.py` to handle command-line arguments as specified in `quickstart.md`.

## Phase 3.4: Reporting
- [x] T014 Implement the report generation logic in `src/reporting/report.py` to create the final Markdown report.
- [x] T015 Create the report template in `src/reporting/templates/report.md`.

## Phase 3.5: Tests (TDD)
- [x] T016 [P] Write a unit test for the `Project` model in `tests/unit/test_project.py`.
- [x] T017 [P] Write a unit test for the `Scan` model in `tests/unit/test_scan.py`.
- [x] T018 [P] Write a unit test for the `Finding` model in `tests/unit/test_finding.py`.
- [x] T019 [P] Write a unit test for the output parser in `tests/unit/test_parser.py`.
- [x] T020 Write an integration test for the main workflow in `tests/integration/test_workflow.py` that simulates the user journey from `quickstart.md`.

## Phase 3.6: Polish
- [ ] T021 [P] Add comprehensive docstrings and type hints to all new modules.
- [x] T022 [P] Create a `README.md` with detailed setup and usage instructions.
- [x] T023 [P] Write unit tests for each runner module to ensure correct container execution and error handling.
- [x] T024 Review and refine the seccomp profiles and network configurations for the Podman containers.

## Dependencies
- **Models first**: T004, T005, T006 must be completed before other implementation tasks.
- **Parser before runners**: T008 must be completed before T009-T012.
- **Core logic before CLI/Reporting**: T007-T012 must be completed before T013 and T014.
- **Tests can be developed alongside features**: T016-T020 can be worked on after their corresponding models/modules are created.

## Parallel Example
```
# These model and setup tasks can be run in parallel:
Task: "T001 [P] Create the initial project structure in src/ and tests/ as defined in plan.md."
Task: "T002 [P] Initialize the Python project using pyproject.toml and add initial dependencies."
Task: "T004 [P] Implement the Project data model in src/models/project.py based on data-model.md."
Task: "T005 [P] Implement the Scan data model in src/models/scan.py based on data-model.md."
Task: "T006 [P] Implement the Finding data model in src/models/finding.py based on data-model.md."

# Once the parser is done, all runners can be developed in parallel:
Task: "T009 [P] Implement the Semgrep runner in src/orchestration/runners/semgrep_runner.py"
Task: "T010 [P] Implement the Trivy runner in src/orchestration/runners/trivy_runner.py"
Task: "T011 [P] Implement the OSV-Scanner runner in src/orchestration/runners/osv_runner.py"
Task: "T012 [P] Implement the OWASP ZAP runner in src/orchestration/runners/zap_runner.py"
```