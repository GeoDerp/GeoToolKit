#!/usr/bin/env python3
"""
Non-interactive DAST container startup script
Builds and starts DAST targets without waiting for user input
"""

import json
import subprocess
import time


def run_command(cmd, capture=True):
    """Run a command and return the result"""
    try:
        if capture:
            result = subprocess.run(cmd, capture_output=True, text=True, check=False)
        else:
            result = subprocess.run(cmd, check=False)
        return result
    except Exception as e:
        print(f"Error running {' '.join(cmd)}: {e}")
        return None


def main():
    print("🎯 Starting DAST Targets (Non-Interactive)")
    print("=" * 50)

    # Load config
    config_file = "container-projects.json"
    with open(config_file) as f:
        config = json.load(f)

    # Create network
    print("\n🌐 Creating network...")
    run_command(["podman", "network", "create", "gt-dast-net"])

    # Build and start each container
    for project in config["projects"]:
        name = project["name"]
        path = project["path"]
        port = project["port"]

        print(f"\n📦 {name}")
        print("   Building...")

        # Build
        result = run_command(
            ["podman", "build", "-t", f"{name}:test", "-f", f"{path}/Dockerfile", path],
            capture=False,
        )

        if result and result.returncode == 0:
            print("   ✅ Build successful")

            # Start container
            print(f"   Starting on port {port}...")
            result = run_command(
                [
                    "podman",
                    "run",
                    "-d",
                    "--rm",
                    "--name",
                    f"{name}-target",
                    "--network",
                    "gt-dast-net",
                    "-p",
                    f"127.0.0.1:{port}:{port}",
                    f"{name}:test",
                ]
            )

            if result and result.returncode == 0:
                print("   ✅ Started successfully")
            else:
                print("   ❌ Failed to start")
        else:
            print("   ❌ Build failed")

    # Wait for startup
    print("\n⏱️  Waiting 10 seconds for containers to initialize...")
    time.sleep(10)

    # List running containers
    print("\n📋 Running containers:")
    run_command(["podman", "ps", "--filter", "network=gt-dast-net"], capture=False)

    print("\n✅ DAST targets are ready!")
    print("\nTo stop all targets, run:")
    print("  podman stop $(podman ps -q --filter network=gt-dast-net)")
    print("  podman network rm gt-dast-net")


if __name__ == "__main__":
    main()
