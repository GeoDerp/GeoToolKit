from unittest.mock import MagicMock, patch

from src.orchestration.runners.trivy_runner import TrivyRunner


def test_trivy_fallback_without_seccomp(monkeypatch):
    # Simulate first call raising CalledProcessError, second call returns valid JSON
    mock_result = MagicMock()
    mock_result.stdout = '{"Results": []}'
    mock_result.stderr = ""
    mock_result.returncode = 0

    called = {"count": 0}

    def fake_run(cmd, capture_output, text, check, timeout):
        called["count"] += 1
        if called["count"] == 1:
            raise subprocess.CalledProcessError(
                returncode=125, cmd=cmd, stderr="seccomp error"
            )
        return mock_result

    with patch("subprocess.run") as mock_run:
        import subprocess

        mock_run.side_effect = fake_run
        # Ensure seccomp path would be chosen so fallback code path is used
        monkeypatch.setenv("GEOTOOLKIT_USE_SECCOMP", "1")
        findings = TrivyRunner.run_scan("/mock/target/path")
        assert isinstance(findings, list)
        assert called["count"] == 2
