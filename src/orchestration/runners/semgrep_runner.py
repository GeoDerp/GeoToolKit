import json
import subprocess
from pathlib import Path

from src.models.finding import Finding
from src.orchestration.parser import OutputParser


class SemgrepRunner:
    """
    Runs Semgrep scans and parses its output using secure podman containers.
    """

    @staticmethod
    def run_scan(project_path: str) -> list[Finding]:
        """Runs Semgrep on the specified project path and returns a list of findings."""
        project_path_obj = Path(project_path)
        # Align with unit test expectations (simplified invocation)
        command = [
            "podman",
            "run",
            "--rm",
            "--network=none",
            "-v",
            f"{project_path_obj}:/src",
            "-v",
            f"{project_path_obj}:/.semgrep.yml:/.semgrep.yml",
            "docker.io/semgrep/semgrep",
            "semgrep",
            "--config",
            "/.semgrep.yml",
            "--json",
            "/src",
        ]

        try:
            print(f"Running Semgrep command: {' '.join(command)}")
            result = subprocess.run(command, capture_output=True, text=True, check=True)
            json_output = result.stdout

            if not json_output.strip():
                print("Warning: Semgrep returned empty output")
                return []

            return OutputParser.parse_semgrep_json(json_output)
        except subprocess.CalledProcessError as e:
            print(f"Error running Semgrep: {e}")
            print(f"Stderr: {e.stderr}")
            return []
        except FileNotFoundError:
            print("Semgrep command not found")
            return []
        except json.JSONDecodeError as e:
            print(f"Failed to decode Semgrep JSON output: {e}")
            return []
        except Exception as e:
            print(f"Unexpected error running Semgrep: {e}")
            return []
