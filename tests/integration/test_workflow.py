import json
import subprocess
import sys
from pathlib import Path

import pytest


@pytest.fixture(scope="module")
def setup_test_environment(tmp_path_factory):
    # Create a temporary directory for the entire test module run
    test_dir = tmp_path_factory.mktemp("integration_test_env")
    
    # Define paths within the temp dir
    projects_json_path = test_dir / "test_projects.json"
    report_md_path = test_dir / "test_report.md"
    database_path = test_dir / "mock_db.tar.gz"
    
    # Create mock repos dir
    repos_dir = test_dir / "mock_repos"
    repos_dir.mkdir()

    mock_project_1_path = repos_dir / "mock-repo-1"
    mock_project_2_path = repos_dir / "mock-repo-2"

    # Create and initialize mock project directories
    for repo_path in [mock_project_1_path, mock_project_2_path]:
        repo_path.mkdir(exist_ok=True)
        (repo_path / "README.md").write_text("# Test Repo")
        if repo_path == mock_project_1_path:
            # Add a file with a simulated finding for mock-repo-1
            (repo_path / "config.py").write_text(
                "SECRET_KEY = 'supersecret'\nDATABASE_URL = 'sqlite:///test.db'"
            )

    # Create projects.json content
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

    with open(projects_json_path, "w") as f:
        json.dump(local_projects_content, f)

    # Create mock database file (empty for now)
    database_path.touch()

    # Return the paths needed for the test
    return {
        "projects_json": projects_json_path,
        "report_md": report_md_path,
        "database": database_path
    }


@pytest.mark.integration
@pytest.mark.slow
def test_main_workflow_integration(setup_test_environment):
    env = setup_test_environment
    
    # Construct the command to run src/main.py
    project_root = Path(__file__).parents[2]
    python_executable = sys.executable
    main_script = project_root / "src" / "main.py"

    if not main_script.exists():
        pytest.fail(f"Main script not found at {main_script}")

    command = [
        str(python_executable),
        str(main_script),
        "--input",
        str(env["projects_json"]),
        "--output",
        str(env["report_md"]),
        "--database-path",
        str(env["database"]),
    ]

    print(f"Running command: {' '.join(command)}")

    try:
        # Run the command
        result = subprocess.run(command, capture_output=True, text=True, check=True)
        print("STDOUT:", result.stdout)
        print("STDERR:", result.stderr)
    except subprocess.CalledProcessError as e:
        print(f"Command failed with exit code {e.returncode}")
        print("STDOUT:", e.stdout)
        print("STDERR:", e.stderr)
        pytest.fail(f"Integration test failed: {e}")

    # Assertions
    report_path = env["report_md"]
    assert report_path.exists()
    assert report_path.stat().st_size > 0

    report_content = report_path.read_text()
    assert "# Scan Report for GeoToolKit" in report_content
    assert "**Total Projects Scanned**: 2" in report_content
    assert "**Total Findings**: 1" in report_content
    assert "Project: mock-repo-1" in report_content
    assert "Project: mock-repo-2" in report_content
