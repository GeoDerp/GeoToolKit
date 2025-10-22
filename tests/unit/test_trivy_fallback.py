import json

from src.orchestration.runners.trivy_runner import TrivyRunner


class FakeCallSequence:
    def __init__(self):
        self.calls = []

    def __call__(self, base_cmd, image, inner_args, seccomp_path, timeout, tool_name):
        # Append call signature for assertions
        self.calls.append((tool_name, inner_args))
        # Behavior simulation:
        # 1st call: initial run -> unknown-command symptom
        if len(self.calls) == 1:
            return (1, "", "Error: unknown command 'trivy' for 'trivy'")
        # 2nd call: probe -> returns non-zero (simulate noisy images)
        if len(self.calls) == 2:
            return (0, "Trivy v1.2.3", "")
        # 3rd call: fallback filesystem -> succeed with JSON
        if len(self.calls) == 3:
            return (0, json.dumps([]), "")
        return (1, "", "failed")


def test_trivy_fallback(monkeypatch, tmp_path):
    seq = FakeCallSequence()
    monkeypatch.setattr("src.orchestration.runners.trivy_runner.run_with_seccomp_fallback", seq)
    # Mock parse to ensure it is called and returns []
    monkeypatch.setattr("src.orchestration.runners.trivy_runner.OutputParser.parse_trivy_json", lambda s: [])

    res = TrivyRunner.run_scan(str(tmp_path))
    assert isinstance(res, list)
    # verify the sequence of attempted tool names included trivy-probe and trivy-filesystem
    tool_names = [c[0] for c in seq.calls]
    assert any("trivy-probe" in t for t in tool_names)
    assert any("trivy-filesystem" in t for t in tool_names)
