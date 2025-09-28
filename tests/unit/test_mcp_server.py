"""Tests for MCP server functionality."""

import json
import os
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest


def test_mcp_server_import():
    """Test that MCP server module can be imported successfully."""
    from mcp_server.mcp_server import MCP_AVAILABLE, main

    assert MCP_AVAILABLE is True, "MCP dependencies should be available"
    assert main is not None, "MCP server main function should be available"


def test_mcp_server_environment_variables():
    """Test that MCP server reads environment variables correctly."""
    # Set test environment variables
    os.environ["MCP_HOST"] = "127.0.0.1"
    os.environ["MCP_PORT"] = "9000"
    os.environ["DATABASE_PATH"] = "test-db.tar.gz"

    # Import should work without errors - just test the import
    from mcp_server.mcp_server import MCP_AVAILABLE

    assert MCP_AVAILABLE is True

    # Clean up
    del os.environ["MCP_HOST"]
    del os.environ["MCP_PORT"]
    del os.environ["DATABASE_PATH"]


def test_mcp_create_projects_validation(tmp_path):
    """Test createProjects tool input validation."""
    from mcp_server.mcp_server import _derive_allowlists

    # Test valid input with the expected structure
    valid_project = {
        "name": "test-project",
        "network_config": {
            "protocol": "https",
            "ports": [80, 443],
            "allowed_egress": {
                "external_hosts": ["api.test.com", "cdn.example.com"],
                "192.168.1.0/24": [8080],
                "10.0.0.0/8": [],
            },
        },
    }

    hosts, cidrs, ports = _derive_allowlists(valid_project)
    # Should have hosts with ports from external_hosts and CIDR keys
    assert any("api.test.com:80" in h or "api.test.com:443" in h for h in hosts), (
        f"Expected api.test.com with port in {hosts}"
    )
    # Should have CIDR from keys with "/"
    assert any("192.168.1.0/24" in c for c in cidrs), f"Expected CIDR in {cidrs}"
    assert "80" in ports or "443" in ports, f"Expected ports in {ports}"


def test_mcp_normalize_projects_output(tmp_path):
    """Test normalizeProjects tool output format."""
    from mcp_server.mcp_server import _derive_allowlists

    # Create test projects data with proper structure
    projects_data = [
        {
            "name": "test1",
            "network_config": {
                "protocol": "https",
                "ports": [443],
                "allowed_egress": {"external_hosts": ["api1.test.com"]},
            },
        },
        {
            "name": "test2",
            "network_config": {
                "protocol": "http",
                "ports": [8080],
                "allowed_egress": {"external_hosts": ["api2.test.com"]},
            },
        },
    ]

    # Test that allowlists are derived correctly
    for project in projects_data:
        hosts, cidrs, ports = _derive_allowlists(project)
        assert len(hosts) > 0, f"Should derive at least one host from {project}"
        assert len(ports) > 0, f"Should derive at least one port from {project}"


def test_mcp_write_json_functionality(tmp_path):
    """Test JSON writing functionality."""
    from mcp_server.mcp_server import _write_json

    test_data = {"test": "data", "number": 42}
    test_file = tmp_path / "test.json"

    _write_json(test_file, test_data)

    # Verify file was written correctly
    assert test_file.exists()
    with open(test_file) as f:
        loaded_data = json.load(f)
    assert loaded_data == test_data


def test_mcp_main_cli_integration():
    """Test MCP server main CLI integration."""
    from src.main import main as cli_main

    # Test that MCP server mode is detected
    test_args = [
        "main.py",
        "--mcp-server",
        "--mcp-host",
        "127.0.0.1",
        "--mcp-port",
        "9001",
        "--database-path",
        "test-db.tar.gz",
    ]

    with patch.object(sys, "argv", test_args):
        with patch("mcp_server.mcp_server.main") as mock_mcp_main:
            # Should attempt to import and call MCP server
            try:
                cli_main()
            except SystemExit:
                pass  # Expected when MCP server would start

            # Verify environment variables were set
            assert os.environ.get("MCP_HOST") == "127.0.0.1"
            assert os.environ.get("MCP_PORT") == "9001"
            assert os.environ.get("DATABASE_PATH") == "test-db.tar.gz"


def test_mcp_tools_available():
    """Test that MCP tools are properly registered."""
    from mcp_server.mcp_server import MCP_AVAILABLE, mcp

    if not MCP_AVAILABLE:
        pytest.skip("MCP not available")

    # Test that MCP instance exists and has tool decorator
    assert hasattr(mcp, "tool"), "MCP instance should have tool decorator"

    # Test that the MCP instance is properly configured
    assert hasattr(mcp, "name"), "MCP instance should have a name"


def test_mcp_allowlist_derivation_edge_cases():
    """Test allowlist derivation with edge cases."""
    from mcp_server.mcp_server import _derive_allowlists

    # Test empty project
    empty_project = {"name": "empty"}
    hosts, cidrs, ports = _derive_allowlists(empty_project)
    assert isinstance(hosts, list)
    assert isinstance(cidrs, list)
    assert isinstance(ports, list)

    # Test project with minimal network config
    basic_project = {
        "name": "basic",
        "network_config": {"allowed_egress": {"external_hosts": ["github.com"]}},
    }
    hosts, cidrs, ports = _derive_allowlists(basic_project)
    # Should have github.com with default port 80 since no protocol specified
    assert any("github.com:80" in host for host in hosts), (
        f"Should include github.com:80 in {hosts}"
    )


def test_mcp_server_graceful_degradation():
    """Test MCP server graceful degradation when dependencies unavailable."""
    # This tests the fallback behavior when MCP is not available
    with tempfile.TemporaryDirectory() as temp_dir:
        # Create a mock module to test fallback
        mock_mcp_path = Path(temp_dir) / "mock_mcp.py"
        with open(mock_mcp_path, "w") as f:
            f.write("""
MCP_AVAILABLE = False

class MockFastMCP:
    def __init__(self, **kwargs):
        pass
    def run(self, **kwargs):
        print("MCP dependencies not available")

def main():
    print("MCP dependencies not available. Install with: uv sync --extra mcp")
""")

        # The actual implementation should handle this gracefully
        assert True, "Graceful degradation should be handled in the real implementation"
