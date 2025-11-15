import ipaddress
import json
import os
import socket
import subprocess
import time
from urllib.parse import urlparse, urlunparse

import requests  # type: ignore[import]
from src.models.finding import Finding
from src.orchestration.parser import OutputParser
from src.orchestration.podman_helper import (
    _make_log_file,
    build_podman_base,
    choose_seccomp_path,
)

# Default timeout for ZAP API to become ready (in seconds)
# Increased default to allow slower container startups in constrained hosts.
DEFAULT_ZAP_READY_TIMEOUT = 300


class ZapRunner:
    """
    Runs OWASP ZAP scans and parses its output using secure podman containers.
    This runner manages the complete ZAP lifecycle in an isolated container.
    """

    @staticmethod
    def _normalize_allowlist(
        network_allowlist: dict | list | None,
    ) -> tuple[list[str], list[str], list[str]]:
        hosts: list[str] = []
        ip_ranges: list[str] = []
        ports: list[str] = []

        if isinstance(network_allowlist, dict):
            hosts = [str(h).strip() for h in network_allowlist.get("hosts") or [] if str(h).strip()]
            ip_ranges = [str(r).strip() for r in network_allowlist.get("ip_ranges") or [] if str(r).strip()]
            ports = [str(p).strip() for p in network_allowlist.get("ports") or [] if str(p).strip()]
        elif isinstance(network_allowlist, list):
            for entry in network_allowlist:
                entry_str = str(entry).strip()
                if not entry_str:
                    continue
                if "/" in entry_str:
                    ip_ranges.append(entry_str)
                else:
                    hosts.append(entry_str)

        return hosts, ip_ranges, ports

    @staticmethod
    def _podman_network_exists(name: str) -> bool:
        if not name:
            return False
        try:
            probe = subprocess.run(
                ["podman", "network", "exists", name],
                capture_output=True,
                text=True,
                check=False,
            )
            return probe.returncode == 0
        except Exception:
            return False

    @staticmethod
    def _is_target_allowed(
        target_url: str, hosts: list[str], ip_ranges: list[str], ports: list[str]
    ) -> bool:
        """Return True if the target URL satisfies the allowlist requirements."""

        parsed = urlparse(target_url)
        hostname = parsed.hostname or ""
        port = parsed.port
        if port is None:
            port = 443 if parsed.scheme == "https" else 80

        host_allowed = False if hosts else True
        for entry in hosts:
            entry_host = entry
            entry_port: str | None = None
            if ":" in entry:
                entry_host, entry_port = entry.rsplit(":", 1)
            entry_host = entry_host.strip()
            if not entry_host:
                continue
            if hostname and hostname.lower() == entry_host.lower():
                if entry_port is None or str(port) == entry_port:
                    host_allowed = True
                    break

        if not host_allowed and hostname:
            # Evaluate CIDR ranges
            try:
                ip_obj = ipaddress.ip_address(hostname)
                for cidr in ip_ranges:
                    try:
                        network = ipaddress.ip_network(cidr, strict=False)
                    except ValueError:
                        continue
                    if ip_obj in network:
                        host_allowed = True
                        break
            except ValueError:
                # Hostname is not an IP address
                pass

        port_allowed = False if ports else True
        if ports:
            port_allowed = str(port) in {str(p) for p in ports}

        return host_allowed and port_allowed

    @staticmethod
    def run_scan(
        target_url: str,
        network_allowlist: dict | list | None = None,
        timeout: int | None = None,
    ) -> list[Finding]:
        """Runs an OWASP ZAP scan on the specified target URL and returns a list of findings."""
        findings: list[Finding] = []
        container_name = f"zap-scanner-{int(time.time())}"

        # choose seccomp path if allowed
        use_seccomp_env = os.environ.get("GEOTOOLKIT_USE_SECCOMP", "1").lower()
        seccomp_path = None
        if use_seccomp_env not in ("0", "false", "no"):
            seccomp_path = choose_seccomp_path(None, "zap")

        zap_port = os.environ.get("ZAP_PORT", "8080")
        zap_image = os.environ.get("ZAP_IMAGE", "ghcr.io/zaproxy/zaproxy:latest")
        zap_base_url_override = os.environ.get("ZAP_BASE_URL")
        skip_container = os.environ.get("ZAP_SKIP_CONTAINER", "0").lower() in (
            "1",
            "true",
            "yes",
        )
        podman_pull_policy = os.environ.get("ZAP_PODMAN_PULL", "missing")

        # Create a persistent per-run log file for ZAP so we can inspect
        # podman command lines, stdout/stderr and container logs when
        # readiness fails.
        log_file = _make_log_file("zap")

        # Construct podman command (when not skipping container)
        base_cmd = build_podman_base([])

        # For debugging, allow callers to request that containers are kept after exit
        keep_container = os.environ.get(
            "GEOTOOLKIT_ZAP_KEEP_CONTAINER", "0"
        ).lower() in (
            "1",
            "true",
            "yes",
        )
        if keep_container:
            try:
                if "--rm" in base_cmd:
                    base_cmd = [c for c in base_cmd if c != "--rm"]
            except Exception:
                pass

        # Normalize allowlist early so we can select the appropriate network
        allow_hosts, allow_ip_ranges, allow_ports = ZapRunner._normalize_allowlist(
            network_allowlist
        )

        # Optional network selection
        podman_network = os.environ.get("ZAP_PODMAN_NETWORK")
        if not podman_network:
            preferred = os.environ.get("GEOTOOLKIT_DAST_NETWORK", "gt-dast-net")
            if ZapRunner._podman_network_exists(preferred):
                podman_network = preferred
            elif any(
                h.startswith("127.0.0.1") or h.startswith("localhost") for h in allow_hosts
            ):
                # Allow host loopback access but keep container isolated from broader network
                podman_network = "slirp4netns:allow_host_loopback=true"
        if podman_network:
            try:
                if "--network=none" in base_cmd:
                    base_cmd = [c for c in base_cmd if c != "--network=none"]
            except Exception:
                pass

        # tmpfs sizes
        tmpfs_tmp_size = os.environ.get("ZAP_TMPFS_TMP_SIZE", "200m")
        tmpfs_zap_size = os.environ.get("ZAP_TMPFS_ZAP_SIZE", "1024m")
        tmpfs_home_size = os.environ.get("ZAP_TMPFS_HOME_SIZE", "512m")

        # If the caller requested host networking, pre-check port availability
        publish_ports = True
        if podman_network and podman_network.lower() == "host":
            try:
                port_int = int(zap_port)
            except Exception:
                port_int = None

            if port_int is not None:
                s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                try:
                    s.bind(("0.0.0.0", port_int))
                    s.listen(1)
                    s.close()
                    publish_ports = False
                except OSError:
                    print(
                        f"Requested host network with port {port_int} but port is in use; falling back to bridge-mode port mapping."
                    )
                    podman_network = None
                    publish_ports = True
                finally:
                    try:
                        s.close()
                    except Exception:
                        pass
            else:
                publish_ports = False

        podman_command: list[str] = base_cmd + [
            "-d",
            "--name",
            container_name,
            "--cap-add=NET_BIND_SERVICE",
            "--read-only",
            f"--tmpfs=/tmp:rw,noexec,nosuid,size={tmpfs_tmp_size}",
            f"--tmpfs=/zap:rw,exec,nosuid,size={tmpfs_zap_size}",
            f"--tmpfs=/home/zap:rw,exec,nosuid,size={tmpfs_home_size}",
        ]

        if publish_ports:
            podman_command += ["-p", f"{zap_port}:{zap_port}"]
        if podman_network:
            podman_command += ["--network", podman_network]
        if seccomp_path:
            podman_command += [f"--security-opt=seccomp={str(seccomp_path)}"]
        if podman_pull_policy in {"always", "missing", "never"}:
            podman_command += ["--pull", podman_pull_policy]
        extra_podman_args = os.environ.get("ZAP_PODMAN_ARGS")
        if extra_podman_args:
            podman_command += extra_podman_args.split()

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

        disable_autoupdate = os.environ.get("ZAP_DISABLE_AUTOUPDATE", "0").lower() in (
            "1",
            "true",
            "yes",
        )
        if disable_autoupdate:
            podman_command += [
                "-config",
                "autoupdate.checkForUpdates=false",
                "-config",
                "autoupdate.checkForInstalledAddons=false",
            ]

        if zap_api_key:
            podman_command += [
                "-config",
                "api.disablekey=false",
                "-config",
                f"api.key={zap_api_key}",
            ]
        else:
            podman_command += [
                "-config",
                f"api.disablekey={'true' if zap_disable_api_key or not zap_api_key else 'false'}",
            ]

        if skip_container:
            print(
                "ZAP_SKIP_CONTAINER is set; will not start a container and will connect to an existing ZAP instance."
            )
        else:
            try:
                with open(log_file, "w", encoding="utf-8") as fh:
                    fh.write("# Podman command to start ZAP\n")
                    fh.write(" ".join(podman_command) + "\n\n")
            except Exception:
                pass
            print(f"Starting ZAP container: {' '.join(podman_command)}")

        if allow_hosts or allow_ip_ranges or allow_ports:
            try:
                print("Applying network allowlist entries:")
                for h in allow_hosts:
                    print(f"  - host: {h}")
                for r in allow_ip_ranges:
                    print(f"  - ip_range: {r}")
                for p in allow_ports:
                    print(f"  - port: {p}")
            except Exception:
                pass
        elif target_url.startswith(("http://", "https://")):
            raise PermissionError(
                "Network allowlist is required for DAST scans but none was provided."
            )

        if not ZapRunner._is_target_allowed(
            target_url, allow_hosts, allow_ip_ranges, allow_ports
        ):
            raise PermissionError(
                f"Target {target_url} is not included in the provided network allowlist."
            )

        # Pre-check: resolve target hostname to IP(s) and check against allowlist
        try:
            parsed = urlparse(target_url)
            hostname = parsed.hostname
            target_port = parsed.port

            ips = set()
            if hostname:
                try:
                    resolved = socket.getaddrinfo(hostname, None)
                    ips = {ai[4][0] for ai in resolved}
                except Exception:
                    ips = set()

            for ip in ips:
                s_ip = str(ip)
                for cidr in allow_ip_ranges:
                    if cidr and s_ip.startswith(str(cidr).split("/")[0]):
                        print(
                            f"Target IP {s_ip} matched allowlist {cidr}; allowing network access."
                        )

            if hostname:
                for ah in allow_hosts:
                    if ah and (ah in hostname or hostname in ah):
                        print(
                            f"Target hostname {hostname} matched allowlist {ah}; allowing network access."
                        )

            if target_port and any(str(target_port) == str(p) for p in allow_ports):
                print(
                    f"Target port {target_port} is listed in allowlist; allowing network access."
                )
        except Exception:
            pass

        container_started = False
        try:
            try:
                if not skip_container:
                    start = subprocess.run(
                        podman_command, capture_output=True, text=True
                    )
                    try:
                        with open(log_file, "a", encoding="utf-8") as fh:
                            fh.write("# podman start stdout\n")
                            fh.write((start.stdout or "") + "\n\n")
                            fh.write("# podman start stderr\n")
                            fh.write((start.stderr or "") + "\n\n")
                    except Exception:
                        pass

                    if start.returncode == 0:
                        container_started = True
                    else:
                        print("Failed to start ZAP container")
                        if start.stderr:
                            print(start.stderr.strip())
                        try:
                            ps = subprocess.run(
                                [
                                    "podman",
                                    "ps",
                                    "-a",
                                    "--filter",
                                    f"name={container_name}",
                                ],
                                capture_output=True,
                                text=True,
                            )
                            with open(log_file, "a", encoding="utf-8") as fh:
                                fh.write("# podman ps -a output\n")
                                fh.write((ps.stdout or "") + "\n\n")
                        except Exception:
                            pass
                else:
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

            # Readiness checks
            if "PYTEST_CURRENT_TEST" not in os.environ:
                ready = False
                deadline = time.time() + float(
                    os.environ.get("ZAP_READY_TIMEOUT", str(DEFAULT_ZAP_READY_TIMEOUT))
                )
                attempt_count = 0
                backoff = float(os.environ.get("ZAP_READY_BACKOFF", "2"))
                log_every = int(os.environ.get("ZAP_READY_LOG_EVERY", "1"))
                while time.time() < deadline:
                    attempt_count += 1
                    if attempt_count % log_every == 0:
                        try:
                            print(
                                f"ZAP readiness attempt {attempt_count}, deadline in {int(deadline - time.time())}s"
                            )
                        except Exception:
                            pass

                    try:
                        parsed_probe = urlparse(zap_base_url)
                        probe_host = parsed_probe.hostname or "localhost"
                        probe_port = int(parsed_probe.port or zap_port)
                    except Exception:
                        probe_host = "localhost"
                        try:
                            probe_port = int(zap_port)
                        except Exception:
                            probe_port = None

                    tcp_ok = False
                    if probe_port is not None:
                        try:
                            with socket.create_connection(
                                (probe_host, probe_port), timeout=3
                            ):
                                tcp_ok = True
                        except Exception:
                            tcp_ok = False

                    if tcp_ok:
                        try:
                            r = requests.get(
                                f"{zap_base_url}/JSON/core/view/version/", timeout=5
                            )
                            r.raise_for_status()
                            ready = True
                            break
                        except Exception:
                            pass

                    if container_started:
                        try:
                            logs = subprocess.run(
                                ["podman", "logs", container_name],
                                capture_output=True,
                                text=True,
                            )
                            try:
                                with open(log_file, "a", encoding="utf-8") as fh:
                                    fh.write(
                                        f"# podman logs (poll attempt {attempt_count})\n"
                                    )
                                    fh.write((logs.stdout or "") + "\n\n")
                            except Exception:
                                pass
                            if (
                                logs
                                and logs.stdout
                                and "ZAP is now listening" in logs.stdout
                            ):
                                ready = True
                                break
                        except Exception:
                            pass

                    time.sleep(backoff)

                if not ready:
                    print("ZAP did not become ready within timeout.")
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
                        container_host_hostname = os.environ.get(
                            "CONTAINER_HOST_HOSTNAME"
                        )
                        if not container_host_hostname and container_started:
                            try:
                                insp = subprocess.run(
                                    [
                                        "podman",
                                        "inspect",
                                        "--format",
                                        "{{range .NetworkSettings.Networks}}{{.Gateway}}{{end}}",
                                        container_name,
                                    ],
                                    capture_output=True,
                                    text=True,
                                    timeout=3,
                                )
                                gw = (insp.stdout or "").strip()
                                if gw:
                                    container_host_hostname = gw
                            except Exception:
                                container_host_hostname = None

                        if not container_host_hostname:
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
                    mapped_target_url = target_url

            # Ensure the ZAP base URL is reachable; attempt container-IP fallback if needed
            try:
                r = requests.get(f"{zap_base_url}/JSON/core/view/version/", timeout=5)
                r.raise_for_status()
            except Exception:
                if container_started:
                    try:
                        insp = subprocess.run(
                            [
                                "podman",
                                "inspect",
                                "--format",
                                "{{range .NetworkSettings.Networks}}{{.IPAddress}}{{end}}",
                                container_name,
                            ],
                            capture_output=True,
                            text=True,
                            timeout=5,
                        )
                        ip = (insp.stdout or "").strip()
                        if ip:
                            alt_base = f"http://{ip}:{zap_port}"
                            print(
                                f"HTTP probe failed against {zap_base_url}; retrying using container IP {alt_base}"
                            )
                            try:
                                r2 = requests.get(
                                    f"{alt_base}/JSON/core/view/version/", timeout=5
                                )
                                r2.raise_for_status()
                                zap_base_url = alt_base
                            except Exception:
                                pass
                    except Exception:
                        pass

            # Spider the target URL
            print(f"Spidering target: {mapped_target_url}")
            
            # Check if spider add-on is available before attempting scan
            try:
                components_response = requests.get(
                    f"{zap_base_url}/JSON/core/view/componentList/", timeout=10
                )
                components_response.raise_for_status()
                components = components_response.json()
                has_spider = any(
                    "spider" in str(comp).lower() 
                    for comp in components.get("componentList", [])
                )
                if not has_spider:
                    print("Warning: Spider component not found in ZAP componentList")
                    print("Available components:", components.get("componentList", []))
            except Exception as e:
                print(f"Warning: Could not check ZAP components: {e}")
            
            # Try to start spider scan
            spider_url = f"{zap_base_url}/JSON/spider/action/scan/"
            spider_params = {
                "url": mapped_target_url,
                "maxChildren": "10",
                "recurse": "true",
            }
            
            try:
                response = requests.get(spider_url, params=spider_params, timeout=30)
                response.raise_for_status()
                spider_scan_id = response.json().get("scan", "0")
            except requests.exceptions.HTTPError as e:
                if e.response and e.response.status_code == 404:
                    # Spider add-on might not be available or API changed
                    print("Spider API returned 404 - add-on may not be loaded. Skipping spider phase.")
                    print("You can manually install spider add-on in ZAP or use a different ZAP image.")
                    spider_scan_id = None
                else:
                    raise
            
            # If spider started successfully, wait for completion
            if spider_scan_id is not None:
                spider_seconds = int(os.environ.get("ZAP_SPIDER_TIMEOUT", "120"))
                spider_timeout = time.time() + spider_seconds
                for _attempt in range(max(1, spider_seconds // 1)):
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
            else:
                print("Skipped spider phase, proceeding directly to active scan")

            # Active scan
            print(f"Active scanning target: {mapped_target_url}")
            ascan_url = f"{zap_base_url}/JSON/ascan/action/scan/"
            ascan_params = {"url": mapped_target_url, "recurse": "true"}
            ascan_seconds = int(os.environ.get("ZAP_ASCAN_TIMEOUT", "600"))
            response = requests.get(ascan_url, params=ascan_params, timeout=30)
            response.raise_for_status()
            ascan_id = response.json().get("scan", "0")

            ascan_timeout = time.time() + ascan_seconds
            for _attempt in range(max(1, ascan_seconds // 1)):
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
