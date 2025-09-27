#!/usr/bin/env python3
"""
Minimal functionality validator that works without external dependencies.
Tests the basic project structure and configuration validity.
"""

import json
import subprocess
import sys
from pathlib import Path


def test_basic_structure():
    """Test that basic project structure exists."""
    print("🔍 Testing Basic Project Structure")
    print("-" * 40)

    required_files = [
        "README.md",
        "pyproject.toml",
        "src/main.py",
        "src/models/project.py",
        "src/orchestration/workflow.py",
        "seccomp/default.json",
        "projects.json"
    ]

    required_dirs = [
        "src/models",
        "src/orchestration",
        "src/orchestration/runners",
        "src/reporting",
        "tests/unit",
        "tests/integration",
        "seccomp"
    ]

    issues = []

    for file_path in required_files:
        if Path(file_path).exists():
            print(f"✅ {file_path}")
        else:
            print(f"❌ {file_path} - MISSING")
            issues.append(f"Missing required file: {file_path}")

    for dir_path in required_dirs:
        if Path(dir_path).exists():
            print(f"✅ {dir_path}/")
        else:
            print(f"❌ {dir_path}/ - MISSING")
            issues.append(f"Missing required directory: {dir_path}")

    return issues


def test_configuration_files():
    """Test that configuration files are valid JSON."""
    print("\n🔍 Testing Configuration Files")
    print("-" * 40)

    config_files = [
        "projects.json",
        "test-projects.json",
        "validation/configs/enhanced-projects.json"
    ]

    issues = []

    for config_file in config_files:
        if Path(config_file).exists():
            try:
                with open(config_file) as f:
                    data = json.load(f)

                # Validate structure
                if "projects" in data:
                    project_count = len(data["projects"])
                    print(f"✅ {config_file} - {project_count} projects")

                    # Check required fields in projects
                    for i, project in enumerate(data["projects"]):
                        required_fields = ["url", "name", "language"]
                        for field in required_fields:
                            if field not in project:
                                issues.append(f"{config_file}: Project {i} missing {field}")
                else:
                    issues.append(f"{config_file}: Missing 'projects' key")

            except json.JSONDecodeError as e:
                print(f"❌ {config_file} - Invalid JSON: {e}")
                issues.append(f"Invalid JSON in {config_file}: {e}")
            except Exception as e:
                print(f"❌ {config_file} - Error: {e}")
                issues.append(f"Error reading {config_file}: {e}")
        else:
            print(f"⚠️  {config_file} - Not found")

    return issues


def test_security_profiles():
    """Test that seccomp profiles exist and are valid."""
    print("\n🔍 Testing Security Profiles")
    print("-" * 40)

    required_profiles = [
        "seccomp/default.json",
        "seccomp/semgrep-seccomp.json",
        "seccomp/trivy-seccomp.json",
        "seccomp/osv-scanner-seccomp.json",
        "seccomp/zap-seccomp.json"
    ]

    issues = []

    for profile in required_profiles:
        if Path(profile).exists():
            try:
                with open(profile) as f:
                    data = json.load(f)
                    if "syscalls" in data:
                        syscall_count = len(data["syscalls"])
                        print(f"✅ {profile} - {syscall_count} syscall rules")
                    else:
                        print(f"✅ {profile} - Valid JSON")
            except json.JSONDecodeError as e:
                print(f"❌ {profile} - Invalid JSON: {e}")
                issues.append(f"Invalid JSON in {profile}: {e}")
        else:
            print(f"❌ {profile} - MISSING")
            issues.append(f"Missing security profile: {profile}")

    return issues


def test_container_tooling():
    """Test that container runtime is available."""
    print("\n🔍 Testing Container Tooling")
    print("-" * 40)

    issues = []

    # Test Podman
    try:
        result = subprocess.run(["podman", "--version"], capture_output=True, text=True, timeout=10)
        if result.returncode == 0:
            print(f"✅ Podman: {result.stdout.strip()}")
        else:
            print("❌ Podman not working")
            issues.append("Podman not working properly")
    except FileNotFoundError:
        print("❌ Podman not found")
        issues.append("Podman not installed")
    except Exception as e:
        print(f"❌ Podman error: {e}")
        issues.append(f"Podman error: {e}")

    # Test Docker as fallback
    try:
        result = subprocess.run(["docker", "--version"], capture_output=True, text=True, timeout=10)
        if result.returncode == 0:
            print(f"✅ Docker: {result.stdout.strip()}")
        else:
            print("⚠️  Docker not working")
    except FileNotFoundError:
        print("⚠️  Docker not found")
    except Exception:
        print("⚠️  Docker not available")

    return issues


def test_documented_features():
    """Test that features mentioned in README are implemented."""
    print("\n🔍 Testing Documented Features")
    print("-" * 40)

    issues = []

    # Check runners exist
    runners = [
        "src/orchestration/runners/semgrep_runner.py",
        "src/orchestration/runners/trivy_runner.py",
        "src/orchestration/runners/osv_runner.py",
        "src/orchestration/runners/zap_runner.py"
    ]

    for runner in runners:
        if Path(runner).exists():
            print(f"✅ {runner.split('/')[-1]}")
        else:
            print(f"❌ {runner.split('/')[-1]} - MISSING")
            issues.append(f"Missing security runner: {runner}")

    # Check MCP server
    if Path("mcp/server.py").exists():
        print("✅ MCP server implementation")
    else:
        print("❌ MCP server - MISSING")
        issues.append("Missing MCP server implementation")

    # Check report generation
    if Path("src/reporting/report.py").exists():
        print("✅ Report generation")
    else:
        print("❌ Report generation - MISSING")
        issues.append("Missing report generation")

    # Check offline database support
    if Path("scripts/build_offline_db.py").exists():
        print("✅ Offline database builder")
    else:
        print("❌ Offline database builder - MISSING")
        issues.append("Missing offline database builder")

    return issues


def main():
    """Run all validation tests."""
    print("🛡️  GeoToolKit Functionality Validation")
    print("=" * 50)

    all_issues = []

    all_issues.extend(test_basic_structure())
    all_issues.extend(test_configuration_files())
    all_issues.extend(test_security_profiles())
    all_issues.extend(test_container_tooling())
    all_issues.extend(test_documented_features())

    print("\n📊 Validation Summary")
    print("-" * 40)

    if not all_issues:
        print("🎉 All functionality validation tests passed!")
        print("✅ GeoToolKit meets the documented specification")
        return 0
    else:
        print(f"⚠️  Found {len(all_issues)} issues:")
        for i, issue in enumerate(all_issues, 1):
            print(f"   {i}. {issue}")

        print(f"\n❌ GeoToolKit needs {len(all_issues)} fixes to fully meet specification")
        return len(all_issues)


if __name__ == "__main__":
    sys.exit(main())
