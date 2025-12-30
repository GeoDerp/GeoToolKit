import json
import os
import re
import subprocess
from pathlib import Path

from src.models.finding import Finding
from src.orchestration.parser import OutputParser
from src.orchestration.podman_helper import (
    build_podman_base,
    choose_seccomp_path,
    run_with_seccomp_fallback,
)


class TrivyRunner:
    """
    Runs Trivy scans and parses its output using secure podman containers.
    """

    @staticmethod
    def run_scan(
        target_path: str, scan_type: str = "fs", timeout: int | None = None
    ) -> list[Finding] | None:
        """Runs Trivy on the specified target path and scan type, returning a list of findings."""
        target_path_obj = Path(target_path)
        # Resolve a usable seccomp profile if one exists. Behavior can be
        # controlled via environment variables to support constrained hosts
        # (rootless Podman, CI, etc.). Priority order:
        # 1. TRIVY_SECCOMP_PATH (explicit path override)
        # 2. project-local seccomp/<file>
        # 3. packaged seccomp/ (only if GEOTOOLKIT_ALLOW_PACKAGED_SECCOMP=1)
        # If GEOTOOLKIT_USE_SECCOMP is set to 0/false/no then seccomp is disabled.
        # choose a seccomp path sensibly
        use_seccomp_env = os.environ.get("GEOTOOLKIT_USE_SECCOMP", "1").lower()
        chosen: Path | None = None
        if use_seccomp_env not in ("0", "false", "no"):
            chosen = choose_seccomp_path(target_path, "trivy")

        # Use conservative mount flags: avoid automatic SELinux relabel (:Z)
        # to prevent relabel permission failures on some hosts. The runner
        # will still respect GEOTOOLKIT_SELINUX_RELABEL=1 to opt-in.
        selinux_relabel = os.environ.get("GEOTOOLKIT_SELINUX_RELABEL", "0").lower() in (
            "1",
            "true",
            "yes",
        )
        mount_suffix = ":ro,Z" if selinux_relabel else ":ro"
        mount_spec = f"{target_path_obj}:/src{mount_suffix}"

        # If a host cache dir is provided, mount it into the container so
        # Trivy can use a pre-populated DB and avoid network downloads.
        trivy_cache_dir = os.environ.get("TRIVY_CACHE_DIR") or os.environ.get(
            "GEOTOOLKIT_TRIVY_CACHE_DIR"
        )

        trivy_image = os.environ.get("TRIVY_IMAGE", "docker.io/aquasec/trivy")

        # If offline mode requested but no cache dir is present, skip Trivy
        # entirely to avoid attempted DB downloads on isolated hosts.
        trivy_offline_raw = os.environ.get(
            "GEOTOOLKIT_TRIVY_OFFLINE"
        ) or os.environ.get("TRIVY_SKIP_UPDATE")
        trivy_offline = str(trivy_offline_raw).lower() in ("1", "true", "yes")
        if trivy_offline and (not trivy_cache_dir):
            print(
                "Trivy offline mode requested and no cache dir provided; skipping Trivy scan."
            )
            return []

        mounts = [mount_spec]
        if trivy_cache_dir:
            cache_mount_spec = f"{trivy_cache_dir}:/root/.cache/trivy:rw"
            mounts.append(cache_mount_spec)

        base_cmd = build_podman_base(mounts)
        # The Trivy image already has an entrypoint of `trivy`, so pass the
        # subcommand directly (e.g. `fs`). If a cache dir was mounted, pass
        # it as --cache-dir and, when offline is requested, also pass
        # --skip-db-update (Trivy may still require DB present for first run).
        inner_args = [scan_type, "--format", "json"]
        if trivy_cache_dir:
            inner_args += ["--cache-dir", "/root/.cache/trivy"]
            # Check if the provided cache directory contains Trivy data
            try:
                p = Path(trivy_cache_dir).expanduser()
                # Resolve relative paths to absolute when possible
                try:
                    p = p.resolve()
                except Exception:
                    pass
                non_empty = False
                # Prefer a strict check for Trivy DB files that indicate a usable cache
                try:
                    db_dir = p / "db"
                    trivy_db = db_dir / "trivy.db"
                    metadata = db_dir / "metadata.json"
                    if (
                        trivy_db.exists()
                        and trivy_db.is_file()
                        and trivy_db.stat().st_size > 1024
                        and metadata.exists()
                        and metadata.is_file()
                        and metadata.stat().st_size > 0
                    ):
                        non_empty = True
                        print(
                            f"Trivy cache present: DB={trivy_db.stat().st_size} bytes"
                        )
                    else:
                        # Fallback: any files present
                        for _ in p.rglob("*"):
                            non_empty = True
                            break
                except Exception:
                    non_empty = False
            except Exception:
                non_empty = False
            # If offline is explicitly requested but the cache dir is empty,
            # skip Trivy entirely to avoid attempted DB downloads on offline hosts.
            if (
                trivy_offline
                and str(trivy_offline).lower() in ("1", "true", "yes")
                and not non_empty
            ):
                print(
                    "Trivy offline requested but cache dir appears empty; skipping Trivy to avoid downloads."
                )
                return []
            # Do NOT add --skip-db-update here. Trivy has complex "first run" logic that
            # makes --skip-db-update fail even when a cache exists. Instead:
            # 1. Mount the cache (done above via mounts)
            # 2. Let Trivy try to use it
            # 3. If Trivy fails trying to download (offline env), catch the error and return []
            #
            # This approach allows Trivy to work when network is available (for updates)
            # while gracefully failing in offline environments.
        inner_args += ["/src"]

        try:
            # Run via secure helper which will attempt seccomp then fallback
            rc, out, err = run_with_seccomp_fallback(
                base_cmd=base_cmd,
                image=trivy_image,
                inner_args=inner_args,
                seccomp_path=chosen,
                timeout=timeout,
                tool_name="trivy",
            )

            if rc != 0:
                # If Trivy failed, attempt to detect CLI shape and retry with
                # alternate subcommands. Some Trivy images expose different
                # top-level commands (e.g. 'filesystem' instead of 'fs').
                print(f"Trivy run exited with code {rc}. See logs/ for details.")
                if out.strip():
                    print("stdout:", out)
                if err.strip():
                    print("stderr:", err)

                err_text = (err or "") + (out or "")
                # Use a forgiving regex to match unknown-command symptoms
                if re.search(r"unknown command.*trivy", err_text, flags=re.I):
                    # If offline mode explicitly requested and cache appears empty,
                    # avoid attempting fallback runs that will likely also fail.
                    if trivy_offline and (not trivy_cache_dir):
                        print(
                            "Trivy offline requested and cache empty; skipping fallback attempts."
                        )
                        return []

                    # Probe trivy --version (short timeout) to gather hints
                    probe_args = ["--version"]
                    rc2, out2, err2 = run_with_seccomp_fallback(
                        base_cmd=base_cmd,
                        image=trivy_image,
                        inner_args=probe_args,
                        seccomp_path=chosen,
                        timeout=10,
                        tool_name="trivy-probe",
                    )
                    if rc2 == 0:
                        print("Trivy probe succeeded:", out2.strip())
                    else:
                        print(
                            "Trivy probe failed:",
                            err2.strip() if err2 else out2.strip(),
                        )

                    # Try a set of alternate subcommands in order of likelihood
                    alternate_subs = ["filesystem", "fs", "image"]
                    for sub in alternate_subs:
                        print(f"Attempting Trivy fallback using subcommand: {sub}")
                        alt_args = [sub, "--format", "json", "/src"]
                        rc3, out3, err3 = run_with_seccomp_fallback(
                            base_cmd=base_cmd,
                            image=trivy_image,
                            inner_args=alt_args,
                            seccomp_path=chosen,
                            timeout=timeout,
                            tool_name=f"trivy-{sub}",
                        )
                        if rc3 == 0 and out3 and out3.strip():
                            print(f"Trivy fallback {sub} succeeded")
                            json_output = out3
                            return OutputParser.parse_trivy_json(json_output)
                        else:
                            print(f"Trivy fallback {sub} failed (rc={rc3})")

                # Preserve previous behavior: treat tool failures as empty findings
                return []

            json_output = out
            if not json_output.strip():
                print("Warning: Trivy returned empty output")
                return []

            return OutputParser.parse_trivy_json(json_output)
        except subprocess.TimeoutExpired:
            print("Error: Trivy scan timed out.")
            return []
        except subprocess.CalledProcessError as e:
            print(f"Error running Trivy: {e}")
            print(f"Stderr: {e.stderr}")
            # If we attempted to pass a seccomp profile but the container run
            # fails for any reason, retry once without the seccomp option. In
            # many constrained hosts seccomp or container attach/socket issues
            # cause failures that are resolved by removing the seccomp option.
            # Errors handled above; keep compatibility
            return []
        except FileNotFoundError:
            print("Trivy command not found")
            return []
        except json.JSONDecodeError as e:
            print(f"Failed to decode Trivy JSON output: {e}")
            return []
        except Exception as e:
            print(f"Unexpected error running Trivy: {e}")
            return []
