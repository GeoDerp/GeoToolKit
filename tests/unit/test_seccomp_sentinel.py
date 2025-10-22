import subprocess

from src.orchestration.podman_helper import build_podman_base, run_with_seccomp_fallback


def test_no_dev_null_sentinel(tmp_path, monkeypatch):
    """Ensure we don't pass /dev/null as the seccomp profile sentinel to Podman.

    The helper should only pass a seccomp path when it actually exists and is readable.
    If no packaged seccomp exists, it must not attempt to pass '/dev/null' which
    causes decoding errors in container runtimes.
    """

    base_cmd = build_podman_base([f"{tmp_path}/src:/src:ro"])

    # Prepare a fake subprocess.run that captures the command passed in
    called = {}

    def fake_run(cmd, capture_output, text, timeout, check):
        # record the exact command
        called['cmd'] = cmd
        # Return a dummy successful result
        class Proc:
            returncode = 0
            stdout = ""
            stderr = ""

        return Proc()

    monkeypatch.setattr(subprocess, 'run', fake_run)

    # Call the helper with seccomp_path=None to simulate missing packaged profiles
    rc, out, err = run_with_seccomp_fallback(
        base_cmd=base_cmd,
        image="docker.io/semgrep/semgrep",
        inner_args=["semgrep", "--version"],
        seccomp_path=None,
        timeout=5,
        tool_name="semgrep-test",
    )

    # Ensure subprocess.run was called and that '/dev/null' is not part of the command
    assert 'cmd' in called, "subprocess.run was not called"
    joined = " ".join(called['cmd'])
    assert '/dev/null' not in joined, f"Unexpected sentinel present in podman command: {joined}"
