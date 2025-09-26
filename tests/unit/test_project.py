import pytest
from uuid import UUID
from pydantic import ValidationError
from src.models.project import Project

def test_project_creation_invalid_url():
    # Test with a completely malformed input that should still fail validation
    with pytest.raises(ValidationError): # Pydantic will raise ValidationError
        Project(url="", name="test-repo")  # Empty string should fail