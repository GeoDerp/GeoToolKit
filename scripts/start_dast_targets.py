#!/usr/bin/env python3
"""
DAST Container Management Script for GeoToolKit validation
Manages containerized targets for DAST scanning with network isolation
"""

import json
import subprocess
import sys
import time
from typing import Any

import requests


class DastTargetManager:
    def __init__(self, container_projects_file: str):
        self.container_projects_file = container_projects_file
        self.network_name = "gt-dast-net"
        self.running_containers = []

        # Load container project configurations
        try:
            with open(container_projects_file) as f:
                self.projects_data = json.load(f)
        except FileNotFoundError:
            print(f"❌ Container projects file not found: {container_projects_file}")
            sys.exit(1)
        except json.JSONDecodeError as e:
            print(f"❌ Invalid JSON in {container_projects_file}: {e}")
            sys.exit(1)

    def run_command(self, cmd: list[str], capture_output: bool = True) -> subprocess.CompletedProcess:
        """Run a shell command and return the result"""
        try:
            result = subprocess.run(
                cmd,
                capture_output=capture_output,
                text=True,
                check=False
            )
            return result
        except Exception as e:
            print(f"❌ Command failed: {' '.join(cmd)}")
            print(f"Error: {e}")
            return subprocess.CompletedProcess(cmd, 1, "", str(e))

    def create_network(self) -> bool:
        """Create isolated network for DAST testing"""
        print(f"🌐 Creating isolated network: {self.network_name}")

        # Check if network already exists
        result = self.run_command(["podman", "network", "ls", "--format", "{{.Name}}"])
        if self.network_name in result.stdout:
            print(f"⚠️  Network {self.network_name} already exists")
            return True

        # Create new network
        result = self.run_command([
            "podman", "network", "create",
            "--driver", "bridge",
            self.network_name
        ])

        if result.returncode == 0:
            print(f"✅ Network {self.network_name} created successfully")
            return True
        else:
            print(f"❌ Failed to create network: {result.stderr}")
            return False

    def remove_network(self) -> bool:
        """Remove the isolated network"""
        print(f"🗑️  Removing network: {self.network_name}")
        result = self.run_command(["podman", "network", "rm", self.network_name])

        if result.returncode == 0:
            print(f"✅ Network {self.network_name} removed")
            return True
        else:
            print(f"⚠️  Could not remove network: {result.stderr}")
            return False

    def build_container(self, project: dict[str, Any]) -> bool:
        """Build container for a project"""
        project_name = project["name"]
        project_url = project["url"]

        print(f"🔨 Building container for {project_name}")

        # For this simulation, we'll use pre-built images where available
        # In a real scenario, you'd clone the repo and build from source

        known_images = {
            "juice-shop": "bkimminich/juice-shop:latest",
            "httpbin": "kennethreitz/httpbin:latest",
            "gin": "golang:1.21-alpine",  # Would build custom image
            "spring-boot": "openjdk:17-jdk-alpine"  # Would build custom image
        }

        if project_name in known_images:
            # Pull existing image
            result = self.run_command([
                "podman", "pull", known_images[project_name]
            ])

            if result.returncode == 0:
                # Tag with our naming convention
                self.run_command([
                    "podman", "tag",
                    known_images[project_name],
                    f"{project_name}:test"
                ])
                print(f"✅ Container ready: {project_name}:test")
                return True
            else:
                print(f"❌ Failed to pull image for {project_name}: {result.stderr}")
                return False
        else:
            print(f"⚠️  No pre-built image for {project_name}, would need to clone and build")
            print(f"   Repository: {project_url}")
            return False

    def start_container(self, project: dict[str, Any]) -> bool:
        """Start a container for DAST target"""
        project_name = project["name"]
        network_config = project.get("network_config", {})
        ports = network_config.get("ports", ["8080"])
        primary_port = ports[0]

        container_name = f"{project_name}-dast-target"

        print(f"🚀 Starting container: {container_name}")

        # Build port mapping arguments
        port_args = []
        for port in ports:
            port_args.extend(["-p", f"127.0.0.1:{port}:{port}"])

        cmd = [
            "podman", "run",
            "-d",  # detached
            "--rm",  # remove on exit
            "--name", container_name,
            "--network", self.network_name
        ] + port_args + [
            f"{project_name}:test"
        ]

        result = self.run_command(cmd)

        if result.returncode == 0:
            self.running_containers.append(container_name)
            print(f"✅ Container started: {container_name}")

            # Wait for startup
            startup_time = network_config.get("startup_time_seconds", 30)
            print(f"⏱️  Waiting {startup_time}s for container startup...")
            time.sleep(startup_time)

            return True
        else:
            print(f"❌ Failed to start container: {result.stderr}")
            return False

    def check_health(self, project: dict[str, Any]) -> bool:
        """Check if container target is healthy and responding"""
        project_name = project["name"]
        network_config = project.get("network_config", {})
        ports = network_config.get("ports", ["8080"])
        health_endpoint = network_config.get("health_endpoint", "/")
        primary_port = ports[0]

        health_url = f"http://127.0.0.1:{primary_port}{health_endpoint}"

        print(f"🩺 Checking health: {health_url}")

        try:
            response = requests.get(health_url, timeout=10)
            if response.status_code < 400:
                print(f"✅ {project_name} is healthy (HTTP {response.status_code})")
                return True
            else:
                print(f"⚠️  {project_name} returned HTTP {response.status_code}")
                return False
        except requests.exceptions.RequestException as e:
            print(f"❌ Health check failed for {project_name}: {e}")
            return False

    def stop_all_containers(self) -> None:
        """Stop all running DAST target containers"""
        print("🛑 Stopping all DAST target containers...")

        for container_name in self.running_containers:
            print(f"   Stopping {container_name}")
            result = self.run_command(["podman", "stop", container_name])
            if result.returncode != 0:
                print(f"   ⚠️  Could not stop {container_name}: {result.stderr}")

        self.running_containers.clear()
        print("✅ All containers stopped")

    def generate_network_allowlist(self) -> list[str]:
        """Generate network allowlist from container projects"""
        allowlist = []

        for project in self.projects_data.get("projects", []):
            if not project.get("container_capable"):
                continue

            network_config = project.get("network_config", {})
            allowed_egress = network_config.get("allowed_egress", {})

            # Add localhost entries
            for port in allowed_egress.get("localhost", []):
                allowlist.append(f"127.0.0.1:{port}")

        return allowlist

    def start_all_targets(self) -> list[dict[str, Any]]:
        """Start all DAST targets and return list of healthy ones"""
        if not self.create_network():
            return []

        healthy_targets = []

        for project in self.projects_data.get("projects", []):
            if not project.get("container_capable"):
                continue

            print(f"\n📋 Processing {project['name']} ({project['language']})")

            # Build container
            if not self.build_container(project):
                print(f"   ❌ Skipping {project['name']} - build failed")
                continue

            # Start container
            if not self.start_container(project):
                print(f"   ❌ Skipping {project['name']} - start failed")
                continue

            # Check health
            if self.check_health(project):
                healthy_targets.append(project)
                print(f"   ✅ {project['name']} ready for DAST")
            else:
                print(f"   ⚠️  {project['name']} unhealthy, may still be scannable")
                healthy_targets.append(project)  # Include anyway for testing

        return healthy_targets

    def cleanup(self) -> None:
        """Clean up all resources"""
        self.stop_all_containers()
        self.remove_network()


def main():
    if len(sys.argv) != 2:
        print("Usage: python scripts/start_dast_targets.py <container-projects.json>")
        sys.exit(1)

    container_projects_file = sys.argv[1]

    print("🎯 GeoToolKit DAST Target Manager")
    print("=" * 40)

    manager = DastTargetManager(container_projects_file)

    try:
        # Start all targets
        healthy_targets = manager.start_all_targets()

        if healthy_targets:
            print(f"\n✅ Started {len(healthy_targets)} DAST targets")
            print("🌐 Network allowlist:")
            allowlist = manager.generate_network_allowlist()
            for entry in allowlist:
                print(f"   - {entry}")

            print("\n🔍 Ready for DAST scanning!")
            print("To run DAST scan:")
            print("   python src/main.py --input validation/configs/container-projects.json \\")
            print("                      --output validation/reports/security-report.md \\")
            print("                      --database-path data/offline-db.tar.gz")

            input("\nPress Enter to stop all targets and cleanup...")
        else:
            print("\n❌ No healthy DAST targets available")

    finally:
        print("\n🧹 Cleaning up...")
        manager.cleanup()


if __name__ == "__main__":
    main()
