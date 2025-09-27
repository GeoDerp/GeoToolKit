import json
import subprocess
from pathlib import Path

import pytest

# Define paths for test artifacts
TEST_DIR = Path(__file__).parent
PROJECTS_JSON_PATH = TEST_DIR / "test_projects.json"
REPORT_MD_PATH = TEST_DIR / "test_report.md"
DATABASE_PATH = TEST_DIR / "mock_db.tar.gz"

# Mock content for projects.json
# MOCK_PROJECTS_CONTENT will now be used as a template, and its 'url' fields
# will be dynamically set within the fixture using temporary paths.
MOCK_PROJECTS_CONTENT = {
    "projects": [
        {
            "url": "https://github.com/test/mock-repo-1"  # Placeholder, will be overwritten
        },
        {
            "url": "https://github.com/test/mock-repo-2"  # Placeholder, will be overwritten
        },
    ]
}

# No separate network-allowlist file is used; allowlist is embedded in projects.json


@pytest.fixture(scope="module")
def setup_test_environment(tmp_path_factory):  # Add tmp_path_factory as an argument
    # Create a temporary directory for mock repositories
    temp_repos_dir = tmp_path_factory.mktemp("mock_repos")

    mock_project_1_path = temp_repos_dir / "mock-repo-1"
    mock_project_2_path = temp_repos_dir / "mock-repo-2"

    # Create and initialize mock project directories
    for repo_path in [mock_project_1_path, mock_project_2_path]:
        repo_path.mkdir(exist_ok=True)
        (repo_path / "README.md").write_text("# Test Repo")
        if repo_path == mock_project_1_path:
            # Add a file with a simulated finding for mock-repo-1
            (repo_path / "config.py").write_text(
                "SECRET_KEY = 'supersecret'\nDATABASE_URL = 'sqlite:///test.db'"
            )

    # Create a local copy of MOCK_PROJECTS_CONTENT and update URLs
    # Embed network allowlist details and ports directly in projects.json
    local_projects_content = {
        "projects": [
            {
                "url": str(mock_project_1_path),
                "ports": ["8080"],
                "network_allow_hosts": ["localhost:8080", "127.0.0.1:8080"],
                "network_allow_ip_ranges": ["127.0.0.1/32"],
            },
            {
                "url": str(mock_project_2_path),
                "ports": ["8080"],
                "network_allow_hosts": ["localhost:8080", "127.0.0.1:8080"],
                "network_allow_ip_ranges": ["127.0.0.1/32"],
            },
        ]
    }

    with open(PROJECTS_JSON_PATH, "w") as f:
        json.dump(local_projects_content, f)  # Use the local content

    # Create mock database file (empty for now)
    DATABASE_PATH.touch()

    # No network-allowlist file needed; configuration is embedded above

    yield  # Run tests

    # Clean up after tests
    PROJECTS_JSON_PATH.unlink(missing_ok=True)
    REPORT_MD_PATH.unlink(missing_ok=True)
    DATABASE_PATH.unlink(missing_ok=True)
    # No allowlist file to clean up
    # tmp_path_factory automatically cleans up the temporary directory (temp_repos_dir)
    # and its contents, so explicit shutil.rmtree calls for mock_project_1_path
    # and mock_project_2_path are no longer needed.


def test_main_workflow_integration(setup_test_environment):
    # Construct the command to run src/main.py
    # Find the project root dynamically
    # From tests/integration/test_workflow.py, go up 2 levels to reach the project root (GeoToolKit)
    project_root = Path(__file__).parents[2]

    python_executable = project_root / ".venv" / "bin" / "python"
    main_script = project_root / "src" / "main.py"

    # Ensure the python executable for the virtual environment exists
    if not python_executable.exists():
        pytest.fail(
            f"Python executable for virtual environment not found at {python_executable}. "
            f"Please ensure the virtual environment is created and activated, or adjust the path."
        )

    # Ensure the main script exists
    if not main_script.exists():
        pytest.fail(
            f"Main script not found at {main_script}. Please check the project structure."
        )

    command = [
        str(python_executable),
        str(main_script),
        "--input",
        str(PROJECTS_JSON_PATH),
        "--output",
        str(REPORT_MD_PATH),
        "--database-path",
        str(DATABASE_PATH),
    ]

    print(f"Running command: {' '.join(command)}")

    try:
        result = subprocess.run(command, capture_output=True, text=True, check=True)
        print("STDOUT:", result.stdout)
        print("STDERR:", result.stderr)
    except subprocess.CalledProcessError as e:
        print(f"Command failed with exit code {e.returncode}")
        print("STDOUT:", e.stdout)
        print("STDERR:", e.stderr)
        pytest.fail(f"Integration test failed: {e}")

    # Assert that the report file was created
    assert REPORT_MD_PATH.exists()
    assert REPORT_MD_PATH.stat().st_size > 0

    # Basic content assertion (can be expanded)
    report_content = REPORT_MD_PATH.read_text()
    assert "# Scan Report for GeoToolKit" in report_content
    assert "**Total Projects Scanned**: 2" in report_content
    assert (
        "**Total Findings**: 1" in report_content
    )  # Expecting one finding from the mock repo
    assert "Project: mock-repo-1" in report_content
    assert "Project: mock-repo-2" in report_content
    # Note: Due to container runtime issues, the scanners don't actually find security issues
    # but the workflow still runs successfully and generates reports
