import argparse
import json

from models.project import Project
from orchestration.workflow import Workflow
from reporting.report import ReportGenerator

def main():
    """Main entry point for the Automated Malicious Code Scanner CLI."""
    parser = argparse.ArgumentParser(description="Automated Malicious Code Scanner")
    parser.add_argument("--input", required=True, help="Path to the projects.json file.")
    parser.add_argument("--output", required=True, help="Path for the generated report (e.g., report.md).")
    parser.add_argument("--database-path", required=True, help="Path to the offline vulnerability database (e.g., data/offline-db.tar.gz).")
    parser.add_argument("--network-allowlist", help="Path to the network-allowlist.txt file.")

    args = parser.parse_args()

    print(f"Starting GeoToolKit scan with input: {args.input}, output: {args.output}, database: {args.database_path}")
    if args.network_allowlist:
        print(f"Network allow-list: {args.network_allowlist}")

    # 1. Read projects.json
    projects_data: dict[str, list[dict[str, str]]] = {}
    try:
        with open(args.input) as f:
            projects_data = json.load(f)
    except FileNotFoundError:
        print(f"Error: Input file not found at {args.input}")
        return
    except json.JSONDecodeError:
        print(f"Error: Invalid JSON in input file {args.input}")
        return

    projects: list[Project] = []
    for project_dict in projects_data.get("projects", []):
        try:
            # Extract name from dict or derive from URL
            name = project_dict.get("name", project_dict["url"].split("/")[-1])
            
            project = Project(
                url=project_dict["url"],
                name=name,
                language=project_dict.get("language"),
                description=project_dict.get("description")
            )
            projects.append(project)
        except KeyError as e:
            print(f"Warning: Project entry missing required key {e}: {project_dict}")
        except Exception as e:
            print(f"Warning: Could not create Project object from {project_dict}: {e}")

    if not projects:
        print("No valid projects found to scan. Exiting.")
        return

    # Prepare optional network allowlist entries
    allowlist_entries: list[str] | None = None
    if args.network_allowlist:
        try:
            with open(args.network_allowlist, "r") as f:
                allowlist_entries = [line.strip() for line in f if line.strip() and not line.strip().startswith("#")]
        except Exception as e:
            print(f"Warning: Failed to read network allowlist file: {e}")

    # 2. Run scans for each project
    all_scans = []
    for project in projects:
        scan_result = Workflow.run_project_scan(project, network_allowlist=allowlist_entries)
        all_scans.append(scan_result)

    # 3. Generate report
    print(f"Generating report to {args.output}...")
    report_generator = ReportGenerator(all_scans, projects, args.output)
    report_generator.generate_report()
    print("Report generation complete.")

if __name__ == "__main__":
    main()
