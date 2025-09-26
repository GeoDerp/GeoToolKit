import json

from src.models.finding import Finding, Severity


class OutputParser:
    """
    Parses the JSON output from various security scanning tools and converts them into a standardized Finding object.
    """

    @staticmethod
    def parse_semgrep_json(json_output: str) -> list[Finding]:
        findings: list[Finding] = []
        data = json.loads(json_output)
        for result in data.get("results", []):
            check_id = result.get("check_id", "N/A")
            path = result.get("path", "N/A")
            start_line = result.get("start", {}).get("line", None)
            end_line = result.get("end", {}).get("line", None)
            extra = result.get("extra", {})
            message = extra.get("message", "No description provided.")
            severity_str = extra.get("severity", "UNKNOWN").capitalize()

            # Map Semgrep severity to our standardized severity levels
            if severity_str == "Error":
                severity = Severity.HIGH
            elif severity_str == "Warning":
                severity = Severity.MEDIUM
            elif severity_str == "Info":
                severity = Severity.LOW
            else:
                severity = Severity.UNKNOWN

            findings.append(
                Finding(
                    tool="Semgrep",
                    description=f"{check_id}: {message}",
                    severity=severity,
                    filePath=path,
                    lineNumber=start_line if start_line is not None else end_line,
                    complianceMappings=[]  # Semgrep doesn't directly provide compliance mappings in default JSON
                )
            )
        return findings

    @staticmethod
    def parse_trivy_json(json_output: str) -> list[Finding]:
        findings: list[Finding] = []
        data = json.loads(json_output)

        # Trivy can have different report types (e.g., 'Vulnerabilities', 'Misconfigurations', 'Secrets')
        # This parser focuses on 'Vulnerabilities' and 'Misconfigurations' for now.
        # It iterates through 'Results' which can contain multiple scanned targets (e.g., image, filesystem)
        for result_block in data.get("Results", []):
            target = result_block.get("Target", "N/A")

            # Parse Vulnerabilities
            for vulnerability in result_block.get("Vulnerabilities", []):
                vulnerability_id = vulnerability.get("VulnerabilityID", "N/A")
                pkg_name = vulnerability.get("PkgName", "N/A")
                installed_version = vulnerability.get("InstalledVersion", "N/A")
                severity_str = vulnerability.get("Severity", "UNKNOWN").capitalize()
                description = vulnerability.get("Description", "No description provided.")

                # Map Trivy severity
                if severity_str == "Critical":
                    severity = Severity.HIGH
                elif severity_str == "High":
                    severity = Severity.HIGH
                elif severity_str == "Medium":
                    severity = Severity.MEDIUM
                elif severity_str == "Low":
                    severity = Severity.LOW
                else:
                    severity = Severity.UNKNOWN

                findings.append(
                    Finding(
                        tool="Trivy",
                        description=f"{vulnerability_id} in {pkg_name}@{installed_version}: {description}",
                        severity=severity,
                        filePath=target,  # Trivy's target can be a file path or image name
                        lineNumber=None,  # Trivy vulnerabilities are package-level, no specific line number
                        complianceMappings=[]  # Trivy doesn't directly provide compliance mappings in default JSON
                    )
                )

            # Parse Misconfigurations
            for misconfiguration in result_block.get("Misconfigurations", []):
                policy_id = misconfiguration.get("ID", "N/A")
                title = misconfiguration.get("Title", "N/A")
                description = misconfiguration.get("Description", "No description provided.")
                severity_str = misconfiguration.get("Severity", "UNKNOWN").capitalize()
                filepath = misconfiguration.get("Filepath", "N/A")
                start_line = misconfiguration.get("StartLine", None)

                # Map Trivy severity
                if severity_str == "Critical":
                    severity = Severity.HIGH
                elif severity_str == "High":
                    severity = Severity.HIGH
                elif severity_str == "Medium":
                    severity = Severity.MEDIUM
                elif severity_str == "Low":
                    severity = Severity.LOW
                else:
                    severity = Severity.UNKNOWN

                findings.append(
                    Finding(
                        tool="Trivy",
                        description=f"{policy_id}: {title} - {description}",
                        severity=severity,
                        filePath=filepath,
                        lineNumber=start_line,
                        complianceMappings=[]  # Trivy doesn't directly provide compliance mappings in default JSON
                    )
                )
        return findings

    @staticmethod
    def parse_osv_scanner_json(json_output: str) -> list[Finding]:
        findings: list[Finding] = []
        data = json.loads(json_output)

        for result in data.get("results", []):
            source = result.get("source", {})
            source_path = source.get("path", "N/A")

            for package_with_vulns in result.get("packages", []):
                package = package_with_vulns.get("package", {})
                package_name = package.get("name", "N/A")
                package_version = package.get("version", "N/A")

                for vulnerability_data in package_with_vulns.get("vulnerabilities", []):
                    osv_id = vulnerability_data.get("id", "N/A")
                    summary = vulnerability_data.get("summary", "No summary provided.")
                    details = vulnerability_data.get("details", "No details provided.")
                    # OSV-Scanner often provides CVSS, but a direct 'severity' string might need mapping
                    # For simplicity, we'll default to Medium. A more robust solution would parse CVSS scores.
                    severity = Severity.MEDIUM

                    # OSV-Scanner doesn't directly provide line numbers or specific file paths for vulnerabilities
                    # as it's typically package-level. The source_path is the lockfile/SBOM.
                    findings.append(
                        Finding(
                            tool="OSV-Scanner",
                            description=f"{osv_id} in {package_name}@{package_version}: {summary}. Details: {details}",
                            severity=severity,
                            filePath=source_path,
                            lineNumber=None,
                            complianceMappings=[]  # OSV-Scanner doesn't directly provide compliance mappings
                        )
                    )
        return findings

    @staticmethod
    def parse_owasp_zap_json(json_output: str) -> list[Finding]:
        """Parses OWASP ZAP JSON output into a list of Finding objects."""
        findings: list[Finding] = []
        data = json.loads(json_output)

        for site in data.get("site", []):
            for alert in site.get("alerts", []):
                alert_name = alert.get("alert", "N/A")
                description = alert.get("desc", "No description provided.")
                solution = alert.get("solution", "No solution provided.")
                risk_desc = alert.get("riskdesc", "UNKNOWN").split(" ")[0]  # e.g., "High (Medium)" -> "High"
                cwe_id = alert.get("cweid", "N/A")

                # Map ZAP risk to our standardized severity levels
                if risk_desc == "High":
                    severity = Severity.HIGH
                elif risk_desc == "Medium":
                    severity = Severity.MEDIUM
                elif risk_desc == "Low" or risk_desc == "Informational":
                    severity = Severity.LOW
                else:
                    severity = Severity.UNKNOWN

                # ZAP alerts can have multiple instances
                for instance in alert.get("instances", []):
                    uri = instance.get("uri", "N/A")
                    # ZAP doesn't typically provide line numbers for web vulnerabilities
                    findings.append(
                        Finding(
                            tool="OWASP ZAP",
                            description=f"{alert_name}: {description}. Solution: {solution}",
                            severity=severity,
                            filePath=uri,  # URI is the closest to a 'file path' for web scans
                            lineNumber=None,
                            complianceMappings=[f"CWE-{cwe_id}"] if cwe_id != "N/A" else []
                        )
                    )
        return findings
