#!/usr/bin/env python3
"""
Quick GeoToolKit Validation Demo
Demonstrates the validation plan with working components
"""

import json
import subprocess
from datetime import datetime
from pathlib import Path


def run_quick_validation():
    print("🎯 GeoToolKit Quick Validation Demo")
    print("=" * 50)

    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")

    # Step 1: Environment Check
    print("\n📋 Step 1: Environment Verification")
    print("-" * 30)

    env_checks = {}

    # Check Python
    try:
        result = subprocess.run(["python", "--version"], capture_output=True, text=True)
        env_checks["python"] = result.returncode == 0
        if env_checks["python"]:
            print(f"✅ Python: {result.stdout.strip()}")
        else:
            print("❌ Python not found")
    except:
        env_checks["python"] = False
        print("❌ Python not available")

    # Check UV
    try:
        result = subprocess.run(
            ["uv", "--version"], capture_output=True, text=True, timeout=5
        )
        env_checks["uv"] = result.returncode == 0
        if env_checks["uv"]:
            print(f"✅ UV: {result.stdout.strip()}")
        else:
            print("⚠️  UV not found, using standard Python")
    except:
        env_checks["uv"] = False
        print("⚠️  UV not available, using standard Python")

    # Check Podman
    try:
        result = subprocess.run(
            ["podman", "--version"], capture_output=True, text=True, timeout=5
        )
        env_checks["podman"] = result.returncode == 0
        if env_checks["podman"]:
            print(f"✅ Podman: {result.stdout.strip()}")
        else:
            print("⚠️  Podman not found")
    except:
        env_checks["podman"] = False
        print("⚠️  Podman not available")

    # Step 2: Project Configuration Validation
    print("\n📋 Step 2: Project Configuration Validation")
    print("-" * 30)

    config_checks = {}

    # Check projects.json
    projects_file = Path("projects.json")
    if projects_file.exists():
        print("✅ projects.json found")
        try:
            with open(projects_file) as f:
                projects_data = json.load(f)
                project_count = len(projects_data.get("projects", []))
                print(f"✅ {project_count} projects configured")

                # Count languages
                languages = set()
                container_capable = 0
                for project in projects_data.get("projects", []):
                    if project.get("language"):
                        languages.add(project["language"])
                    if project.get("container_capable"):
                        container_capable += 1

                print(
                    f"✅ {len(languages)} languages covered: {', '.join(sorted(languages))}"
                )
                print(f"✅ {container_capable} container-capable projects for DAST")
                config_checks["projects"] = True
        except Exception as e:
            print(f"❌ Error reading projects.json: {e}")
            config_checks["projects"] = False
    else:
        print("❌ projects.json not found")
        config_checks["projects"] = False

    # Check enhanced configs
    enhanced_file = Path("validation/configs/enhanced-projects.json")
    if enhanced_file.exists():
        print("✅ Enhanced projects configuration exists")
        config_checks["enhanced"] = True
    else:
        print("⚠️  Enhanced projects configuration not found")
        config_checks["enhanced"] = False

    # Step 3: Validation Directory Structure
    print("\n📋 Step 3: Validation Structure")
    print("-" * 30)

    validation_dirs = [
        "validation",
        "validation/configs",
        "validation/logs",
        "validation/reports",
    ]
    structure_ok = True

    for dir_path in validation_dirs:
        dir_obj = Path(dir_path)
        if dir_obj.exists():
            print(f"✅ {dir_path}/ exists")
        else:
            print(f"❌ {dir_path}/ missing")
            structure_ok = False

    # Step 4: Quick Functionality Test
    print("\n📋 Step 4: Quick Functionality Test")
    print("-" * 30)

    # Test basic import
    try:
        # Simple import test
        result = subprocess.run(
            [
                "python",
                "-c",
                "import src.models.project; print('✅ GeoToolKit modules importable')",
            ],
            capture_output=True,
            text=True,
            timeout=10,
        )
        if result.returncode == 0:
            print(result.stdout.strip())
            func_test = True
        else:
            print("❌ Module import failed")
            func_test = False
    except Exception as e:
        print(f"❌ Import test failed: {e}")
        func_test = False

    # Step 5: Generate Summary Report
    print("\n📋 Step 5: Validation Summary")
    print("-" * 30)

    total_checks = len(env_checks) + len(config_checks) + 1 + 1  # structure + func
    passed_checks = (
        sum(env_checks.values())
        + sum(config_checks.values())
        + (1 if structure_ok else 0)
        + (1 if func_test else 0)
    )

    success_rate = (passed_checks / total_checks) * 100

    print(
        f"📊 Validation Results: {passed_checks}/{total_checks} checks passed ({success_rate:.1f}%)"
    )

    # Create summary report
    summary = {
        "validation_timestamp": timestamp,
        "success_rate": round(success_rate, 1),
        "total_checks": total_checks,
        "passed_checks": passed_checks,
        "environment_checks": env_checks,
        "configuration_checks": config_checks,
        "structure_ok": structure_ok,
        "functionality_test": func_test,
        "ready_for_full_validation": success_rate >= 80,
    }

    # Save summary
    summary_file = Path("validation") / f"quick-validation-{timestamp}.json"
    summary_file.parent.mkdir(parents=True, exist_ok=True)

    with open(summary_file, "w") as f:
        json.dump(summary, f, indent=2)

    print(f"💾 Summary saved to: {summary_file}")

    if success_rate >= 80:
        print("\n🎉 System ready for full validation!")
        print("Next steps:")
        print("   1. Run: python scripts/enrich_projects.py")
        print("   2. Run: python scripts/validation_executor.py")
        print(
            "   3. For DAST: python scripts/start_dast_targets.py validation/configs/container-projects.json"
        )
    else:
        print("\n⚠️  System needs setup before full validation")
        print("Issues to address:")
        if not env_checks.get("python"):
            print("   - Install Python 3.11+")
        if not config_checks.get("projects"):
            print("   - Fix projects.json configuration")
        if not structure_ok:
            print("   - Run mkdir -p validation/{configs,logs,reports}")
        if not func_test:
            print("   - Check GeoToolKit module structure")

    return success_rate >= 80


if __name__ == "__main__":
    success = run_quick_validation()
    exit(0 if success else 1)
