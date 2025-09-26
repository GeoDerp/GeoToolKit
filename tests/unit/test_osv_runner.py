import subprocess
from unittest.mock import MagicMock, patch

from src.models.finding import Finding
from src.orchestration.runners.osv_runner import OSVRunner

# Mock OSV-Scanner JSON output for successful scan
MOCK_OSV_SUCCESS_OUTPUT = """
{
  "results": [
    {
      "source": {"path": "/mock/project/path/requirements.lock"},
      "packages": [
        {
          "package": {"name": "requests", "version": "2.25.1"},
          "vulnerabilities": [
            {
              "id": "OSV-2023-1",
              "summary": "Requests vulnerable to something.",
              "details": "Detailed explanation."
            }
          ]
        }
      ]
    }
  ]
}
"""


def test_osv_runner_success():
    with patch("subprocess.run") as mock_subprocess_run:
        mock_result = MagicMock()
        mock_result.stdout = MOCK_OSV_SUCCESS_OUTPUT
        mock_result.stderr = ""
        mock_result.returncode = 0
        mock_subprocess_run.return_value = mock_result

        findings = OSVRunner.run_scan("/mock/project/path")

        mock_subprocess_run.assert_called_once_with(
            [
                "podman",
                "run",
                "--rm",
                "--network=none",
                "--security-opt=seccomp=/path/to/osv-scanner-seccomp.json",
                "-v",
                "/mock/project/path:/src",
                "ghcr.io/ossf/osv-scanner:latest",
                "osv-scanner",
                "--format",
                "json",
                "/src",
            ],
            capture_output=True,
            text=True,
            check=True,
        )
        assert len(findings) == 1
        assert isinstance(findings[0], Finding)
        assert findings[0].tool == "OSV-Scanner"
        assert findings[0].severity == "Medium"
        assert "OSV-2023-1" in findings[0].description


def test_osv_runner_no_findings():
    with patch("subprocess.run") as mock_subprocess_run:
        mock_result = MagicMock()
        mock_result.stdout = '{"results": []}'
        mock_result.stderr = ""
        mock_result.returncode = 0
        mock_subprocess_run.return_value = mock_result

        findings = OSVRunner.run_scan("/mock/project/path")

        assert len(findings) == 0


def test_osv_runner_command_not_found(capsys):
    with patch("subprocess.run") as mock_subprocess_run:
        mock_subprocess_run.side_effect = FileNotFoundError

        findings = OSVRunner.run_scan("/mock/project/path")

        assert len(findings) == 0
        captured = capsys.readouterr()
        assert "OSV-Scanner command not found" in captured.out


def test_osv_runner_called_process_error(capsys):
    with patch("subprocess.run") as mock_subprocess_run:
        mock_subprocess_run.side_effect = subprocess.CalledProcessError(
            returncode=1,
            cmd=["osv-scanner", "--format", "json", "/mock/project/path"],
            stderr="OSV-Scanner error output",
        )

        findings = OSVRunner.run_scan("/mock/project/path")

        assert len(findings) == 0
        captured = capsys.readouterr()
        assert "Error running OSV-Scanner" in captured.out
        assert "OSV-Scanner error output" in captured.out


def test_osv_runner_json_decode_error(capsys):
    with patch("subprocess.run") as mock_subprocess_run:
        mock_result = MagicMock()
        mock_result.stdout = "invalid json"
        mock_result.stderr = ""
        mock_result.returncode = 0
        mock_subprocess_run.return_value = mock_result

        findings = OSVRunner.run_scan("/mock/project/path")

        assert len(findings) == 0
        captured = capsys.readouterr()
        assert "Failed to decode OSV-Scanner JSON output" in captured.out
