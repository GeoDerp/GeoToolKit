import json
from pathlib import Path
from unittest.mock import patch
from unittest.mock import patch as mock_patch

from src.main import main as cli_main


def write_projects(tmp_path: Path) -> Path:
    payload = {
        "projects": [
            {
                "url": str(tmp_path),
                "name": "local-test",
                "language": "Python",
                "network_config": {
                    "ports": ["8080"],
                    "protocol": "http",
                    "allowed_egress": {"localhost": ["8080"], "external_hosts": ["example.com"]},
                },
            }
        ]
    }
    proj = tmp_path / "projects.json"
    proj.write_text(json.dumps(payload))
    # create minimal file
    (tmp_path / "README.md").write_text("# dummy")
    return proj


def test_cli_runs_and_generates_report(tmp_path):
    proj = write_projects(tmp_path)
    out = tmp_path / "report.md"
    db = tmp_path / "offline-db.tar.gz"
    db.write_text("")

    argv = [
        "prog",
        "--input",
        str(proj),
        "--output",
        str(out),
        "--database-path",
        str(db),
    ]

    with patch("sys.argv", argv):
        # Avoid actually invoking containerized scanners
        with mock_patch("src.orchestration.workflow.Workflow._run_security_scans", return_value=[]):
            cli_main()

    assert out.exists()
    content = out.read_text()
    assert "Scan Report" in content or "Security" in content
