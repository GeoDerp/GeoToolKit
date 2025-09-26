"""Unit tests for the Finding model.

Tests validation of Finding model fields and ensures proper error handling
for invalid input data.
"""

import pytest
from pydantic import ValidationError
from src.models.finding import Finding


def test_finding_creation_invalid_severity():
    """Test that Finding raises ValidationError for invalid severity values."""
    with pytest.raises(ValidationError):  # Pydantic will raise ValidationError
        Finding(
            tool="Semgrep",
            description="Issue",
            severity="Unknown",  # Invalid severity value
            filePath="file.py",
            lineNumber=1,
            complianceMappings=[],
        )
