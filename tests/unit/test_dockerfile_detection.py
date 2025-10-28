"""
Test Dockerfile detection in the workflow.
"""
import tempfile
from pathlib import Path

import pytest
from src.models.project import Project
from src.orchestration.workflow import Workflow


def test_dockerfile_detection_with_dockerfile():
    """Test that Dockerfile is detected when present."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create a Dockerfile
        dockerfile = Path(tmpdir) / "Dockerfile"
        dockerfile.write_text("FROM python:3.11\nRUN pip install flask\nCMD ['python', 'app.py']")
        
        # Create a project
        project = Project(
            url="https://github.com/test/repo",
            name="test-project",
            language="Python"
        )
        
        # Run detection
        Workflow._detect_dockerfile(project, Path(tmpdir))
        
        # Assert Dockerfile was detected
        assert project.dockerfile_present is True
        assert project.container_capable is True


def test_dockerfile_detection_without_dockerfile():
    """Test that project without Dockerfile is marked correctly."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Don't create a Dockerfile
        
        # Create a project
        project = Project(
            url="https://github.com/test/repo",
            name="test-project",
            language="Python"
        )
        
        # Run detection
        Workflow._detect_dockerfile(project, Path(tmpdir))
        
        # Assert Dockerfile was not detected
        assert project.dockerfile_present is False


def test_dockerfile_detection_with_lowercase():
    """Test that lowercase 'dockerfile' is also detected."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create a lowercase dockerfile
        dockerfile = Path(tmpdir) / "dockerfile"
        dockerfile.write_text("FROM node:18\nRUN npm install\nCMD ['node', 'server.js']")
        
        # Create a project
        project = Project(
            url="https://github.com/test/repo",
            name="test-project",
            language="JavaScript"
        )
        
        # Run detection
        Workflow._detect_dockerfile(project, Path(tmpdir))
        
        # Assert dockerfile was detected
        assert project.dockerfile_present is True
        assert project.container_capable is True


def test_should_run_dast_with_dockerfile():
    """Test that DAST is enabled when Dockerfile is detected."""
    project = Project(
        url="https://github.com/test/repo",
        name="test-project",
        language="Python",
        dockerfile_present=True,
        container_capable=True
    )
    
    assert Workflow._should_run_dast_scan(project) is True


def test_should_run_dast_without_dockerfile_github():
    """Test that DAST is NOT enabled for GitHub repos without Dockerfile."""
    project = Project(
        url="https://github.com/test/repo",
        name="test-project",
        language="Python",
        dockerfile_present=False,
        container_capable=False
    )
    
    assert Workflow._should_run_dast_scan(project) is False


def test_should_run_dast_with_http_url():
    """Test that DAST is enabled for direct HTTP URLs."""
    project = Project(
        url="http://localhost:8080",
        name="test-app",
        language="Python"
    )
    
    assert Workflow._should_run_dast_scan(project) is True
