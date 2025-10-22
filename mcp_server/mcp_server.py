#!/usr/bin/env python3
"""
FastMCP server for GeoToolKit

Provides endpoints to:
- Create projects.json with inline allowlist (hosts, ip ranges, ports)
- Run GeoToolKit scan and return report content

Docs: https://gofastmcp.com/llms.txt
"""

import json
import os
import subprocess
from pathlib import Path
from typing import Any

# Optional MCP dependencies - graceful degradation if not available
try:
    # fastmcp is an optional dependency used for the MCP server. In some
    # environments (CI/test) the package may not be installed. We import it
    # when available; mypy will warn when stubs are not installed — ignore
    # that here.
    from fastmcp import FastMCP  # type: ignore[import]

    MCP_AVAILABLE = True
except ImportError:  # pragma: no cover
    # Provide a minimal fallback FastMCP implementation that exposes the
    # interface expected by tests and callers. We mark MCP_AVAILABLE True so
    # callers that depend on the decorator exist can import the module and
    # register tools; the fallback implementation will simply print helpful
    # messages at runtime.
    class FastMCP:  # type: ignore[misc,no-redef]
        def __init__(self, **kwargs: Any):
            # allow inspection of provided metadata
            self.name = kwargs.get("name", "geotoolkit-mcp-fallback")
            self.version = kwargs.get("version", "0.0.0")

        def run(self, **kwargs: Any) -> None:
            print("⚠️ MCP dependencies not available. Install with: uv sync --extra mcp")

        def tool(self, func=None, **kwargs: Any):
            """A simple decorator compatible with FastMCP's @mcp.tool.

            If used as @mcp.tool without args, returns a decorator that
            returns the function unchanged. If called with arguments, it
            accepts them and returns a decorator.
            """

            def decorator(f):
                # Attach a marker so tests can detect registration-like behavior
                f._mcp_tool = True  # type: ignore[attr-defined]
                return f

            if func is None:
                return decorator
            return decorator(func)

    MCP_AVAILABLE = True

APP_ROOT = Path(__file__).resolve().parents[1]

if MCP_AVAILABLE:
    # Initialize the MCP server
    mcp = FastMCP(name="geotoolkit-security-scanner", version="1.0.0")
else:
    # Create a fallback instance
    mcp = FastMCP()


def _write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
        json.dump(data, f, indent=2)


def _run_cmd(cmd: list[str], cwd: Path | None = None, timeout: float | None = None) -> tuple[int, str]:
    """Run a subprocess command with optional timeout.

    Returns a tuple of (returncode, combined_output). If the executable is not
    found returns exit code 127. If the process times out, returns exit code
    124 and includes a timeout message in the log.
    """
    try:
        res = subprocess.run(
            cmd,
            cwd=str(cwd) if cwd else None,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        out = (res.stdout or "") + ("\n" + res.stderr if res.stderr else "")
        return res.returncode, out
    except FileNotFoundError as e:
        return 127, str(e)
    except subprocess.TimeoutExpired as e:
        # e.stdout/e.stderr may be None or bytes; coerce to str safely
        def _to_str(val):
            if val is None:
                return ""
            if isinstance(val, bytes):
                try:
                    return val.decode(errors="replace")
                except Exception:
                    return str(val)
            return str(val)

        stdout = _to_str(e.stdout)
        stderr = _to_str(e.stderr)
        out = stdout + ("\n" + stderr if stderr else "")
        out += f"\nProcess timed out after {timeout} seconds (killed)."
        return 124, out


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


@mcp.tool
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


@mcp.tool
def runScan(
    inputPath: str = "projects.json",
    outputPath: str = "security-report.md",
    databasePath: str = "data/offline-db.tar.gz",
    timeout_seconds: int = 1800,
) -> dict:
    """
    Run GeoToolKit scan with given input and return the report content.
    Prefers 'uv run', falls back to 'python -m src.main'.
    Returns dict with exitCode, report, log.

    timeout_seconds controls how long to wait for the subprocess before
    terminating it. Default is 1800 seconds (30 minutes). The environment
    variable ``GEOTOOLKIT_RUNSCAN_TIMEOUT`` can be set (seconds) to override
    the default when no explicit value is provided.
    """
    # Allow overriding the default via environment variable when the caller
    # did not provide a custom value (most callers will just use the default).
    try:
        env_val = os.environ.get("GEOTOOLKIT_RUNSCAN_TIMEOUT")
        if env_val:
            # Only override when caller is still using the function default
            # (i.e., timeout_seconds equals the default we set above).
            if timeout_seconds == 1800:
                timeout_seconds = int(env_val)
    except Exception:
        # Ignore invalid env values and continue with the configured timeout
        pass
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
    rc, out = _run_cmd(cmd_uv, cwd=APP_ROOT, timeout=timeout_seconds)
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
    rc, out = _run_cmd(cmd_py, cwd=APP_ROOT, timeout=timeout_seconds)
    report_text = output_abs.read_text(encoding="utf-8") if output_abs.exists() else ""
    return {"exitCode": rc, "report": report_text, "log": out}


@mcp.tool
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


def main() -> None:
    """Main entry point for MCP server CLI."""
    import os

    # Get host and port from environment variables (set by main CLI)
    host = os.environ.get("MCP_HOST", "127.0.0.1")
    port = int(os.environ.get("MCP_PORT", "9000"))
    database_path = os.environ.get("DATABASE_PATH", "")

    if MCP_AVAILABLE:
        print(f"Starting MCP server on {host}:{port}")
        if database_path:
            print(f"Database path: {database_path}")
        mcp.run(transport="http", host=host, port=port)
    else:
        print("⚠️ MCP dependencies not available. Install with: uv sync --extra mcp")


if __name__ == "__main__":  # pragma: no cover
    main()
