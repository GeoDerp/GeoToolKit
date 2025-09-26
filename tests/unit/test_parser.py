import pytest
import json
from src.orchestration.parser import OutputParser
from src.models.finding import Finding

# Mock JSON outputs for each tool
MOCK_SEMGREP_JSON = '''
{
  "results": [
    {
      "check_id": "python.lang.security.audit.non-literal-exec.non-literal-exec",
      "path": "src/main.py",
      "start": {"line": 10, "col": 5},
      "end": {"line": 10, "col": 20},
      "extra": {
        "message": "Detected a non-literal argument to an execution function.",
        "severity": "ERROR"
      }
    },
    {
      "check_id": "python.lang.maintainability.useless-expression.useless-expression",
      "path": "src/utils.py",
      "start": {"line": 5, "col": 1},
      "end": {"line": 5, "col": 10},
      "extra": {
        "message": "This expression has no effect.",
        "severity": "INFO"
      }
    }
  ]
}
'''

MOCK_TRIVY_JSON = '''
{
  "Results": [
    {
      "Target": "python:3.9-slim-buster",
      "Vulnerabilities": [
        {
          "VulnerabilityID": "CVE-2023-1234",
          "PkgName": "openssl",
          "InstalledVersion": "1.1.1n-0+deb11u5",
          "Severity": "HIGH",
          "Description": "OpenSSL vulnerability description.",
          "PrimaryURL": "https://cve.mitre.org/cgi-bin/cvename.cgi?name=CVE-2023-1234"
        }
      ],
      "Misconfigurations": [
        {
          "ID": "AVD-ID-0001",
          "Title": "Container running as root",
          "Description": "Ensure that containers are not run with the root user.",
          "Severity": "CRITICAL",
          "Filepath": "Dockerfile",
          "StartLine": 1
        }
      ]
    }
  ]
}
'''

MOCK_OSV_SCANNER_JSON = '''
{
  "results": [
    {
      "source": {"path": "requirements.lock"},
      "packages": [
        {
          "package": {"name": "requests", "version": "2.25.1"},
          "vulnerabilities": [
            {
              "id": "OSV-2023-567",
              "summary": "Requests library vulnerable to header injection.",
              "details": "Detailed explanation of the vulnerability.",
              "severity": "HIGH"
            }
          ]
        }
      ]
    }
  ]
}
'''

MOCK_OWASP_ZAP_JSON = '''
{
  "@version": "2.11.1",
  "site": [
    {
      "@name": "http://localhost:8080",
      "alerts": [
        {
          "pluginid": "40012",
          "alertRef": "40012",
          "alert": "Cross Site Scripting (Reflected)",
          "riskdesc": "High (Medium)",
          "desc": "A reflected XSS vulnerability was found.",
          "solution": "Sanitize all user input.",
          "cweid": "79",
          "instances": [
            {
              "uri": "http://localhost:8080/search?query=test<script>alert(1)</script>",
              "method": "GET",
              "param": "query",
              "evidence": "<script>alert(1)</script>"
            }
          ]
        }
      ]
    }
  ]
}
'''

def test_parse_semgrep_json():
    findings = OutputParser.parse_semgrep_json(MOCK_SEMGREP_JSON)
    assert len(findings) == 2

    f1 = findings[0]
    assert isinstance(f1, Finding)
    assert f1.tool == "Semgrep"
    assert "non-literal-exec" in f1.description
    assert f1.severity == "High"
    assert f1.filePath == "src/main.py"
    assert f1.lineNumber == 10

    f2 = findings[1]
    assert f2.severity == "Low"
    assert f2.filePath == "src/utils.py"
    assert f2.lineNumber == 5

def test_parse_trivy_json():
    findings = OutputParser.parse_trivy_json(MOCK_TRIVY_JSON)
    assert len(findings) == 2 # 1 vulnerability, 1 misconfiguration

    f1 = findings[0]
    assert isinstance(f1, Finding)
    assert f1.tool == "Trivy"
    assert "CVE-2023-1234" in f1.description
    assert f1.severity == "High"
    assert f1.filePath == "python:3.9-slim-buster"
    assert f1.lineNumber is None

    f2 = findings[1]
    assert isinstance(f2, Finding)
    assert f2.tool == "Trivy"
    assert "AVD-ID-0001" in f2.description
    assert f2.severity == "High"
    assert f2.filePath == "Dockerfile"
    assert f2.lineNumber == 1

def test_parse_osv_scanner_json():
    findings = OutputParser.parse_osv_scanner_json(MOCK_OSV_SCANNER_JSON)
    assert len(findings) == 1

    f1 = findings[0]
    assert isinstance(f1, Finding)
    assert f1.tool == "OSV-Scanner"
    assert "OSV-2023-567" in f1.description
    assert f1.severity == "Medium"
    assert f1.filePath == "requirements.lock"
    assert f1.lineNumber is None

def test_parse_owasp_zap_json():
    findings = OutputParser.parse_owasp_zap_json(MOCK_OWASP_ZAP_JSON)
    assert len(findings) == 1

    f1 = findings[0]
    assert isinstance(f1, Finding)
    assert f1.tool == "OWASP ZAP"
    assert "Cross Site Scripting (Reflected)" in f1.description
    assert f1.severity == "High"
    assert f1.filePath == "http://localhost:8080/search?query=test<script>alert(1)</script>"
    assert f1.lineNumber is None
    assert "CWE-79" in f1.complianceMappings
