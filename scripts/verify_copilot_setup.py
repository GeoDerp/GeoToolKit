#!/usr/bin/env python3
"""
GitHub Copilot Setup Verification Script for GeoToolKit

This script helps verify that GitHub Copilot is properly configured
for the GeoToolKit security scanner project.
"""

import json
import os
import sys
from pathlib import Path


def check_file_exists(filepath: str, description: str) -> bool:
    """Check if a file exists and print status."""
    if os.path.exists(filepath):
        print(f"✓ {description}: {filepath}")
        return True
    else:
        print(f"✗ {description} MISSING: {filepath}")
        return False


def check_json_valid(filepath: str, description: str) -> bool:
    """Check if a JSON file is valid."""
    try:
        with open(filepath, 'r') as f:
            json.load(f)
        print(f"✓ {description} is valid JSON")
        return True
    except FileNotFoundError:
        print(f"✗ {description} not found: {filepath}")
        return False
    except json.JSONDecodeError as e:
        print(f"✗ {description} has invalid JSON: {e}")
        return False


def check_copilot_extensions() -> bool:
    """Check if Copilot extensions are in recommendations."""
    try:
        with open('.vscode/extensions.json', 'r') as f:
            data = json.load(f)
        
        recommendations = data.get('recommendations', [])
        copilot_extensions = ['GitHub.copilot', 'GitHub.copilot-chat']
        
        missing = []
        for ext in copilot_extensions:
            if ext in recommendations:
                print(f"✓ {ext} found in recommendations")
            else:
                missing.append(ext)
                print(f"✗ {ext} missing from recommendations")
        
        return len(missing) == 0
    except Exception as e:
        print(f"✗ Error checking extensions: {e}")
        return False


def check_copilot_settings() -> bool:
    """Check if Copilot settings are configured."""
    try:
        with open('.vscode/settings.json', 'r') as f:
            data = json.load(f)
        
        copilot_settings = [
            'github.copilot.enable',
            'github.copilot.inlineSuggest.enable',
            'editor.inlineSuggest.enabled'
        ]
        
        missing = []
        for setting in copilot_settings:
            if setting in data:
                print(f"✓ {setting} configured")
            else:
                missing.append(setting)
                print(f"✗ {setting} not configured")
        
        return len(missing) == 0
    except Exception as e:
        print(f"✗ Error checking settings: {e}")
        return False


def main():
    """Main verification function."""
    print("GitHub Copilot Setup Verification for GeoToolKit")
    print("=" * 50)
    
    # Check if we're in the right directory
    if not os.path.exists('pyproject.toml'):
        print("✗ Not in GeoToolKit root directory (pyproject.toml not found)")
        print("Please run this script from the GeoToolKit root directory")
        sys.exit(1)
    
    print("✓ Running from GeoToolKit root directory")
    print()
    
    # Check required files
    print("Checking configuration files...")
    files_ok = True
    files_to_check = [
        ('.vscode/extensions.json', 'VSCode extensions'),
        ('.vscode/settings.json', 'VSCode settings'),
        ('.vscode/tasks.json', 'VSCode tasks'),
        ('.github/copilot-instructions.md', 'Copilot instructions'),
        ('.copilotignore', 'Copilot ignore file'),
        ('geotoolkit.code-workspace', 'VSCode workspace'),
        ('docs/COPILOT_SETUP.md', 'Copilot setup guide')
    ]
    
    for filepath, description in files_to_check:
        if not check_file_exists(filepath, description):
            files_ok = False
    
    print()
    
    # Check JSON validity
    print("Checking JSON file validity...")
    json_ok = True
    json_files = [
        ('.vscode/extensions.json', 'VSCode extensions'),
        ('.vscode/settings.json', 'VSCode settings'),
        ('.vscode/tasks.json', 'VSCode tasks'),
        ('geotoolkit.code-workspace', 'VSCode workspace')
    ]
    
    for filepath, description in json_files:
        if not check_json_valid(filepath, description):
            json_ok = False
    
    print()
    
    # Check Copilot-specific configuration
    print("Checking Copilot configuration...")
    extensions_ok = check_copilot_extensions()
    print()
    settings_ok = check_copilot_settings()
    print()
    
    # Summary
    print("Verification Summary")
    print("-" * 20)
    
    all_ok = files_ok and json_ok and extensions_ok and settings_ok
    
    if all_ok:
        print("✓ All checks passed! GitHub Copilot should be properly configured.")
        print("\nNext steps:")
        print("1. Open this project in VSCode")
        print("2. Install recommended extensions when prompted")
        print("3. Sign in to GitHub Copilot")
        print("4. Try editing a Python file in src/ to test suggestions")
        print("\nFor detailed setup instructions, see docs/COPILOT_SETUP.md")
    else:
        print("✗ Some checks failed. Please review the errors above.")
        print("You may need to re-run the setup or check the configuration files.")
    
    return 0 if all_ok else 1


if __name__ == '__main__':
    sys.exit(main())