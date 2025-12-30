"""Tests for DAST target resolution and allowlist enforcement."""

from src.models.project import Project
from src.orchestration.runners.zap_runner import ZapRunner
from src.orchestration.workflow import Workflow


def test_should_run_dast_when_targets_present() -> None:
    project = Project(
        url="https://github.com/example/repo",
        name="example",
        dast_targets=["http://127.0.0.1:3000/"],
    )

    assert Workflow._should_run_dast_scan(project) is True
    assert Workflow._resolve_dast_targets(project) == ["http://127.0.0.1:3000/"]


def test_should_skip_dast_without_targets_for_repo() -> None:
    project = Project(
        url="https://github.com/example/repo",
        name="example",
    )

    assert Workflow._resolve_dast_targets(project) == []
    assert Workflow._should_run_dast_scan(project) is False


def test_zap_allowlist_enforcement() -> None:
    hosts = ["127.0.0.1:3000", "localhost:3000"]
    ip_ranges: list[str] = []
    ports = ["3000"]

    assert ZapRunner._is_target_allowed(
        "http://127.0.0.1:3000/", hosts, ip_ranges, ports
    )
    assert not ZapRunner._is_target_allowed(
        "http://10.0.0.5:80/", hosts, ip_ranges, ports
    )
