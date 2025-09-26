"""Unit tests for the Project model.

Tests validation of Project model fields and ensures proper error handling
for invalid input data.
"""

import pytest
from pydantic import ValidationError
from src.models.project import Project


def test_project_creation_invalid_url():
    """Test that Project raises ValidationError for invalid URL values."""
    # Test with a completely malformed input that should still fail validation
    with pytest.raises(ValidationError):  # Pydantic will raise ValidationError
        Project(
            url="",  # Empty string should fail
            name="test-repo",
            language="Python",
            description="Test project",
        )
