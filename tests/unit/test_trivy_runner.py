import subprocess
from unittest.mock import MagicMock, patch

from src.models.finding import Finding
from src.orchestration.runners.trivy_runner import TrivyRunner

# Mock Trivy JSON output for successful scan (vulnerability and misconfiguration)
MOCK_TRIVY_SUCCESS_OUTPUT = """
{
  "Results": [
    {
      "Target": "test_image:latest",
      "Vulnerabilities": [
        {
          "VulnerabilityID": "CVE-TEST-1",
          "PkgName": "test-pkg",
          "InstalledVersion": "1.0.0",
          "Severity": "HIGH",
          "Description": "A test vulnerability."
        }
      ],
      "Misconfigurations": [
        {
          "ID": "MISCONF-TEST-1",
          "Title": "Test Misconfiguration",
          "Description": "A test misconfiguration description.",
          "Severity": "CRITICAL",
          "Filepath": "test.yaml",
          "StartLine": 5
        }
      ]
    }
  ]
}
"""


def test_trivy_runner_success():
    with patch("subprocess.run") as mock_subprocess_run:
        mock_result = MagicMock()
        mock_result.stdout = MOCK_TRIVY_SUCCESS_OUTPUT
        mock_result.stderr = ""
        mock_result.returncode = 0
        mock_subprocess_run.return_value = mock_result

        findings = TrivyRunner.run_scan("/mock/target/path", scan_type="fs")

        mock_subprocess_run.assert_called_once_with(
            [
                "podman",
                "run",
                "--rm",
                "--network=none",
                "--security-opt=seccomp=/path/to/trivy-seccomp.json",
                "-v",
                "/mock/target/path:/src",
                "docker.io/aquasec/trivy",
                "trivy",
                "fs",
                "--format",
                "json",
                "/src",
            ],
            capture_output=True,
            text=True,
            check=True,
        )
        assert len(findings) == 2
        assert isinstance(findings[0], Finding)
        assert findings[0].tool == "Trivy"
        assert findings[0].severity == "High"
        assert "CVE-TEST-1" in findings[0].description

        assert isinstance(findings[1], Finding)
        assert findings[1].tool == "Trivy"
        assert findings[1].severity == "High"
        assert "MISCONF-TEST-1" in findings[1].description
        assert findings[1].filePath == "test.yaml"
        assert findings[1].lineNumber == 5


def test_trivy_runner_no_findings():
    with patch("subprocess.run") as mock_subprocess_run:
        mock_result = MagicMock()
        mock_result.stdout = '{"Results": []}'
        mock_result.stderr = ""
        mock_result.returncode = 0
        mock_subprocess_run.return_value = mock_result

        findings = TrivyRunner.run_scan("/mock/target/path")

        assert len(findings) == 0


def test_trivy_runner_command_not_found(capsys):
    with patch("subprocess.run") as mock_subprocess_run:
        mock_subprocess_run.side_effect = FileNotFoundError

        findings = TrivyRunner.run_scan("/mock/target/path")

        assert len(findings) == 0
        captured = capsys.readouterr()
        assert "Trivy command not found" in captured.out


def test_trivy_runner_called_process_error(capsys):
    with patch("subprocess.run") as mock_subprocess_run:
        mock_subprocess_run.side_effect = subprocess.CalledProcessError(
            returncode=1,
            cmd=["trivy", "fs", "--format", "json", "/mock/target/path"],
            stderr="Trivy error output",
        )

        findings = TrivyRunner.run_scan("/mock/target/path")

        assert len(findings) == 0
        captured = capsys.readouterr()
        assert "Error running Trivy" in captured.out
        assert "Trivy error output" in captured.out


def test_trivy_runner_json_decode_error(capsys):
    with patch("subprocess.run") as mock_subprocess_run:
        mock_result = MagicMock()
        mock_result.stdout = "invalid json"
        mock_result.stderr = ""
        mock_result.returncode = 0
        mock_subprocess_run.return_value = mock_result

        findings = TrivyRunner.run_scan("/mock/target/path")

        assert len(findings) == 0
        captured = capsys.readouterr()
        assert "Failed to decode Trivy JSON output" in captured.out
