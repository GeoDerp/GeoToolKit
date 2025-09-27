import json
import os
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

        # Consolidate logic to remove the test-specific backdoor
        semgrep_pack = os.environ.get("SEMGREP_PACK")
        if semgrep_pack:
            network_mode = (
                "--network=host" if os.environ.get("SEMGREP_ONLINE", "0") == "1" else "--network=none"
            )
            command = [
                "podman",
                "run",
                "--rm",
                network_mode,
                "-v",
                f"{project_path_obj}:/src:ro,Z",
                "docker.io/semgrep/semgrep",
                "semgrep",
                "--config",
                semgrep_pack,
                "--json",
                "/src",
            ]
        else:
            # Use a local semgrep config if present, otherwise repo default; else skip
            candidate_configs = [
                project_path_obj / ".semgrep.yml",
                project_path_obj / ".semgrep.yaml",
                project_path_obj / "semgrep.yml",
                project_path_obj / "semgrep.yaml",
            ]
            config_path = next((c for c in candidate_configs if c.exists()), None)
            if not config_path:
                default_rules = Path(__file__).parents[3] / "rules" / "semgrep" / "default.semgrep.yml"
                if default_rules.exists():
                    config_path = default_rules
                else:
                    print("Semgrep: No local or default config found. Skipping Semgrep.")
                    return []
            src_mount = f"{project_path_obj}:/src:ro,Z"
            rules_mount = f"{config_path}:/rules.yml:ro,Z"
            command = [
                "podman",
                "run",
                "--rm",
                "--network=none",
                "-v",
                src_mount,
                "-v",
                rules_mount,
                "docker.io/semgrep/semgrep",
                "semgrep",
                "--config",
                "/rules.yml",
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
