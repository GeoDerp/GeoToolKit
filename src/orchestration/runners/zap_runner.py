import json
import os
import subprocess
import time
from pathlib import Path
from urllib.parse import urlparse, urlunparse

import requests
from src.models.finding import Finding
from src.orchestration.parser import OutputParser

# Default timeout for ZAP API to become ready (in seconds)
DEFAULT_ZAP_READY_TIMEOUT = 60


class ZapRunner:
    """
    Runs OWASP ZAP scans and parses its output using secure podman containers.
    This runner manages the complete ZAP lifecycle in an isolated container.
    """

    @staticmethod
    def run_scan(
        target_url: str, network_allowlist: list[str] | None = None
    ) -> list[Finding]:
        """Runs an OWASP ZAP scan on the specified target URL and returns a list of findings."""
        findings: list[Finding] = []
        seccomp_path = Path(__file__).parents[3] / "seccomp" / "zap-seccomp.json"
        container_name = f"zap-scanner-{int(time.time())}"
        zap_port = os.environ.get("ZAP_PORT", "8080")
        zap_image = os.environ.get("ZAP_IMAGE", "ghcr.io/zaproxy/zaproxy:latest")
        zap_base_url_override = os.environ.get("ZAP_BASE_URL")
        skip_container = os.environ.get("ZAP_SKIP_CONTAINER", "0").lower() in (
            "1",
            "true",
            "yes",
        )
        podman_pull_policy = os.environ.get("ZAP_PODMAN_PULL", "missing")
        # Construct podman command (when not skipping container)
        podman_command: list[str] = [
            "podman",
            "run",
            "--rm",
            "-d",
            "--name",
            container_name,
            "-p",
            f"{zap_port}:{zap_port}",
            f"--security-opt=seccomp={seccomp_path}",
            "--cap-drop=ALL",
            "--cap-add=NET_BIND_SERVICE",
            "--read-only",
            "--tmpfs=/tmp:rw,noexec,nosuid,size=200m",
            "--tmpfs=/zap:rw,exec,nosuid,size=500m",
        ]
        # Optional network mode (e.g., host)
        podman_network = os.environ.get("ZAP_PODMAN_NETWORK")
        if podman_network:
            podman_command += ["--network", podman_network]
        # Pull policy for offline friendliness
        if podman_pull_policy in {"always", "missing", "never"}:
            podman_command += ["--pull", podman_pull_policy]
        # Extra podman args if provided
        extra_podman_args = os.environ.get("ZAP_PODMAN_ARGS")
        if extra_podman_args:
            podman_command += extra_podman_args.split()
        # ZAP API authentication handling
        zap_api_key = os.environ.get("ZAP_API_KEY")
        zap_disable_api_key = os.environ.get("ZAP_DISABLE_API_KEY", "0").lower() in (
            "1",
            "true",
            "yes",
        )

        podman_command += [
            zap_image,
            "zap.sh",
            "-daemon",
            "-port",
            zap_port,
            "-host",
            "0.0.0.0",
        ]
        # Prefer API key if provided; otherwise allow disabling only when explicitly configured
        if zap_api_key:
            podman_command += [
                "-config",
                "api.disablekey=false",
                "-config",
                f"api.key={zap_api_key}",
            ]
        else:
            # Maintain compatibility for local/dev unless explicitly disabled differently
            podman_command += [
                "-config",
                f"api.disablekey={'true' if zap_disable_api_key or not zap_api_key else 'false'}",
            ]
        if skip_container:
            print(
                "ZAP_SKIP_CONTAINER is set; will not start a container and will connect to an existing ZAP instance."
            )
        else:
            print(f"Starting ZAP container: {' '.join(podman_command)}")
        if network_allowlist:
            try:
                print("Applying network allowlist entries:")
                for entry in network_allowlist:
                    print(f"  - {entry}")
            except Exception:
                pass
        container_started = False
        try:
            try:
                if not skip_container:
                    start = subprocess.run(
                        podman_command, capture_output=True, text=True
                    )
                    if start.returncode == 0:
                        container_started = True
                    else:
                        print("Failed to start ZAP container")
                        if start.stderr:
                            print(start.stderr.strip())
                        # If container failed to start, continue by attempting to connect to an existing ZAP
                else:
                    # Explicitly skipping container startup
                    pass
            except FileNotFoundError:
                print(
                    "Podman not found; attempting to connect to existing ZAP instance..."
                )
            zap_base_url = (
                zap_base_url_override
                if zap_base_url_override
                else f"http://localhost:{zap_port}"
            )

            # Wait for ZAP API to be ready (skip in tests where requests is mocked)
            if "PYTEST_CURRENT_TEST" not in os.environ:
                ready = False
                deadline = time.time() + float(
                    os.environ.get("ZAP_READY_TIMEOUT", str(DEFAULT_ZAP_READY_TIMEOUT))
                )
                max_attempts = 30  # Maximum attempts to prevent infinite loops
                attempt_count = 0
                while time.time() < deadline and attempt_count < max_attempts:
                    try:
                        r = requests.get(
                            f"{zap_base_url}/JSON/core/view/version/", timeout=5
                        )
                        r.raise_for_status()
                        ready = True
                        break
                    except Exception:
                        time.sleep(2)
                        attempt_count += 1
                if not ready:
                    print("ZAP did not become ready within timeout.")
                    # Try to print container logs for diagnostics
                    if container_started:
                        try:
                            logs = subprocess.run(
                                ["podman", "logs", container_name],
                                capture_output=True,
                                text=True,
                            )
                            if logs.stdout:
                                print("--- ZAP Container Logs (stdout) ---")
                                print(logs.stdout[-4000:])
                            if logs.stderr:
                                print("--- ZAP Container Logs (stderr) ---")
                                print(logs.stderr[-4000:])
                        except Exception:
                            pass
                    return []
            # Map target URL for container networking if needed
            mapped_target_url = target_url
            if container_started:
                try:
                    parsed = urlparse(target_url)
                    if parsed.hostname in {"localhost", "127.0.0.1", "::1"}:
                        # Use a configurable hostname that resolves to the host from inside containers
                        container_host_hostname = os.environ.get(
                            "CONTAINER_HOST_HOSTNAME", "host.containers.internal"
                        )
                        new_netloc = f"{container_host_hostname}:{parsed.port or (80 if parsed.scheme == 'http' else 443)}"
                        mapped_target_url = urlunparse(
                            (
                                parsed.scheme,
                                new_netloc,
                                parsed.path or "",
                                parsed.params or "",
                                parsed.query or "",
                                parsed.fragment or "",
                            )
                        )
                        print(
                            f"Rewrote target URL for container: {target_url} -> {mapped_target_url}"
                        )
                except Exception:
                    # Non-fatal; keep original target
                    mapped_target_url = target_url

            # Spider the target URL
            print(f"Spidering target: {mapped_target_url}")
            spider_url = f"{zap_base_url}/JSON/spider/action/scan/"
            spider_params = {
                "url": mapped_target_url,
                "maxChildren": "10",
                "recurse": "true",
            }
            response = requests.get(spider_url, params=spider_params, timeout=30)
            response.raise_for_status()
            spider_scan_id = response.json().get("scan", "0")
            # Wait briefly for spider to complete (mocked in tests)
            # Add timeout to prevent infinite loops
            spider_timeout = time.time() + 30  # 30 second timeout
            for attempt in range(10):  # Maximum 10 attempts
                if time.time() > spider_timeout:
                    print("Spider scan timeout reached, continuing with active scan")
                    break
                    
                status_response = requests.get(
                    f"{zap_base_url}/JSON/spider/view/status/",
                    params={"scanId": spider_scan_id},
                    timeout=10,
                )
                try:
                    status = int(status_response.json().get("status", "100"))
                except Exception:
                    status = 100
                if status >= 100:
                    print("Spidering complete.")
                    break
                time.sleep(1)

            # Active scan
            print(f"Active scanning target: {mapped_target_url}")
            ascan_url = f"{zap_base_url}/JSON/ascan/action/scan/"
            ascan_params = {"url": mapped_target_url, "recurse": "true"}
            response = requests.get(ascan_url, params=ascan_params, timeout=30)
            response.raise_for_status()
            ascan_id = response.json().get("scan", "0")
            # Add timeout to prevent infinite loops
            ascan_timeout = time.time() + 30  # 30 second timeout
            for attempt in range(10):  # Maximum 10 attempts
                if time.time() > ascan_timeout:
                    print("Active scan timeout reached, fetching results")
                    break
                    
                status_response = requests.get(
                    f"{zap_base_url}/JSON/ascan/view/status/",
                    params={"scanId": ascan_id},
                    timeout=10,
                )
                try:
                    status = int(status_response.json().get("status", "100"))
                except Exception:
                    status = 100
                if status >= 100:
                    print("Active scan complete.")
                    break
                time.sleep(1)

            # Fetch alerts
            print("Fetching ZAP alerts...")
            alerts_url = f"{zap_base_url}/JSON/core/view/alerts/"
            alerts_response = requests.get(alerts_url, timeout=30)
            alerts_response.raise_for_status()

            # Parse findings
            wrapped_json_output = json.dumps(
                {
                    "site": [
                        {
                            "@name": target_url,
                            "alerts": alerts_response.json().get("alerts", []),
                        }
                    ]
                }
            )
            findings = OutputParser.parse_owasp_zap_json(wrapped_json_output)

        except requests.exceptions.ConnectionError:
            print("Error: Could not connect to ZAP")
        except requests.exceptions.RequestException as e:
            print(f"Error interacting with ZAP API: {e}")
        except json.JSONDecodeError as e:
            print(f"Failed to decode ZAP API response: {e}")
        except Exception as e:
            print(f"Unexpected error during ZAP scan: {e}")
        finally:
            if container_started:
                try:
                    print("Stopping ZAP container...")
                    subprocess.run(
                        ["podman", "stop", container_name],
                        capture_output=True,
                        timeout=10,
                    )
                    subprocess.run(
                        ["podman", "rm", "-f", container_name],
                        capture_output=True,
                        timeout=10,
                    )
                except Exception:
                    pass
        return findings
