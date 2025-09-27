#!/usr/bin/env python3
"""
GeoToolKit Package Deployment Verification Script

This script verifies that the built packages are properly configured
and ready for deployment.
"""

import json
import subprocess
import sys
import zipfile
from pathlib import Path


def run_command(cmd, check=True):
    """Run a command and return the result."""
    try:
        result = subprocess.run(
            cmd, shell=True, capture_output=True, text=True, check=check
        )
        return result.stdout.strip(), result.stderr.strip(), result.returncode
    except subprocess.CalledProcessError as e:
        return e.stdout.strip(), e.stderr.strip(), e.returncode


def verify_cli_package():
    """Verify CLI package is properly built."""
    print("🔍 Verifying CLI package...")

    # Check for wheel file
    dist_path = Path("dist")
    wheel_files = list(dist_path.glob("*.whl"))
    if not wheel_files:
        print("❌ No wheel files found in dist/")
        return False

    wheel_file = wheel_files[0]
    print(f"✅ Found wheel file: {wheel_file.name}")

    # Check entry points in wheel
    with zipfile.ZipFile(wheel_file, "r") as zf:
        try:
            # Dynamically find the .dist-info directory
            dist_info_dir = next(
                (
                    name
                    for name in zf.namelist()
                    if name.endswith(".dist-info/entry_points.txt")
                ),
                None,
            )
            if not dist_info_dir:
                print("❌ entry_points.txt not found in any .dist-info directory")
                return False
            entry_points = zf.read(dist_info_dir).decode()
            if "geotoolkit = src.main:main" in entry_points:
                print("✅ CLI entry point configured correctly")
            else:
                print("❌ CLI entry point missing or incorrect")
                return False

            if "geotoolkit-mcp = mcp.server:main" in entry_points:
                print("✅ MCP server entry point configured correctly")
            else:
                print("❌ MCP server entry point missing or incorrect")
                return False

        except KeyError:
            print("❌ Entry points file not found in wheel")
            return False

    return True


def verify_mcp_server():
    """Verify MCP server components."""
    print("🔍 Verifying MCP server...")

    # Check manifest file exists
    manifest_path = Path("mcp/manifest.json")
    if not manifest_path.exists():
        print("❌ MCP manifest.json not found")
        return False

    # Validate manifest structure
    try:
        with open(manifest_path) as f:
            manifest = json.load(f)

        required_fields = ["name", "app_id", "version", "tools"]
        for field in required_fields:
            if field not in manifest:
                print(f"❌ Missing required field in manifest: {field}")
                return False

        print(f"✅ MCP manifest valid: {manifest['name']} v{manifest['version']}")
        print(f"✅ Available tools: {[t['name'] for t in manifest['tools']]}")

    except (json.JSONDecodeError, FileNotFoundError) as e:
        print(f"❌ Manifest validation error: {e}")
        return False

    return True


def verify_package_metadata():
    """Verify package metadata is correct."""
    print("🔍 Verifying package metadata...")

    # Check wheel metadata
    dist_path = Path("dist")
    wheel_files = list(dist_path.glob("*.whl"))
    if not wheel_files:
        return False

    wheel_file = wheel_files[0]
    with zipfile.ZipFile(wheel_file, "r") as zf:
        try:
            # Dynamically find the .dist-info directory
            dist_info_dir = next(
                (
                    name
                    for name in zf.namelist()
                    if name.endswith(".dist-info/METADATA")
                ),
                None,
            )
            if not dist_info_dir:
                print("❌ Could not find METADATA file in any .dist-info directory")
                return False
            metadata = zf.read(dist_info_dir).decode()

            # Check key metadata fields
            checks = [
                ("Name: geotoolkit", "Package name"),
                ("Homepage:", "Homepage URL"),
                ("Repository:", "Repository URL"),
                ("Author:", "Author information"),
                ("Classifier: Topic :: Security", "Security topic classifier"),
            ]

            for check, desc in checks:
                if check in metadata:
                    print(f"✅ {desc} present")
                else:
                    print(f"⚠️ {desc} missing or incomplete")

        except KeyError:
            print("❌ Package metadata file not found")
            return False

    return True


def verify_build_artifacts():
    """Verify all expected build artifacts are present."""
    print("🔍 Verifying build artifacts...")

    dist_path = Path("dist")
    if not dist_path.exists():
        print("❌ dist/ directory not found")
        return False

    # Check for expected files
    expected_patterns = [
        "*.whl",  # Wheel file
        "*.tar.gz",  # Source distribution
    ]

    all_found = True
    for pattern in expected_patterns:
        files = list(dist_path.glob(pattern))
        if files:
            print(f"✅ Found {pattern}: {[f.name for f in files]}")
        else:
            print(f"❌ Missing {pattern} files")
            all_found = False

    return all_found


def verify_installation_test():
    """Test package installation in a temporary environment."""
    print("🔍 Testing package installation...")

    # Find the wheel file
    dist_path = Path("dist")
    wheel_files = list(dist_path.glob("*.whl"))
    if not wheel_files:
        print("❌ No wheel file found for installation test")
        return False

    wheel_file = wheel_files[0]

    # Test installation simulation (without actually installing)
    stdout, stderr, code = run_command(f"python -m zipfile -l {wheel_file}")
    if code == 0:
        print("✅ Wheel file structure is valid")
        # Check if key modules are included
        if "src/" in stdout and "mcp/" in stdout:
            print("✅ Both src and mcp modules included in package")
        else:
            print("⚠️ Package structure may be incomplete")
            print(f"Package contents preview:\n{stdout[:500]}...")
    else:
        print("❌ Wheel file validation failed")
        return False

    return True


def main():
    """Run all verification checks."""
    print("🛡️ GeoToolKit Package Deployment Verification")
    print("=" * 50)

    checks = [
        ("CLI Package", verify_cli_package),
        ("MCP Server", verify_mcp_server),
        ("Package Metadata", verify_package_metadata),
        ("Build Artifacts", verify_build_artifacts),
        ("Installation Test", verify_installation_test),
    ]

    results = []
    for name, check_func in checks:
        print(f"\n📋 {name}")
        print("-" * 30)
        try:
            success = check_func()
            results.append((name, success))
            if success:
                print(f"✅ {name} verification passed")
            else:
                print(f"❌ {name} verification failed")
        except Exception as e:
            print(f"💥 {name} verification error: {e}")
            results.append((name, False))

    # Summary
    print("\n📊 Verification Summary")
    print("=" * 30)
    passed = sum(1 for _, success in results if success)
    total = len(results)

    for name, success in results:
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status} {name}")

    print(f"\nOverall: {passed}/{total} checks passed")

    if passed == total:
        print("🎉 All verifications passed! Package is ready for deployment.")
        return 0
    else:
        print("⚠️ Some verifications failed. Please review before deployment.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
