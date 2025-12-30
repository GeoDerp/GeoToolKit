import json
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from mcp_server import mcp_server
from src.main import main as cli_main
from src.models.finding import Finding

# Mock data
MOCK_PROJECTS = {
    "projects": [
        {
            "url": "https://github.com/example/repo",
            "name": "mock-repo",
            "language": "Python",
            "network_config": {
                "ports": ["8000"],
                "protocol": "http",
                "allowed_egress": {"external_hosts": ["api.example.com"]},
            },
        },
        {
            "url": "http://example-app.com",
            "name": "mock-webapp",
            "description": "Live web app for DAST",
            "network_allow_hosts": ["example-app.com:80"]
        }
    ]
}


@pytest.fixture
def mock_runners():
    with (
        patch(
            "src.orchestration.runners.semgrep_runner.SemgrepRunner.run_scan"
        ) as mock_semgrep,
        patch(
            "src.orchestration.runners.trivy_runner.TrivyRunner.run_scan"
        ) as mock_trivy,
        patch("src.orchestration.runners.osv_runner.OSVRunner.run_scan") as mock_osv,
        patch("src.orchestration.runners.zap_runner.ZapRunner.run_scan") as mock_zap,
    ):
        # Return empty list or mock findings
        mock_semgrep.return_value = [
            Finding(
                tool="Semgrep",
                severity="High",
                description="Mock finding",
                filePath="test.py",
                line=1,
            )
        ]
        mock_trivy.return_value = []
        mock_osv.return_value = []
        mock_zap.return_value = [
            Finding(
                tool="OWASP ZAP",
                severity="Medium",
                description="Mock DAST finding",
                filePath="target",
            )
        ]

        yield {
            "semgrep": mock_semgrep,
            "trivy": mock_trivy,
            "osv": mock_osv,
            "zap": mock_zap,
        }


@pytest.fixture
def mock_git_clone():
    with patch("src.orchestration.workflow.git.Repo.clone_from") as mock_clone:
        yield mock_clone


@pytest.fixture
def mock_subprocess_run():
    with patch("subprocess.run") as mock_run:
        mock_run.return_value.returncode = 0
        mock_run.return_value.stdout = "Mock output"
        yield mock_run


def test_mcp_runScan_mocks(tmp_path, mock_subprocess_run):
    """Test the runScan tool from MCP server with mocks."""

    # Setup paths
    projects_file = tmp_path / "projects.json"
    report_file = tmp_path / "report.md"
    db_file = tmp_path / "db.tar.gz"

    # Write mock projects.json
    with open(projects_file, "w") as f:
        json.dump(MOCK_PROJECTS, f)

    # Mock output file creation (simulating the scanner creating it)
    report_file.write_text("# Mock Security Report")

    # Call the tool
    with patch("mcp_server.mcp_server.APP_ROOT", tmp_path):
        result = mcp_server.runScan(
            inputPath=str(projects_file.name),
            outputPath=str(report_file.name),
            databasePath=str(db_file.name),
        )

    # Verify results
    assert result["exitCode"] == 0
    assert "# Mock Security Report" in result["report"]

    # Verify subprocess was called (uv run or python)
    assert mock_subprocess_run.called
    args = mock_subprocess_run.call_args[0][0]
    # Check that it tried to run the main module
    assert "src.main" in args or "src.main" in " ".join(args)


def test_cli_full_workflow_mocked(tmp_path, mock_runners, mock_git_clone):
    """Test the full CLI workflow with mocked Runners and Git."""

    # Setup inputs
    projects_file = tmp_path / "projects.json"
    report_file = tmp_path / "report.md"
    db_file = tmp_path / "db.tar.gz"
    db_file.touch()

    with open(projects_file, "w") as f:
        json.dump(MOCK_PROJECTS, f)

    # Mock project directory existing after clone
    mock_repo_dir = tmp_path / "mock-repo"
    mock_repo_dir.mkdir()
    (mock_repo_dir / "requirements.txt").touch()  # Make it look like Python

    # Patch the git clone to return a mock object that "clones" to our tmp dir
    mock_repo_obj = MagicMock()
    mock_repo_obj.working_dir = str(mock_repo_dir)
    mock_git_clone.return_value = mock_repo_obj

    # Run CLI
    test_args = [
        "geotoolkit",
        "--input",
        str(projects_file),
        "--output",
        str(report_file),
        "--database-path",
        str(db_file),
    ]

    with patch.object(sys, "argv", test_args):
        try:
            cli_main()
        except SystemExit as e:
            assert e.code == 0

    # Verify report generated
    assert report_file.exists()
    content = report_file.read_text()
    assert "Scan Report" in content
    assert "Mock finding" in content

    # Verify Runners were called
    assert mock_runners["semgrep"].called
    assert mock_runners["trivy"].called
    assert mock_runners["osv"].called
    
    # DAST should now be called because we added a web app target
    assert mock_runners["zap"].called
    
    # Let's verify SAST (Semgrep) was called at least.
    assert mock_runners["semgrep"].called

def test_mcp_detectNetworkConfig():
    """Test the detectNetworkConfig tool logic."""

    # Test Django detection
    res = mcp_server.detectNetworkConfig(
        "http://example.com", "my-django-app", "Python", "A django project"
    )
    assert res["ok"]
    assert "django" in res["detected_framework"]
    assert "8000" in res["network_config"]["ports"]

    # Test Node/Express detection
    res = mcp_server.detectNetworkConfig(
        "http://example.com", "express-api", "JavaScript", "Express server"
    )
    assert res["ok"]
    assert "express" in res["detected_framework"]
    assert "3000" in res["network_config"]["ports"]

    # Test Fallback
    res = mcp_server.detectNetworkConfig(
        "http://example.com", "unknown-app", "Rust", "Some app"
    )
    assert res["ok"]
    assert (
        "8080" in res["network_config"]["ports"]
    )  # Rust defaults to 8080 in our logic
