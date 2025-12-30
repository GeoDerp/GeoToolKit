#!/usr/bin/env python3
"""Preflight checks for GeoToolKit scans.

Checks runtime prerequisites (Podman, seccomp files, common images) and exits
with non-zero status when problems are found.
"""

import shutil
import subprocess
import sys
from pathlib import Path

REQUIRED_IMAGES = [
    "docker.io/aquasec/trivy",
    "docker.io/semgrep/semgrep",
    "docker.io/ossf/osv-scanner:latest",
]

PROJECT_ROOT = Path(__file__).parents[1]
SECCOMP_DIR = PROJECT_ROOT / "seccomp"


def check_podman():
    if not shutil.which("podman"):
        print("ERROR: podman is not installed or not on PATH")
        return False
    try:
        subprocess.run(["podman", "info"], check=True, capture_output=True)
    except subprocess.CalledProcessError as e:
        print("ERROR: podman info failed:")
        print(e.stderr.decode() if e.stderr else str(e))
        return False
    return True


def check_seccomp_files():
    missing = []
    for f in ("trivy-seccomp.json", "osv-scanner-seccomp.json"):
        p = SECCOMP_DIR / f
        if not p.exists():
            missing.append(str(p))
    if missing:
        print("WARNING: Missing seccomp files:")
        for m in missing:
            print(" - ", m)
        print(
            "You may set GEOTOOLKIT_USE_SECCOMP=0 to disable seccomp or install the seccomp files."
        )
        # Not fatal; continue
    else:
        print("Seccomp profiles present")
    return True


def check_images():
    ok = True
    for img in REQUIRED_IMAGES:
        try:
            subprocess.run(["podman", "image", "exists", img], check=True)
            print(f"Image present: {img}")
        except subprocess.CalledProcessError:
            print(f"Image missing (recommended): {img}")
            ok = False
    if not ok:
        print(
            "Tip: pre-pull images with 'podman pull <image>' to avoid runtime pulls and auth issues."
        )
    return ok


if __name__ == "__main__":
    ok = True
    ok = ok and check_podman()
    ok = ok and check_seccomp_files()
    check_images()
    if not ok:
        print("Preflight checks failed. Please fix errors and re-run.")
        sys.exit(2)
    print("Preflight checks passed (non-fatal image presence warnings may exist).")
    sys.exit(0)
