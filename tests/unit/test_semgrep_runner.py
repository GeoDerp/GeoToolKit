import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch

from src.models.finding import Finding
from src.orchestration.runners.semgrep_runner import SemgrepRunner

# Mock Semgrep JSON output for successful scan
MOCK_SEMGREP_SUCCESS_OUTPUT = """
{
  "results": [
    {
      "check_id": "test.rule",
      "path": "test.py",
      "start": {"line": 1, "col": 1},
      "end": {"line": 1, "col": 10},
      "extra": {
        "message": "Test finding message.",
        "severity": "ERROR"
      }
    }
  ]
}
"""


def test_semgrep_runner_success():
    with patch("subprocess.run") as mock_subprocess_run:
        mock_result = MagicMock()
        mock_result.stdout = MOCK_SEMGREP_SUCCESS_OUTPUT
        mock_result.stderr = ""
        mock_result.returncode = 0
        mock_subprocess_run.return_value = mock_result

        # Simulate that the default config is used
        with patch("pathlib.Path.exists") as mock_exists:
            # The first two checks for local configs fail, the third for default config succeeds
            mock_exists.side_effect = [False, False, False, False, True]

            findings = SemgrepRunner.run_scan("/mock/project/path")

            default_rules_path = str(
                Path(__file__).parents[2] / "rules" / "semgrep" / "default.semgrep.yml"
            )
            mock_subprocess_run.assert_called_once_with(
                [
                    "podman",
                    "run",
                    "--rm",
                    "--network=none",
                    "-v",
                    "/mock/project/path:/src:ro,Z",
                    "-v",
                    f"{default_rules_path}:/rules.yml:ro,Z",
                    "docker.io/semgrep/semgrep",
                    "semgrep",
                    "--config",
                    "/rules.yml",
                    "--json",
                    "/src",
                ],
                capture_output=True,
                text=True,
                check=True,
            )
        assert len(findings) == 1
        assert isinstance(findings[0], Finding)
        assert findings[0].tool == "Semgrep"
        assert findings[0].severity == "High"


def test_semgrep_runner_no_findings():
    with patch("subprocess.run") as mock_subprocess_run:
        mock_result = MagicMock()
        mock_result.stdout = '{"results": []}'
        mock_result.stderr = ""
        mock_result.returncode = 0
        mock_subprocess_run.return_value = mock_result

        findings = SemgrepRunner.run_scan("/mock/project/path")

        assert len(findings) == 0


def test_semgrep_runner_command_not_found(capsys):
    with patch("subprocess.run") as mock_subprocess_run:
        mock_subprocess_run.side_effect = FileNotFoundError

        findings = SemgrepRunner.run_scan("/mock/project/path")

        assert len(findings) == 0
        captured = capsys.readouterr()
        assert "Semgrep command not found" in captured.out


def test_semgrep_runner_called_process_error(capsys):
    with patch("subprocess.run") as mock_subprocess_run:
        mock_subprocess_run.side_effect = subprocess.CalledProcessError(
            returncode=1,
            cmd=["semgrep", "--json", "/mock/project/path"],
            stderr="Semgrep error output",
        )

        findings = SemgrepRunner.run_scan("/mock/project/path")

        assert len(findings) == 0
        captured = capsys.readouterr()
        assert "Error running Semgrep" in captured.out
        assert "Semgrep error output" in captured.out


def test_semgrep_runner_json_decode_error(capsys):
    with patch("subprocess.run") as mock_subprocess_run:
        mock_result = MagicMock()
        mock_result.stdout = "invalid json"
        mock_result.stderr = ""
        mock_result.returncode = 0
        mock_subprocess_run.return_value = mock_result

        findings = SemgrepRunner.run_scan("/mock/project/path")

        assert len(findings) == 0
        captured = capsys.readouterr()
        assert "Failed to decode Semgrep JSON output" in captured.out
