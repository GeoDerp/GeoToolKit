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

        # Simulate that the packaged default config is available.
        # Use a side-effect function so additional Path.exists calls
        # (from helpers) don't exhaust a fixed list and cause StopIteration.
        with patch("pathlib.Path.exists") as mock_exists:

            def exists_side_effect(*args, **kwargs):
                # args[0] is the Path instance being checked
                path_obj = args[0] if args else None
                s = str(path_obj)
                # If the call is checking the packaged default rules, return True
                if "default.semgrep.yml" in s:
                    return True
                return False

            mock_exists.side_effect = exists_side_effect

            findings = SemgrepRunner.run_scan("/mock/project/path")

            default_rules_path = str(
                Path(__file__).parents[2] / "rules" / "semgrep" / "default.semgrep.yml"
            )
            seccomp_path = str(
                Path(__file__).parents[2] / "seccomp" / "semgrep-seccomp.json"
            )
            # Ensure the podman invocation contains the expected key pieces
            called = mock_subprocess_run.call_args[0][0]
            joined = " ".join(map(str, called))
            assert joined.startswith("podman run --rm --network=none")
            assert "--cap-drop=ALL" in joined
            # mounts present: either project-local rules or packaged default
            assert "-v" in joined
            assert "/mock/project/path:/src:ro" in joined
            project_rules = "/mock/project/path/semgrep.yml:/rules.yml:ro"
            assert "/rules.yml:ro" in joined
            # Accept the packaged default, a project-local rules file, or
            # a temporary config file created during the run (mounted from /tmp).
            assert (
                (default_rules_path in joined)
                or (project_rules in joined)
                or ("/tmp/" in joined)
            )
            # image and semgrep args
            assert "docker.io/semgrep/semgrep" in joined
            assert "semgrep" in joined
            assert "--config" in joined
            assert "/rules.yml" in joined
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
    # Helper now returns rc 127 when subprocess isn't available
    assert "run exited with code 127" in captured.out


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
    # The runner surfaces the subprocess stderr when the helper returns non-zero
    assert "run exited with code" in captured.out
    # ensure semgrep was mentioned in the error output
    assert "semgrep" in captured.out.lower()


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
