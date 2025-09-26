import pytest
from uuid import UUID
from datetime import datetime
from src.models.scan import Scan
from src.models.finding import Finding

def test_scan_creation():
    project_id = UUID("12345678-1234-5678-1234-567812345678")
    status = "pending"
    scan = Scan(projectId=project_id, status=status)

    assert isinstance(scan.id, UUID)
    assert scan.projectId == project_id
    assert isinstance(scan.timestamp, datetime)
    assert scan.status == status
    assert scan.results == []

def test_scan_creation_with_findings():
    project_id = UUID("12345678-1234-5678-1234-567812345678")
    status = "completed"
    finding = Finding(
        tool="Semgrep",
        description="Hardcoded password",
        severity="High",
        filePath="src/main.py",
        lineNumber=10,
        complianceMappings=["OWASP-Top-10-2021-A07"]
    )
    scan = Scan(projectId=project_id, status=status, results=[finding])

    assert len(scan.results) == 1
    assert scan.results[0].tool == "Semgrep"

def test_scan_creation_invalid_project_id():
    with pytest.raises(Exception): # Pydantic will raise ValidationError
        Scan(projectId="invalid-uuid", status="pending")
