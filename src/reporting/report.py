import os
from collections import Counter
from datetime import datetime

from jinja2 import Environment, FileSystemLoader
from src.models.project import Project
from src.models.scan import Scan


class ReportGenerator:
    """
    Generates a comprehensive Markdown report from scan results using a Jinja2 template.
    """

    def __init__(
        self, scans: list[Scan], projects: list[Project], output_filepath: str
    ):
        self.scans = scans
        self.projects = projects
        self.output_filepath = output_filepath
        self.template_dir = os.path.join(os.path.dirname(__file__), "templates")
        self.env = Environment(loader=FileSystemLoader(self.template_dir))
        self.template = self.env.get_template("report.md")

    def generate_report(self) -> None:
        """Generates the Markdown report and writes it to the specified output file."""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        total_projects = len(self.projects)
        total_findings = sum(len(scan.results) for scan in self.scans)

        # Map project IDs to project objects for easier lookup in the template
        project_map = {str(p.id): p for p in self.projects}

        # Calculate statistics
        severity_stats = self._calculate_severity_stats()
        tool_stats = self._calculate_tool_stats()
        language_stats = self._calculate_language_stats()

        # Prepare data for the template
        scans_list: list[dict[str, object]] = []
        template_data: dict[str, object] = {
            "timestamp": timestamp,
            "total_projects": total_projects,
            "total_findings": total_findings,
            "severity_stats": severity_stats,
            "tool_stats": tool_stats,
            "language_stats": language_stats,
            "scans": scans_list,
        }

        for scan in self.scans:
            project = project_map.get(str(scan.projectId))
            if not project:
                continue

            scans_list.append(
                {
                    "scan_id": scan.id,
                    "project_name": project.name,
                    "project_url": project.url,
                    "project_language": project.language,
                    "project_description": project.description,
                    "status": scan.status,
                    "findings_count": len(scan.results),
                    "findings": [
                        {
                            "severity": f.severity,
                            "tool": f.tool,
                            "description": f.description,
                            "filePath": f.filePath,
                            "lineNumber": f.lineNumber,
                        }
                        for f in scan.results
                    ],
                }
            )

        rendered_report = self.template.render(template_data)

        with open(self.output_filepath, "w") as f:
            f.write(rendered_report)

        print(f"✅ Report successfully generated: {self.output_filepath}")

    def _calculate_severity_stats(self) -> dict[str, int]:
        """Calculate statistics by finding severity."""
        severity_counter: Counter[str] = Counter()
        for scan in self.scans:
            for finding in scan.results:
                severity_counter[finding.severity.lower()] += 1
        return dict(severity_counter)

    def _calculate_tool_stats(self) -> dict[str, int]:
        """Calculate statistics by scanning tool."""
        tool_counter: Counter[str] = Counter()
        for scan in self.scans:
            for finding in scan.results:
                tool_counter[finding.tool] += 1
        return dict(tool_counter)

    def _calculate_language_stats(self) -> dict[str, int]:
        """Calculate statistics by programming language."""
        language_counter: Counter[str] = Counter()
        project_map = {str(p.id): p for p in self.projects}

        for scan in self.scans:
            project = project_map.get(str(scan.projectId))
            if project and project.language:
                language_counter[project.language] += len(scan.results)

        return dict(language_counter)
