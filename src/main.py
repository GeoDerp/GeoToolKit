import argparse
import json
import os
import sys
from typing import Any

from src.models.project import Project
from src.orchestration.workflow import Workflow
from src.reporting.report import ReportGenerator


def main() -> None:
    """Main entry point for the Automated Malicious Code Scanner CLI."""
    parser = argparse.ArgumentParser(description="Automated Malicious Code Scanner")
    
    # MCP server arguments
    parser.add_argument(
        "--mcp-server", 
        action="store_true", 
        help="Start the MCP server instead of running a scan."
    )
    parser.add_argument(
        "--mcp-host", 
        default="127.0.0.1", 
        help="Host for MCP server (default: 127.0.0.1)."
    )
    parser.add_argument(
        "--mcp-port", 
        default=9000, 
        type=int, 
        help="Port for MCP server (default: 9000)."
    )
    
    # Standard scanning arguments
    parser.add_argument(
        "--input", 
        help="Path to the projects.json file."
    )
    parser.add_argument(
        "--output",
        help="Path for the generated report (e.g., report.md).",
    )
    parser.add_argument(
        "--database-path",
        required=True,
        help="Path to the offline vulnerability database (e.g., data/offline-db.tar.gz).",
    )
    parser.add_argument(
        "--network-allowlist", help="Path to the network-allowlist.txt file."
    )

    args = parser.parse_args()

    # Handle MCP server mode
    if args.mcp_server:
        try:
            # Add the project root to Python path so mcp_server module can be imported
            project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            sys.path.insert(0, project_root)
            
            from mcp_server.mcp_server import main as mcp_main
            print(f"Starting MCP server on {args.mcp_host}:{args.mcp_port}")
            print(f"Database path: {args.database_path}")
            
            # Set environment variables for the MCP server to use
            os.environ['MCP_HOST'] = args.mcp_host
            os.environ['MCP_PORT'] = str(args.mcp_port)
            os.environ['DATABASE_PATH'] = args.database_path
            
            mcp_main()
            return
        except ImportError as e:
            print(f"Error: MCP dependencies not available: {e}")
            print("Install with: uv sync --extra mcp")
            sys.exit(1)
        except Exception as e:
            print(f"Error starting MCP server: {e}")
            sys.exit(1)

    # Validate required arguments for scanning mode
    if not args.input:
        parser.error("--input is required when not in MCP server mode")
    if not args.output:
        parser.error("--output is required when not in MCP server mode")

    print(
        f"Starting GeoToolKit scan with input: {args.input}, output: {args.output}, database: {args.database_path}"
    )
    if args.network_allowlist:
        print(f"Network allow-list: {args.network_allowlist}")

    # 1. Read projects.json
    projects_data: dict[str, Any] = {}
    try:
        with open(args.input) as f:
            projects_data = json.load(f)
    except FileNotFoundError:
        print(f"Error: Input file not found at {args.input}")
        return
    except json.JSONDecodeError:
        print(f"Error: Invalid JSON in input file {args.input}")
        return

    timeouts = projects_data.get("timeouts", {})

    def _normalize_network_from_config(
        proj: dict[str, Any],
    ) -> tuple[list[str], list[str], list[str]]:
        """
        Interpret a project's optional network_config structure into:
        - allow_hosts: list of "host:port" entries
        - allow_ip_ranges: list of CIDR strings
        - ports: list of port strings

        Expected schema of network_config:
          {
            "ports": ["3000", "8080"],
            "protocol": "http|https",
            "health_endpoint": "/health",
            "startup_time_seconds": 30,
            "allowed_egress": {
              "localhost": ["3000"],
              "192.168.1.0/24": ["8080"],
              "external_hosts": ["example.com"]
            }
          }
        """
        allow_hosts: set[str] = set()
        allow_ip_ranges: set[str] = set()
        ports: list[str] = [str(p) for p in (proj.get("ports") or [])]

        net_cfg = proj.get("network_config") or {}
        cfg_ports = [str(p) for p in (net_cfg.get("ports") or [])]
        # if top-level ports is empty, use network_config.ports
        if not ports:
            ports = cfg_ports
        protocol = (net_cfg.get("protocol") or "").lower()
        default_port = "443" if protocol == "https" else "80"
        # Build allowlist from allowed_egress
        allowed = net_cfg.get("allowed_egress") or {}
        # External hosts list (no specific ports attached). Apply cfg ports or default
        external_hosts = allowed.get("external_hosts") or []
        if isinstance(external_hosts, str):
            external_hosts = [external_hosts]
        for host in external_hosts:
            host = str(host).strip()
            if not host:
                continue
            if ports:
                for p in ports:
                    allow_hosts.add(f"{host}:{str(p).strip()}")
            else:
                allow_hosts.add(f"{host}:{default_port}")
        # Other keys: hostname/IP literal/CIDR -> port list
        for key, val in allowed.items():
            if key == "external_hosts":
                continue
            # value is list of ports (can be empty)
            port_list = val if isinstance(val, list) else ([val] if val else [])
            port_list = [str(p).strip() for p in port_list if str(p).strip()]
            if "/" in key:
                # CIDR range
                allow_ip_ranges.add(key)
                # We don't encode ports with CIDR in allowlist strings; keep as ranges for runners
            else:
                # Treat as host literal; combine with specified ports or fallback to cfg ports/default
                ports_for_host = port_list or (ports if ports else [default_port])
                for p in ports_for_host:
                    allow_hosts.add(f"{key}:{p}")
                # Convenience: if host looks like 0.0.0.0, also include localhost/127.0.0.1
                if key in {"0.0.0.0", "::", "::0"} and ports_for_host:
                    for p in ports_for_host:
                        allow_hosts.add(f"localhost:{p}")
                        allow_hosts.add(f"127.0.0.1:{p}")

        return sorted(allow_hosts), sorted(allow_ip_ranges), [str(p) for p in ports]

    projects: list[Project] = []
    for project_dict in projects_data.get("projects", []):
        try:
            # Extract name from dict or derive from URL
            name = project_dict.get("name", project_dict["url"].split("/")[-1])

            # Coerce allowlist fields to lists of strings if provided as single strings
            allow_hosts = project_dict.get("network_allow_hosts", [])
            if isinstance(allow_hosts, str):
                allow_hosts = [allow_hosts]
            allow_ip_ranges = project_dict.get("network_allow_ip_ranges", [])
            if isinstance(allow_ip_ranges, str):
                allow_ip_ranges = [allow_ip_ranges]

            # If network_config is present, derive allowlists and ports from it
            if project_dict.get("network_config"):
                derived_hosts, derived_ranges, derived_ports = (
                    _normalize_network_from_config(project_dict)
                )
                # Merge, giving precedence to explicitly provided top-level fields
                allow_hosts = list(
                    {*(derived_hosts or []), *[str(x) for x in (allow_hosts or [])]}
                )
                allow_ip_ranges = list(
                    {
                        *(derived_ranges or []),
                        *[str(x) for x in (allow_ip_ranges or [])],
                    }
                )
                top_ports = project_dict.get("ports", [])
                if not top_ports:
                    project_dict["ports"] = derived_ports

            project = Project(
                url=project_dict["url"],
                name=name,
                language=project_dict.get("language"),
                description=project_dict.get("description"),
                network_allow_hosts=[str(x) for x in (allow_hosts or [])],
                network_allow_ip_ranges=[str(x) for x in (allow_ip_ranges or [])],
                ports=[str(p) for p in (project_dict.get("ports", []) or [])],
            )
            projects.append(project)
        except KeyError as e:
            print(f"Warning: Project entry missing required key {e}: {project_dict}")
        except Exception as e:
            print(f"Warning: Could not create Project object from {project_dict}: {e}")

    if not projects:
        print("No valid projects found to scan. Exiting.")
        return

    # Prepare optional network allowlist entries (global)
    global_allowlist_entries: list[str] | None = None
    if args.network_allowlist:
        try:
            with open(args.network_allowlist) as f:
                global_allowlist_entries = [
                    line.strip()
                    for line in f
                    if line.strip() and not line.strip().startswith("#")
                ]
        except Exception as e:
            print(f"Warning: Failed to read network allowlist file: {e}")

    # 2. Run scans for each project
    all_scans = []
    for project in projects:
        # Build an allowlist from the project's own fields if no global allowlist provided
        per_project_allowlist: list[str] | None = None
        if global_allowlist_entries is not None:
            per_project_allowlist = global_allowlist_entries
        else:
            # Combine host:port entries from network_allow_hosts and ports on localhost
            combined: set[str] = set()
            try:
                for entry in getattr(project, "network_allow_hosts", []) or []:
                    if isinstance(entry, str) and entry.strip():
                        combined.add(entry.strip())
                # Include any CIDR ranges from network_allow_ip_ranges for runner awareness
                for cidr in getattr(project, "network_allow_ip_ranges", []) or []:
                    if isinstance(cidr, str) and cidr.strip():
                        combined.add(cidr.strip())
                # If ports are provided, allow localhost for each
                for p in getattr(project, "ports", []) or []:
                    p_str = str(p).strip()
                    if p_str:
                        combined.add(f"127.0.0.1:{p_str}")
                        combined.add(f"localhost:{p_str}")
            except Exception:
                pass
            per_project_allowlist = sorted(combined) if combined else None

        scan_result = Workflow.run_project_scan(
            project, network_allowlist=per_project_allowlist, timeouts=timeouts
        )
        all_scans.append(scan_result)

    # 3. Generate report
    print(f"Generating report to {args.output}...")
    report_generator = ReportGenerator(all_scans, projects, args.output)
    report_generator.generate_report()
    print("Report generation complete.")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nOperation cancelled by user")
        exit(1)
    except Exception as e:
        print(f"Error: {e}")
        exit(1)
