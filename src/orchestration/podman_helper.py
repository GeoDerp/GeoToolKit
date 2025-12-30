import os
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, List, Optional


def _ensure_logs_dir() -> Path:
    p = Path.cwd() / "logs"
    p.mkdir(parents=True, exist_ok=True)
    return p


def _make_log_file(tool: str) -> Path:
    logs = _ensure_logs_dir()
    ts = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    return logs / f"{tool}-{ts}.log"


def choose_seccomp_path(
    target_path: Optional[str], packaged_name: str
) -> Optional[Path]:
    """Return a readable seccomp Path if available, otherwise None.

    Priority:
    1. TRIVY_SECCOMP_PATH or tool specific override env var
    2. project-local seccomp/<file>
    3. packaged seccomp (only if allowed)
    """
    # Generic environment override naming: <TOOLNAME>_SECCOMP_PATH or TOOL_SECCOMP_PATH
    env_override = os.environ.get(
        f"{packaged_name.upper()}_SECCOMP_PATH"
    ) or os.environ.get("TRIVY_SECCOMP_PATH")
    if env_override:
        p = Path(env_override)
        if p.exists() and os.access(str(p), os.R_OK):
            return p

    if target_path:
        try:
            proj_candidate = (
                Path(target_path) / "seccomp" / f"{packaged_name}-seccomp.json"
            )
            if proj_candidate.exists() and os.access(str(proj_candidate), os.R_OK):
                return proj_candidate
        except Exception:
            pass

    # Packaged candidate inside repository
    packaged_candidate = (
        Path(__file__).parents[2] / "seccomp" / f"{packaged_name}-seccomp.json"
    )
    env_allow = os.environ.get("GEOTOOLKIT_ALLOW_PACKAGED_SECCOMP")
    allow_packaged = (
        packaged_candidate.exists()
        if env_allow is None
        else env_allow.lower() in ("1", "true", "yes")
    )
    if (
        allow_packaged
        and packaged_candidate.exists()
        and os.access(str(packaged_candidate), os.R_OK)
    ):
        return packaged_candidate

    return None


def build_podman_base(mounts: Iterable[str]) -> List[str]:
    """Return a base podman command list with conservative, secure defaults."""
    cmd = [
        "podman",
        "run",
        "--rm",
        "--network=none",
        # Ensure containers run with the caller's UID inside the container so
        # bind-mounted files remain readable in rootless environments.
        "--userns=keep-id",
    ]
    # Drop capabilities by default and run unprivileged (do not add --privileged anywhere)
    cmd += ["--cap-drop=ALL"]
    # Mounts: expect strings like '/host/path:/container/path:ro'
    # If GEOTOOLKIT_SELINUX_RELABEL=1, append ':Z' to each mount to ensure
    # SELinux relabeling so containers can read the files on enforcing hosts.
    # Determine whether to request SELinux relabeling for mounts.
    # Priority:
    # 1. Explicit environment override GEOTOOLKIT_SELINUX_RELABEL
    # 2. Auto-detect SELinux enforcement on the host (if the env var is unset)
    env_val = os.environ.get("GEOTOOLKIT_SELINUX_RELABEL")
    if env_val is not None:
        selinux_relabel = env_val.lower() in ("1", "true", "yes")
    else:
        # Auto-detect: prefer /sys/fs/selinux/enforce (reads '1' when enforcing)
        selinux_relabel = False
        try:
            enforce_path = Path("/sys/fs/selinux/enforce")
            if enforce_path.exists():
                with enforce_path.open("r") as fh:
                    v = fh.read().strip()
                    selinux_relabel = v == "1"
            else:
                # Fall back to `getenforce` if available in PATH
                try:
                    out = subprocess.run(
                        ["getenforce"], capture_output=True, text=True, check=False
                    )
                    if out and out.stdout:
                        selinux_relabel = out.stdout.strip().lower() == "enforcing"
                except Exception:
                    selinux_relabel = False
        except Exception:
            selinux_relabel = False
    for m in mounts:
        mount_str = m
        # If the mount looks like '<host>:<container>[:opts]' and the host
        # part is a relative path (doesn't start with '/'), convert it to an
        # absolute path anchored at cwd. This avoids Podman interpreting the
        # left-hand side as a named volume and creating a named volume with
        # an invalid name when paths like 'data/offline-artifacts/osv_offline.db:/data/osv-offline-db:ro' are used.
        try:
            parts = mount_str.split(":", 2)
            # parts[0] is host path candidate
            if len(parts) >= 2:
                host_candidate = parts[0]
                # Only translate when host_candidate does not look like a URL or an absolute path
                if (not host_candidate.startswith("/")) and (
                    "://" not in host_candidate
                ):
                    abs_host = str((Path.cwd() / host_candidate).resolve())
                    # Reconstruct mount with same container path and any options
                    rest = ":".join(parts[1:])
                    mount_str = abs_host + ":" + rest
        except Exception:
            # On any parsing error, leave the mount string unchanged
            pass
        if selinux_relabel:
            # If the mount already includes a relabel marker (':Z' or ',Z'),
            # leave it as-is. Otherwise, append ',Z' if the mount already
            # contains a ':ro' or ':rw' option, or ':Z' when no option exists.
            if ",Z" in mount_str or ":Z" in mount_str:
                # already has relabel marker
                pass
            else:
                # Determine last option after the final ':' (if any)
                last = mount_str.rsplit(":", 1)[-1]
                if last in ("ro", "rw"):
                    mount_str = mount_str + ",Z"
                else:
                    mount_str = mount_str + ":Z"
        cmd += ["-v", mount_str]
    # Optional: run container process with the calling user's UID/GID.
    # Some tool images switch to a non-root user inside the container which
    # prevents reading bind-mounted files. Making the container process run
    # as the host UID (opt-in) helps with readability in rootless setups.
    run_as_host_user = os.environ.get("GEOTOOLKIT_RUN_AS_HOST_USER", "0").lower() in (
        "1",
        "true",
        "yes",
    )
    if run_as_host_user:
        try:
            uid = os.getuid()
            gid = os.getgid()
            cmd += ["--user", f"{uid}:{gid}"]
        except Exception:
            # If we cannot determine uid/gid, skip adding --user
            pass
    return cmd


def run_with_seccomp_fallback(
    base_cmd: List[str],
    image: str,
    inner_args: List[str],
    seccomp_path: Optional[Path],
    timeout: Optional[int],
    tool_name: str,
) -> tuple[int, str, str]:
    """Run the container, trying seccomp first (if provided), then retrying without seccomp on failure.

    Returns (exit_code, stdout, stderr) and writes a per-run log file.
    """
    log_file = _make_log_file(tool_name)
    # If no seccomp_path provided but the environment requests seccomp, try
    # to use a packaged default seccomp profile so tests and conservative
    # hosts still exercise the seccomp code path and fallback behavior.
    if not seccomp_path:
        use_seccomp_env = os.environ.get("GEOTOOLKIT_USE_SECCOMP", "1").lower()
        if use_seccomp_env not in ("0", "false", "no"):
            # Prefer a packaged candidate if available. If none exists,
            # leave seccomp_path as None so we don't supply an invalid
            # seccomp path (e.g. /dev/null) to Podman which causes
            # Podman to report a decoding error. This keeps the behavior
            # deterministic and avoids unnecessary fallback runs.
            packaged_candidate = Path(__file__).parents[2] / "seccomp" / "default.json"
            if packaged_candidate.exists() and os.access(
                str(packaged_candidate), os.R_OK
            ):
                seccomp_path = packaged_candidate
            else:
                seccomp_path = None

    def _run(cmd: List[str]) -> tuple[int, str, str]:
        try:
            # Explicitly pass check=False so callers/tests that expect a
            # 'check' parameter in mocked subprocess.run receive it.
            proc = subprocess.run(
                cmd, capture_output=True, text=True, timeout=timeout, check=False
            )
            rc = getattr(proc, "returncode", 0) or 0
            out = getattr(proc, "stdout", "") or ""
            err = getattr(proc, "stderr", "") or ""
            return rc, out, err
        except subprocess.TimeoutExpired as te:
            return -124, "", f"TimeoutExpired: {te}"
        except subprocess.CalledProcessError as e:
            # Return the CalledProcessError details so callers can inspect stderr
            try:
                stdout = e.stdout or ""
            except Exception:
                stdout = ""
            try:
                stderr = e.stderr or str(e)
            except Exception:
                stderr = str(e)
            return e.returncode, stdout, stderr
        except Exception as e:
            return 127, "", str(e)

    # Build command with seccomp if available
    if seccomp_path:
        cmd = (
            base_cmd
            + [f"--security-opt=seccomp={str(seccomp_path)}", image]
            + inner_args
        )
        rc, out, err = _run(cmd)
        with open(log_file, "w", encoding="utf-8") as fh:
            fh.write("# Command (with seccomp)\n")
            fh.write(" ".join(cmd) + "\n\n")
            fh.write("# stdout\n")
            fh.write(out + "\n\n")
            fh.write("# stderr\n")
            fh.write(err + "\n")

        # If the seccomp-run failed for any reason (non-zero rc), retry once without seccomp.
        if rc != 0:
            fallback_cmd = base_cmd + [image] + inner_args
            rc2, out2, err2 = _run(fallback_cmd)
            with open(log_file, "a", encoding="utf-8") as fh:
                fh.write("\n# Retried without seccomp\n")
                fh.write(" ".join(fallback_cmd) + "\n\n")
                fh.write("# stdout (fallback)\n")
                fh.write(out2 + "\n\n")
                fh.write("# stderr (fallback)\n")
                fh.write(err2 + "\n")
            return rc2, out2, err2

        return rc, out, err

    # No seccomp provided: run once
    cmd = base_cmd + [image] + inner_args
    rc, out, err = _run(cmd)
    with open(log_file, "w", encoding="utf-8") as fh:
        fh.write("# Command\n")
        fh.write(" ".join(cmd) + "\n\n")
        fh.write("# stdout\n")
        fh.write(out + "\n\n")
        fh.write("# stderr\n")
        fh.write(err + "\n")
    return rc, out, err
