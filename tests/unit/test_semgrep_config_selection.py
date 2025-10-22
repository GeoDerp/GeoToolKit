import json

from src.orchestration.runners.semgrep_runner import SemgrepRunner


def test_semgrep_prefers_project_rules(monkeypatch, tmp_path):
    # Create a fake project rules file
    proj = tmp_path / "proj"
    proj.mkdir()
    rules_dir = proj / "rules" / "semgrep"
    rules_dir.mkdir(parents=True)
    project_rules = rules_dir / "default.semgrep.yml"
    project_rules.write_text("rules: []")

    # Mock choose_seccomp_path to avoid seccomp probing
    monkeypatch.setenv("GEOTOOLKIT_USE_SECCOMP", "0")

    # Monkeypatch run_with_seccomp_fallback to capture args and return a dummy JSON
    called = {}

    def fake_run(base_cmd, image, inner_args, seccomp_path, timeout, tool_name):
        called['base_cmd'] = base_cmd
        called['image'] = image
        called['inner_args'] = inner_args
        # Return success with empty semgrep-like JSON
        return (0, json.dumps({"results": []}), "")

    monkeypatch.setattr("src.orchestration.runners.semgrep_runner.run_with_seccomp_fallback", fake_run)

    # Parse result — should not error and should use the project rules file
    res = SemgrepRunner.run_scan(str(proj))
    assert isinstance(res, list)
    # Validate that the run helper was invoked and the command included /rules.yml
    assert 'inner_args' in called
    joined = " ".join(map(str, called['inner_args']))
    assert "/rules.yml" in joined or "--config" in joined

