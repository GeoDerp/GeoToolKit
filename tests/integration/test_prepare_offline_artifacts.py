import shutil
import subprocess
from pathlib import Path


def has_runtime() -> bool:
    return shutil.which("podman") is not None or shutil.which("docker") is not None


def test_prepare_script_creates_trivy_cache(tmp_path: Path):
    """Run prepare_offline_artifacts.sh and assert trivy cache tarball is produced.

    This is a slow integration test and will be skipped when no container runtime
    is available in the test environment.
    """
    if not has_runtime():
        print("skipping: no podman/docker available")
        return

    outdir = tmp_path / "offline-artifacts"
    outdir.mkdir()
    script = Path(__file__).resolve().parents[2] / "scripts" / "prepare_offline_artifacts.sh"
    assert script.exists(), f"prepare script not found at {script}"

    proc = subprocess.run([str(script), str(outdir)], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, timeout=600)
    print(proc.stdout)
    assert proc.returncode == 0

    trivy_tgz = outdir / "trivy-cache.tgz"
    assert trivy_tgz.exists() and trivy_tgz.stat().st_size > 0
