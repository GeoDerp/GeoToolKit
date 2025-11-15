import json
import subprocess

from src.orchestration.runners import osv_runner


class DummyCompletedProcess:
    def __init__(self, stdout, returncode=0):
        self.stdout = stdout
        self.returncode = returncode


def test_osv_runner_uses_default_image(monkeypatch, tmp_path):
    # Create a dummy project path
    project_dir = tmp_path / "proj"
    project_dir.mkdir()

    called = {}

    def fake_run(cmd, capture_output, text, check, timeout):
        # Record the image used in the command
        called['cmd'] = cmd
        # Return a JSON that the parser can accept (empty results)
        return DummyCompletedProcess(stdout=json.dumps({'results': []}))

    monkeypatch.setattr(subprocess, 'run', fake_run)

    # Ensure no override env var is set
    monkeypatch.delenv('OSV_IMAGE', raising=False)

    res = osv_runner.OSVRunner.run_scan(str(project_dir), timeout=5)

    assert 'cmd' in called
    assert any('ghcr.io/google/osv-scanner' in str(x) for x in called['cmd'])
    assert isinstance(res, list)


def test_osv_runner_uses_alt_image_on_failure(monkeypatch, tmp_path):
    project_dir = tmp_path / "proj"
    project_dir.mkdir()

    calls = []

    def fake_run(cmd, capture_output, text, check, timeout):
        calls.append(cmd)
        # First two calls: simulate failures (seccomp run + fallback without seccomp)
        if len(calls) <= 2:
            raise subprocess.CalledProcessError(returncode=125, cmd=cmd, stderr='pull failed')
        # Third call: successful (should be the alt image)
        return DummyCompletedProcess(stdout=json.dumps({'results': []}))

    monkeypatch.setattr(subprocess, 'run', fake_run)

    # Remove explicit override
    monkeypatch.delenv('OSV_IMAGE', raising=False)

    res = osv_runner.OSVRunner.run_scan(str(project_dir), timeout=5)

    # We expect at least three calls: seccomp attempt, fallback without seccomp,
    # then the alt image invocation which should succeed.
    assert len(calls) >= 3
    # First call used the default ghcr image
    assert any('ghcr.io/google/osv-scanner' in str(c) for c in calls[0])
    # The fallback alt image should appear in subsequent calls (the third call)
    assert any('docker.io/google/osv-scanner' in ' '.join(map(str, c)) for c in calls[1:])
    assert isinstance(res, list)
