#!/usr/bin/env python3
"""
FastMCP server for GeoToolKit

Provides endpoints to:
- Create projects.json with inline allowlist (hosts, ip ranges, ports)
- Run GeoToolKit scan and return report content

Docs: https://gofastmcp.com/llms.txt
"""

import json
import subprocess
from pathlib import Path
from typing import Any

# Optional MCP dependencies - graceful degradation if not available
try:
    from fastmcp import FastMCP, tool  # type: ignore

    MCP_AVAILABLE = True
except ImportError:  # pragma: no cover
    # Create fallback classes for when MCP dependencies are not available
    class FastMCP:  # type: ignore
        def __init__(self, **kwargs: Any):
            pass

        def run(self) -> None:
            print("⚠️ MCP dependencies not available. Install with: uv sync --extra mcp")

    def tool():  # type: ignore
        def decorator(func: Any) -> Any:
            return func

        return decorator

    MCP_AVAILABLE = False

APP_ROOT = Path(__file__).resolve().parents[1]

mcp = FastMCP(app_id="geotoolkit.mcp", app_name="GeoToolKit MCP", version="0.1.0")


def _write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
        json.dump(data, f, indent=2)


def _run_cmd(cmd: list[str], cwd: Path | None = None) -> tuple[int, str]:
    try:
        res = subprocess.run(
            cmd, cwd=str(cwd) if cwd else None, capture_output=True, text=True
        )
        out = (res.stdout or "") + ("\n" + res.stderr if res.stderr else "")
        return res.returncode, out
    except FileNotFoundError as e:
        return 127, str(e)


def _derive_allowlists(p: dict[str, Any]) -> tuple[list[str], list[str], list[str]]:
    allow_hosts: set[str] = set()
    allow_cidrs: set[str] = set()
    ports: list[str] = [str(x) for x in (p.get("ports") or [])]
    net_cfg = p.get("network_config") or {}
    if not ports:
        ports = [str(x) for x in (net_cfg.get("ports") or [])]
    protocol = str(net_cfg.get("protocol") or "").lower()
    default_port = "443" if protocol == "https" else "80"
    allowed = net_cfg.get("allowed_egress") or {}
    ext_hosts = allowed.get("external_hosts") or []
    if isinstance(ext_hosts, str):
        ext_hosts = [ext_hosts]
    for host in ext_hosts:
        host = str(host).strip()
        if not host:
            continue
        if ports:
            for prt in ports:
                allow_hosts.add(f"{host}:{str(prt).strip()}")
        else:
            allow_hosts.add(f"{host}:{default_port}")
    for key, val in allowed.items():
        if key == "external_hosts":
            continue
        values = val if isinstance(val, list) else ([val] if val else [])
        values = [str(v).strip() for v in values if str(v).strip()]
        if "/" in key:
            allow_cidrs.add(key)
        else:
            use_ports = values or (ports if ports else [default_port])
            for prt in use_ports:
                allow_hosts.add(f"{key}:{prt}")
    return sorted(allow_hosts), sorted(allow_cidrs), [str(x) for x in ports]


@tool()
def createProjects(
    projects: list[dict[str, Any]], outputPath: str = "projects.json"
) -> dict:
    """
    Create a projects.json file with allowlist fields in each project.
    Each project may include:
      - url (str), name (str), language (str), description (str)
      - network_allow_hosts (list[str])
      - network_allow_ip_ranges (list[str])
      - ports (list[str|int])
    Returns metadata and path.
    """
    normalized: list[dict[str, Any]] = []
    for p in projects:
        # Copy to avoid mutating caller input
        item = dict(p)
        if item.get("network_config"):
            hosts, cidrs, ports = _derive_allowlists(item)
            # Only set explicit fields if not already provided
            if not item.get("network_allow_hosts"):
                item["network_allow_hosts"] = hosts
            if not item.get("network_allow_ip_ranges"):
                item["network_allow_ip_ranges"] = cidrs
            if not item.get("ports") and ports:
                item["ports"] = ports
        normalized.append(item)

    data = {"projects": normalized}
    out_path = (APP_ROOT / outputPath).resolve()
    _write_json(out_path, data)
    return {
        "ok": True,
        "path": str(out_path),
        "project_count": len(normalized),
    }


@tool()
def runScan(
    inputPath: str = "projects.json",
    outputPath: str = "security-report.md",
    databasePath: str = "data/offline-db.tar.gz",
) -> dict:
    """
    Run GeoToolKit scan with given input and return the report content.
    Prefers 'uv run', falls back to 'python -m src.main'.
    Returns dict with exitCode, report, log.
    """
    input_abs = (APP_ROOT / inputPath).resolve()
    output_abs = (APP_ROOT / outputPath).resolve()
    db_abs = (APP_ROOT / databasePath).resolve()

    output_abs.parent.mkdir(parents=True, exist_ok=True)

    # Try uv run first
    cmd_uv = [
        "uv",
        "run",
        "python",
        "-m",
        "src.main",
        "--input",
        str(input_abs),
        "--output",
        str(output_abs),
        "--database-path",
        str(db_abs),
    ]
    rc, out = _run_cmd(cmd_uv, cwd=APP_ROOT)
    if rc == 0:
        report_text = (
            output_abs.read_text(encoding="utf-8") if output_abs.exists() else ""
        )
        return {"exitCode": rc, "report": report_text, "log": out}

    # Fallback to python
    cmd_py = [
        "python",
        "-m",
        "src.main",
        "--input",
        str(input_abs),
        "--output",
        str(output_abs),
        "--database-path",
        str(db_abs),
    ]
    rc, out = _run_cmd(cmd_py, cwd=APP_ROOT)
    report_text = output_abs.read_text(encoding="utf-8") if output_abs.exists() else ""
    return {"exitCode": rc, "report": report_text, "log": out}


@tool()
def normalizeProjects(
    inputPath: str = "projects.json", outputPath: str | None = None
) -> dict:
    """
    Read an existing projects.json, derive network_allow_hosts/network_allow_ip_ranges/ports from
    network_config, and write back. If outputPath is omitted, overwrites input.
    Returns a small preview of the allowlist for each project.
    """
    in_abs = (APP_ROOT / inputPath).resolve()
    out_abs = (APP_ROOT / (outputPath or inputPath)).resolve()
    try:
        payload = json.loads(in_abs.read_text())
    except Exception as e:
        return {"ok": False, "error": f"Failed to read {in_abs}: {e}"}

    projects = payload.get("projects") or []

    preview: list[dict[str, Any]] = []
    normalized: list[dict[str, Any]] = []
    for p in projects:
        item = dict(p)
        if item.get("network_config"):
            hosts, cidrs, ports = _derive_allowlists(item)
            item.setdefault("network_allow_hosts", hosts)
            item.setdefault("network_allow_ip_ranges", cidrs)
            if not item.get("ports") and ports:
                item["ports"] = ports
            preview.append(
                {
                    "name": item.get("name") or item.get("url"),
                    "hosts": hosts[:5],
                    "cidrs": cidrs[:5],
                    "ports": ports[:5],
                }
            )
        normalized.append(item)

    payload["projects"] = normalized
    try:
        _write_json(out_abs, payload)
    except Exception as e:
        return {"ok": False, "error": f"Failed to write {out_abs}: {e}"}
    return {"ok": True, "path": str(out_abs), "preview": preview}


if __name__ == "__main__":  # pragma: no cover
    # Start MCP server
    mcp.run()


def main() -> None:
    """Main entry point for MCP server CLI."""
    mcp.run()
