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

        # Validate key parts of the podman call rather than exact ordering which
        # can vary depending on helper behavior
        called = mock_subprocess_run.call_args[0][0]
        assert called[0:4] == ["podman", "run", "--rm", "--network=none"]
        assert "--cap-drop=ALL" in called
        # Accept either ':ro' or ':ro,Z' depending on GEOTOOLKIT_SELINUX_RELABEL
        assert any(x.startswith("/mock/target/path:/src:") for x in called)
        assert "docker.io/aquasec/trivy" in called
        # The Trivy image supplies `trivy` as the entrypoint; the runner
        # passes the subcommand (e.g. 'fs') as an argument. Do not require
        # the literal 'trivy' token to appear in the podman invocation.
        assert "fs" in called
        assert "--format" in called
        assert "json" in called
        assert "/src" in called

        assert isinstance(findings, list)
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

        assert findings is not None
        assert len(findings) == 0


def test_trivy_runner_command_not_found(capsys):
    with patch("subprocess.run") as mock_subprocess_run:
        mock_subprocess_run.side_effect = FileNotFoundError

        findings = TrivyRunner.run_scan("/mock/target/path")

        assert findings is None or len(findings) == 0
        captured = capsys.readouterr()
        assert "run exited with code 127" in captured.out


def test_trivy_runner_called_process_error(capsys):
    with patch("subprocess.run") as mock_subprocess_run:
        mock_subprocess_run.side_effect = subprocess.CalledProcessError(
            returncode=1,
            cmd=["trivy", "fs", "--format", "json", "/mock/target/path"],
            stderr="Trivy error output",
        )

        findings = TrivyRunner.run_scan("/mock/target/path")

    assert findings is None or len(findings) == 0
    captured = capsys.readouterr()
    assert "run exited with code" in captured.out
    # Helper may stringify the CalledProcessError (which does not include
    # the .stderr field) or include the stderr; accept either form.
    assert ("Trivy error output" in captured.out) or (
        "returned non-zero exit status" in captured.out
    )


def test_trivy_runner_json_decode_error(capsys):
    with patch("subprocess.run") as mock_subprocess_run:
        mock_result = MagicMock()
        mock_result.stdout = "invalid json"
        mock_result.stderr = ""
        mock_result.returncode = 0
        mock_subprocess_run.return_value = mock_result

        findings = TrivyRunner.run_scan("/mock/target/path")

        assert findings is not None
        assert len(findings) == 0
        captured = capsys.readouterr()
        assert "Failed to decode Trivy JSON output" in captured.out
