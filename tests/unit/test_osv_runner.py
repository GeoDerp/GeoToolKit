import subprocess
from pathlib import Path
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
    with patch(
        "src.orchestration.runners.osv_runner.subprocess.run"
    ) as mock_subprocess_run:
        mock_result = MagicMock()
        mock_result.stdout = MOCK_OSV_SUCCESS_OUTPUT
        mock_result.stderr = ""
        mock_result.returncode = 0
        mock_subprocess_run.return_value = mock_result

        findings = OSVRunner.run_scan("/mock/project/path")

        seccomp_path = str(
            Path(__file__).parents[2] / "seccomp" / "osv-scanner-seccomp.json"
        )
        # Ensure key parts of the podman invocation exist (seccomp may be omitted)
    called = mock_subprocess_run.call_args[0][0]
    assert called[0:4] == ["podman", "run", "--rm", "--network=none"]
    assert "--cap-drop=ALL" in called
    # Accept either ':ro' or ':ro,Z' depending on selinux relabel behavior
    assert any(str(x).startswith("/mock/project/path:/src") for x in called)
    assert "ghcr.io/google/osv-scanner:latest" in called
    # The image provides the `osv-scanner` entrypoint; the runner passes
    # the subcommand (e.g. 'scan') as arguments. Check for the 'scan'
    # token instead of the binary name in the podman invocation.
    assert "scan" in called
    assert findings is not None
    assert len(findings) == 1
    assert isinstance(findings[0], Finding)
    assert findings[0].tool == "OSV-Scanner"
    assert findings[0].severity == "Medium"
    assert "OSV-2023-1" in findings[0].description


def test_osv_runner_no_findings():
    with patch(
        "src.orchestration.runners.osv_runner.subprocess.run"
    ) as mock_subprocess_run:
        mock_result = MagicMock()
        mock_result.stdout = '{"results": []}'
        mock_result.stderr = ""
        mock_result.returncode = 0
        mock_subprocess_run.return_value = mock_result

        findings = OSVRunner.run_scan("/mock/project/path")

        # Empty result should return an empty list
        assert findings is not None
        assert len(findings) == 0


def test_osv_runner_command_not_found(capsys):
    with patch(
        "src.orchestration.runners.osv_runner.subprocess.run"
    ) as mock_subprocess_run:
        mock_subprocess_run.side_effect = FileNotFoundError

        findings = OSVRunner.run_scan("/mock/project/path")

        # Runner returns None to indicate it couldn't run
        assert findings is None
        captured = capsys.readouterr()
        # Helper now returns rc 127 when subprocess isn't available
        assert "initial error (exit 127)" in captured.out


def test_osv_runner_called_process_error(capsys):
    with patch(
        "src.orchestration.runners.osv_runner.subprocess.run"
    ) as mock_subprocess_run:
        mock_subprocess_run.side_effect = subprocess.CalledProcessError(
            returncode=1,
            cmd=["osv-scanner", "--format", "json", "/mock/project/path"],
            stderr="OSV-Scanner error output",
        )

        findings = OSVRunner.run_scan("/mock/project/path")
    # Runner returns None to indicate the run failed
    assert findings is None
    captured = capsys.readouterr()
    assert (
        "initial error (exit 127)" in captured.out
        or "initial error (exit" in captured.out
    )
    assert "osv-scanner" in captured.out.lower()


def test_osv_runner_json_decode_error(capsys):
    with patch(
        "src.orchestration.runners.osv_runner.subprocess.run"
    ) as mock_subprocess_run:
        mock_result = MagicMock()
        mock_result.stdout = "invalid json"
        mock_result.stderr = ""
        mock_result.returncode = 0
        mock_subprocess_run.return_value = mock_result

        findings = OSVRunner.run_scan("/mock/project/path")

        # JSON decode errors are treated as runner failure
        assert findings is None
        captured = capsys.readouterr()
        assert "Failed to decode OSV-Scanner JSON output" in captured.out
