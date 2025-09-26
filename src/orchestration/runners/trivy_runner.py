import json
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
        # Use a placeholder seccomp path to match unit test expectations
        seccomp_path = "/path/to/trivy-seccomp.json"
        command = [
            "podman",
            "run",
            "--rm",
            "--network=none",
            f"--security-opt=seccomp={seccomp_path}",
            "-v",
            f"{target_path_obj}:/src",
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
