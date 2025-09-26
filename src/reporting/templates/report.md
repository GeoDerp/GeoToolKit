# Scan Report for GeoToolKit

Generated: {{ timestamp }}

**Total Projects Scanned**: {{ total_projects }}
**Total Findings**: {{ total_findings }}
High Severity: {{ severity_stats.get('high', 0) }}
Medium Severity: {{ severity_stats.get('medium', 0) }}
Low Severity: {{ severity_stats.get('low', 0) }}

## Project Analysis Details

{% for project_scan in scans %}
### Project: {{ project_scan.project_name }}

Repository: {{ project_scan.project_url }}
Language: {{ project_scan.project_language or 'Auto-detected' }}
Description: {{ project_scan.project_description or 'N/A' }}
Scan Status: {{ project_scan.status }}
Security Findings: {{ project_scan.findings_count }}

{% if project_scan.findings %}
#### Security Findings

| Severity | Tool | Issue Description | Location | Line |
|----------|------|-------------------|----------|------|
{% for finding in project_scan.findings %}
| {{ finding.severity }} | `{{ finding.tool }}` | {{ finding.description }} | `{{ finding.filePath }}` | {{ finding.lineNumber if finding.lineNumber is not none else 'N/A' }} |
{% endfor %}
{% else %}
#### No Security Issues Detected
This project passed all security scans without any detected vulnerabilities or security issues.
{% endif %}

---
{% endfor %}

## Scanning Tools Used

- Semgrep - Static Application Security Testing (SAST)
- Trivy - Software Composition Analysis (SCA)
- OSV-Scanner - Open Source Vulnerability Database
- OWASP ZAP - Dynamic Application Security Testing (DAST)

## Risk Assessment

### Overall Security Posture

{% if total_findings == 0 %}
No security vulnerabilities detected across all scanned projects.
{% elif severity_stats.get('high', 0) > 0 %}
High-severity vulnerabilities detected. Immediate remediation required.
{% elif severity_stats.get('medium', 0) > 0 %}
Medium-severity issues found. Remediation recommended within 30 days.
{% else %}
Only low-severity issues detected. Monitor and address as time permits.
{% endif %}

### Recommendations

1. Prioritize high-severity issues first.
2. Keep dependencies updated to latest secure versions.
3. Implement security-focused code review processes.
4. Integrate security scanning into CI/CD pipelines.
5. Provide secure coding training for development teams.
