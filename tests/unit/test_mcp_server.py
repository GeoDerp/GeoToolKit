from pathlib import Path  # noqa: I001
from typing import Any, cast  # noqa: I001
from unittest.mock import patch  # noqa: I001

import mcp.server as mcp_server_module  # noqa: I001
mcp_server = cast(Any, mcp_server_module)


def test_mcp_create_and_normalize(tmp_path):
    payload = [
        {
            "url": "https://example.com/repo.git",
            "name": "example",
            "network_config": {
                "ports": ["3000"],
                "protocol": "http",
                "allowed_egress": {"localhost": ["3000"], "external_hosts": ["example.com"]},
            },
        }
    ]

    out_path = tmp_path / "projects.mcp.json"
    res = mcp_server.createProjects(payload, outputPath=str(out_path))
    assert res["ok"] is True
    assert Path(res["path"]).exists()

    norm = mcp_server.normalizeProjects(str(out_path))
    assert norm["ok"] is True
    assert "preview" in norm


def test_mcp_run_scan_smoke(tmp_path):
    # Create minimal projects.json
    proj = tmp_path / "projects.json"
    proj.write_text('{"projects": [{"url": ".", "name": "local"}] }')

    out = tmp_path / "out.md"
    db = tmp_path / "db.tar.gz"
    db.write_text("")

    # Patch APP_ROOT in server to tmp_path for isolation
    with patch("mcp.server.APP_ROOT", tmp_path):
        res = mcp_server.runScan(inputPath=str(proj), outputPath=str(out), databasePath=str(db))
        assert "exitCode" in res
        assert Path(out).exists()
