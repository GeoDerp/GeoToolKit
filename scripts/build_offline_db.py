#!/usr/bin/env python3
"""
Build an offline vulnerability database bundle (tar.gz) combining:
- NVD JSON feeds (recent, modified, and last N years)
- OSV export (via osv-scanner offline DB or public export if available)
- GitHub Security Advisories (GHSA) if GITHUB_TOKEN provided

Designed to work in air-gapped or restricted environments with a `--simulate` mode
that generates placeholders to validate pipeline wiring without network access.

Outputs: a tar.gz file with folder structure and a metadata.json manifest.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import shutil
import subprocess
import sys
import tarfile
import tempfile
import time
from collections.abc import Iterable
from pathlib import Path
from urllib import request

NVD_BASE = "https://nvd.nist.gov/feeds/json/cve/1.1"


def log(msg: str) -> None:
    print(f"[offline-db] {msg}")


def safe_mkdir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def download(url: str, dest: Path, retries: int = 3, backoff: float = 2.0) -> bool:
    for attempt in range(1, retries + 1):
        try:
            log(f"Downloading: {url}")
            with request.urlopen(url, timeout=60) as resp:
                data = resp.read()
            dest.write_bytes(data)
            log(f"Saved: {dest}")
            return True
        except Exception as e:
            log(f"Warn: attempt {attempt} failed for {url}: {e}")
            time.sleep(backoff * attempt)
    return False


def collect_nvd(out_dir: Path, years: Iterable[int], include_recent_modified: bool, simulate: bool) -> dict:
    nvd_dir = out_dir / "nvd"
    safe_mkdir(nvd_dir)
    results = {"success": [], "failed": []}

    feeds: list[str] = []
    if include_recent_modified:
        feeds.extend(["nvdcve-1.1-recent.json.gz", "nvdcve-1.1-modified.json.gz"])
    feeds.extend([f"nvdcve-1.1-{y}.json.gz" for y in years])

    if simulate:
        for name in feeds:
            (nvd_dir / name).write_text("{}\n")
            results["success"].append(name)
        return results

    for name in feeds:
        url = f"{NVD_BASE}/{name}"
        dest = nvd_dir / name
        if download(url, dest):
            results["success"].append(name)
        else:
            results["failed"].append(name)

    return results


def collect_osv(out_dir: Path, simulate: bool) -> dict:
    osv_dir = out_dir / "osv"
    safe_mkdir(osv_dir)
    result = {"method": None, "success": False, "note": None}

    if simulate:
        (osv_dir / "osv-offline-placeholder.json").write_text("{}\n")
        result.update({"method": "simulate", "success": True, "note": "placeholder created"})
        return result

    # Prefer osv-scanner offline DB capability if installed
    try:
        subprocess.run(["osv-scanner", "--version"], capture_output=True, check=True)
        cmd = [
            "osv-scanner",
            "--experimental-download-offline-databases",
            f"--download-directory={osv_dir}",
        ]
        log(f"Running: {' '.join(cmd)}")
        subprocess.run(cmd, check=True)
        result.update({"method": "osv-scanner", "success": True})
        return result
    except Exception as e:
        # Try public export (best-effort; may change or be large)
        log(f"osv-scanner not available or failed: {e}")

    # Fallback best-effort: attempt a known public export (may not always be available)
    # We deliberately keep this optional; if it fails, we still produce a bundle with NVD only.
    try:
        url = "https://osv-vulnerabilities.storage.googleapis.com/all.zip"
        dest = osv_dir / "osv-all.zip"
        if download(url, dest):
            result.update({"method": "public-export", "success": True})
        else:
            result.update({"method": "public-export", "success": False, "note": "download failed"})
    except Exception as e:  # pragma: no cover
        result.update({"method": "public-export", "success": False, "note": str(e)})

    return result


def collect_ghsa(out_dir: Path, simulate: bool) -> dict:
    ghsa_dir = out_dir / "ghsa"
    safe_mkdir(ghsa_dir)
    result = {"success": False, "note": None}

    if simulate:
        (ghsa_dir / "ghsa-placeholder.json").write_text("{}\n")
        result.update({"success": True, "note": "placeholder created"})
        return result

    token = os.environ.get("GITHUB_TOKEN")
    if not token:
        result.update({"success": False, "note": "GITHUB_TOKEN not set; skipping GHSA"})
        return result

    # Minimal paging for a sample; full export can be large. Documented as optional.
    try:
        from urllib import error as urlerror

        def gh_req(page: int) -> bytes:
            req = request.Request(
                f"https://api.github.com/advisories?per_page=100&page={page}",
                headers={
                    "Authorization": f"Bearer {token}",
                    "Accept": "application/vnd.github+json",
                },
            )
            with request.urlopen(req, timeout=60) as resp:
                return resp.read()

        combined = []
        for page in range(1, 6):  # fetch up to 500 advisories by default
            try:
                data = json.loads(gh_req(page).decode("utf-8"))
                if not data:
                    break
                combined.extend(data)
            except urlerror.HTTPError as he:
                result.update({"success": False, "note": f"HTTP {he.code}"})
                break
        (ghsa_dir / "advisories.json").write_text(json.dumps(combined))
        result.update({"success": True, "note": f"fetched {len(combined)} advisories (sample)"})
    except Exception as e:  # pragma: no cover
        result.update({"success": False, "note": str(e)})

    return result


def build_bundle(output: Path, workspace: Path, manifest: dict) -> None:
    # Write manifest inside the workspace before bundling
    (workspace / "metadata.json").write_text(json.dumps(manifest, indent=2))
    safe_mkdir(output.parent)
    with tarfile.open(output, "w:gz") as tar:
        # Add the contents of the workspace directory to the tarball at the root
        for item in workspace.iterdir():
            tar.add(item, arcname=item.name)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build an offline vulnerability database tarball")
    parser.add_argument("--output", default="data/offline-db.tar.gz", help="Output tar.gz path")
    parser.add_argument("--years", nargs="*", type=int, default=[], help="NVD years to include (e.g., 2021 2022 2023)")
    parser.add_argument("--recent-modified", action="store_true", default=True, help="Include NVD recent/modified feeds")
    parser.add_argument("--no-recent-modified", dest="recent_modified", action="store_false", help="Skip NVD recent/modified feeds")
    parser.add_argument("--no-osv", action="store_true", help="Skip OSV collection")
    parser.add_argument("--no-ghsa", action="store_true", help="Skip GHSA collection")
    parser.add_argument("--simulate", action="store_true", help="Create placeholders instead of network downloads")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    output = Path(args.output)
    now = dt.datetime.utcnow()

    # Default years: last 5 years
    if not args.years:
        current_year = now.year
        years = list(range(current_year, current_year - 5, -1))
    else:
        years = args.years

    temp_root = Path(tempfile.mkdtemp(prefix="offline-db-"))
    log(f"Workspace: {temp_root}")
    manifest = {
        "created": now.isoformat() + "Z",
        "nvd": None,
        "osv": None,
        "ghsa": None,
        "notes": [],
        "tool": "build_offline_db.py",
    }
    try:
        # NVD
        manifest["nvd"] = collect_nvd(temp_root, years, args.recent_modified, args.simulate)

        # OSV
        if not args.no_osv:
            manifest["osv"] = collect_osv(temp_root, args.simulate)
        else:
            manifest["notes"].append("OSV skipped by flag")

        # GHSA
        if not args.no_ghsa:
            manifest["ghsa"] = collect_ghsa(temp_root, args.simulate)
        else:
            manifest["notes"].append("GHSA skipped by flag")

        # Write manifest before tar for visibility in workspace as well
        (temp_root / "metadata.json").write_text(json.dumps(manifest, indent=2))

                # Create bundle
        build_bundle(output, temp_root, manifest)
        log(f"Bundle created at: {output}")
        return 0
    finally:
        # Keep the tmp dir if simulate (useful for inspection); otherwise cleanup
        if not args.simulate:
            try:
                shutil.rmtree(temp_root)
            except Exception:
                pass


if __name__ == "__main__":
    sys.exit(main())
