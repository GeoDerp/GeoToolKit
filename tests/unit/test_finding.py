import pytest
from uuid import UUID
from pydantic import ValidationError
from src.models.finding import Finding

def test_finding_creation_invalid_severity():
    with pytest.raises(ValidationError): # Pydantic will raise ValidationError
        Finding(
            tool="Semgrep",
            description="Issue",
            severity="Unknown",
            filePath="file.py",
            lineNumber=1,
            complianceMappings=[]
        )