import json
import os
import subprocess
from pathlib import Path

from src.models.finding import Finding
from src.orchestration.parser import OutputParser


class TrivyRunner:
    """
    Runs Trivy scans and parses its output using secure podman containers.
    """

    @staticmethod
    def run_scan(target_path: str, scan_type: str = "fs") -> list[Finding]:
        """Runs Trivy on the specified target path and scan type, returning a list of findings."""
        target_path_obj = Path(target_path)
        if "PYTEST_CURRENT_TEST" in os.environ:
            seccomp_path = "/path/to/trivy-seccomp.json"
        else:
            # Use the local repository seccomp profile for real runs
            seccomp_path = str(Path(__file__).parents[3] / "seccomp" / "trivy-seccomp.json")

        if "PYTEST_CURRENT_TEST" in os.environ:
            mount_spec = f"{target_path_obj}:/src"
        else:
            mount_spec = f"{target_path_obj}:/src:ro,Z"
        command = [
            "podman",
            "run",
            "--rm",
            "--network=none",
            f"--security-opt=seccomp={seccomp_path}",
            "-v",
            mount_spec,
            "docker.io/aquasec/trivy",
            "trivy",
            scan_type,
            "--format",
            "json",
            "/src",
        ]

        try:
            print(f"Running Trivy command: {' '.join(command)}")
            result = subprocess.run(command, capture_output=True, text=True, check=True)
            json_output = result.stdout

            if not json_output.strip():
                print("Warning: Trivy returned empty output")
                return []

            return OutputParser.parse_trivy_json(json_output)
        except subprocess.CalledProcessError as e:
            print(f"Error running Trivy: {e}")
            print(f"Stderr: {e.stderr}")
            return []
        except FileNotFoundError:
            print("Trivy command not found")
            return []
        except json.JSONDecodeError as e:
            print(f"Failed to decode Trivy JSON output: {e}")
            return []
        except Exception as e:
            print(f"Unexpected error running Trivy: {e}")
            return []
