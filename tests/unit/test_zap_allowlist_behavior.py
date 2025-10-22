import subprocess

from src.orchestration.runners.zap_runner import ZapRunner


def test_zap_allowlist_logs_and_proceeds(monkeypatch, capsys):
    # Mock podman run to succeed (simulate container start)
    def fake_run(cmd, capture_output=True, text=True, check=False, timeout=None):
        class P:
            returncode = 0
            stdout = ""
            stderr = ""

        return P()

    monkeypatch.setattr(subprocess, "run", fake_run)

    # Mock requests.get to simulate ZAP readiness and spider/ascan flows
    class DummyResp:
        def __init__(self, ok=True):
            self._ok = ok

        def raise_for_status(self):
            if not self._ok:
                raise Exception("http error")

        def json(self):
            return {"scan": "1"}

    import requests

    monkeypatch.setattr(requests, "get", lambda *a, **k: DummyResp())

    # Provide a network allowlist that matches the target hostname to ensure
    # the allowlist printing path is hit. The runner should still proceed.
    allowlist = ["localhost"]

    findings = ZapRunner.run_scan("http://localhost:1234", network_allowlist=allowlist, timeout=1)
    # The runner returns a list even when no alerts are found
    assert isinstance(findings, list)
    captured = capsys.readouterr()
    assert "matched allowlist" in captured.out or "allowing network access" in captured.out
