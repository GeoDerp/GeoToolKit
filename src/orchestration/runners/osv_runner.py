import json
import os
import subprocess
from pathlib import Path

from src.models.finding import Finding
from src.orchestration.parser import OutputParser
from src.orchestration.podman_helper import (
    build_podman_base,
    choose_seccomp_path,
    run_with_seccomp_fallback,
)


class OSVRunner:
    """
    Runs OSV-Scanner and parses its output using secure podman containers.
    """

    @staticmethod
    def run_scan(project_path: str, timeout: int | None = None) -> list[Finding] | None:
        """Runs OSV-Scanner on the specified project path and returns a list of findings."""
        project_path_obj = Path(project_path)
        use_seccomp_env = os.environ.get("GEOTOOLKIT_USE_SECCOMP", "1").lower()
        chosen: Path | None = None
        if use_seccomp_env not in ("0", "false", "no"):
            chosen = choose_seccomp_path(project_path, "osv-scanner")

        # Choose an OSV scanner image. Allow environment override, then try a
        # small list of known locations/maintainers as fallbacks. Historically
        # the image has moved between registries/owners so try multiple.
        # Default OSV image; unit tests (and many environments) assume the
        # google/ghcr image is the default. Allow explicit override via
        # OSV_IMAGE or OSV_ALT_IMAGE (legacy).
        osv_image = (
            os.environ.get("OSV_IMAGE")
            or os.environ.get("OSV_ALT_IMAGE")
            or "ghcr.io/google/osv-scanner:latest"
        )

        selinux_relabel = os.environ.get("GEOTOOLKIT_SELINUX_RELABEL", "0").lower() in (
            "1",
            "true",
            "yes",
        )
        mount_suffix = ":ro,Z" if selinux_relabel else ":ro"
        src_mount = f"{project_path_obj}:/src{mount_suffix}"

        # Support offline OSV runs. If GEOTOOLKIT_OSV_OFFLINE=1 is set and
        # no offline DB path is provided, skip OSV to avoid network calls.
        osv_offline = os.environ.get("GEOTOOLKIT_OSV_OFFLINE", "0").lower() in (
            "1",
            "true",
            "yes",
        )
        osv_offline_db = os.environ.get("GEOTOOLKIT_OSV_OFFLINE_DB")

        if osv_offline and not osv_offline_db:
            print(
                "OSV offline mode requested and no offline DB provided; skipping OSV-Scanner."
            )
            return []

        mounts = [src_mount]
        inner_args = ["scan", "source", "-r", "/src", "--format", "json"]
        # If an offline DB path is provided, mount it. Only pass the
        # --offline-db flag to the image if the image's help output
        # indicates support for that flag. This avoids passing unknown
        # flags to older image versions.
        if osv_offline_db:
            db_mount = f"{osv_offline_db}:/data/osv-offline-db:ro"
            mounts.append(db_mount)
            # Probe image for known offline flags and pass the first one
            # that appears in the image's help output. Allow override via
            # OSV_IMAGE_OFFLINE_FLAGS (comma-separated) to customize for
            # different image versions.
            candidate_flags_env = os.environ.get("OSV_IMAGE_OFFLINE_FLAGS")
            if candidate_flags_env:
                candidates = [
                    f.strip() for f in candidate_flags_env.split(",") if f.strip()
                ]
            else:
                # Common offline-related flags across OSV-Scanner versions
                candidates = [
                    "--offline-db",
                    "--offline-vulnerabilities",
                    "--download-offline-database",
                    "--download-offline-db",
                ]

            # Allow env override to skip probing if desired
            skip_probe = os.environ.get("OSV_SKIP_HELP_PROBE", "0").lower() in (
                "1",
                "true",
                "yes",
            )
            supports_flag = None
            if skip_probe:
                # If the caller explicitly says to skip probing but provided
                # OSV_IMAGE_HELP_SUPPORTS_OFFLINE, use that hint; otherwise assume none.
                hint = os.environ.get("OSV_IMAGE_HELP_SUPPORTS_OFFLINE")
                if hint and hint.lower() in ("1", "true", "yes"):
                    # Choose the first candidate as a sensible default when
                    # the caller asserts the image supports offline mode.
                    supports_flag = candidates[0] if candidates else None
                else:
                    supports_flag = None
            else:
                try:
                    probe_rc, probe_out, probe_err = run_with_seccomp_fallback(
                        base_cmd=build_podman_base([]),
                        image=osv_image,
                        inner_args=["--help"],
                        seccomp_path=choose_seccomp_path(project_path, "osv-scanner"),
                        timeout=5,
                        tool_name="osv-probe",
                    )
                    help_text = (probe_out or "") + (probe_err or "")
                    for flag in candidates:
                        if flag in help_text:
                            supports_flag = flag
                            break
                except Exception:
                    supports_flag = None

            if supports_flag:
                # supports_flag may be the exact flag string to pass (e.g. --offline-vulnerabilities)
                # For flags that require an argument, map known cases to the mounted path.
                flag = supports_flag
                if flag in (
                    "--offline-db",
                    "--download-offline-database",
                    "--download-offline-db",
                ):
                    inner_args += [flag, "/data/osv-offline-db"]
                else:
                    # Flags that are boolean toggles that don't take an argument
                    inner_args += [flag]
            else:
                # If offline was explicitly requested but no supported flag was found,
                # skip OSV to avoid network calls and inconsistent behavior.
                if osv_offline:
                    print(
                        "OSV offline requested but no supported offline flag detected in image; skipping OSV to avoid network calls."
                    )
                    return []

        base_cmd = build_podman_base(mounts)

        try:
            # run with helper (handles seccomp fallback and logging)
            rc, out, err = run_with_seccomp_fallback(
                base_cmd=base_cmd,
                image=osv_image,
                inner_args=inner_args,
                seccomp_path=chosen,
                timeout=timeout,
                tool_name="osv-scanner",
            )

            if rc != 0:
                combined = (out or "") + "\n" + (err or "")
                # If the failure looks like a network/DNS problem (common in
                # CI/offline environments), skip OSV gracefully instead of
                # failing the whole pipeline. This helps offline runs where
                # api.osv.dev or other endpoints are unreachable.
                net_err_markers = [
                    "temporary failure in name resolution",
                    "lookup",
                    "connection refused",
                    "dial tcp",
                    "read: connection refused",
                    "no such host",
                    "i/o timeout",
                    "connection timed out",
                ]
                low = combined.lower()
                if any(m in low for m in net_err_markers):
                    print(
                        "OSV-Scanner appears to have failed due to network/DNS errors. Skipping OSV to allow the scan to continue in offline/CI environments."
                    )
                    print(
                        "If you want OSV results in offline CI, run the offline DB preparation script on a networked host and set GEOTOOLKIT_OSV_OFFLINE=1 and GEOTOOLKIT_OSV_OFFLINE_DB=/path/to/db"
                    )
                    return []
                # If OSV explicitly reports the offline DB is unavailable
                # or that no offline version of the database exists, treat
                # this as an offline-missing condition and return empty
                # findings instead of failing the entire run.
                if (
                    "unable to fetch OSV database" in combined
                    or "no offline version of the OSV database" in combined
                ):
                    print(
                        "OSV-Scanner offline DB missing or incomplete; skipping OSV results."
                    )
                    return []
                print(f"OSV-Scanner initial error (exit {rc}): {err}")
                # Try alt image fallback similar to previous behavior
                alt = (
                    os.environ.get("OSV_ALT_IMAGE")
                    or "docker.io/google/osv-scanner:latest"
                )
                if alt != osv_image:
                    rc2, out2, err2 = run_with_seccomp_fallback(
                        base_cmd=base_cmd,
                        image=alt,
                        inner_args=inner_args,
                        seccomp_path=chosen,
                        timeout=timeout,
                        tool_name="osv-scanner-alt",
                    )
                    if rc2 == 0 and out2.strip():
                        return OutputParser.parse_osv_scanner_json(out2)

                # Final failure
                return None

            json_output = out
            if not json_output.strip():
                print("Warning: OSV-Scanner returned empty output")
                return []

            return OutputParser.parse_osv_scanner_json(json_output)
        except FileNotFoundError:
            print("OSV-Scanner command not found")
            return None
        except subprocess.CalledProcessError as e:
            print(f"OSV-Scanner execution error: {e}")
            return None
        except subprocess.TimeoutExpired:
            print("Error: OSV-Scanner scan timed out.")
            return None
        except json.JSONDecodeError as e:
            print(f"Failed to decode OSV-Scanner JSON output: {e}")
            return None
        except Exception as e:
            print(f"Unexpected error running OSV-Scanner: {e}")
            return None
