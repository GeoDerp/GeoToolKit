import subprocess
import tempfile
from pathlib import Path

import git
from src.models.finding import Finding
from src.models.project import Project
from src.models.scan import Scan
from src.orchestration.runners.osv_runner import OSVRunner
from src.orchestration.runners.semgrep_runner import SemgrepRunner
from src.orchestration.runners.trivy_runner import TrivyRunner
from src.orchestration.runners.zap_runner import ZapRunner


class Workflow:
    """
    Manages the overall scanning process for projects with secure container execution.
    """

    @staticmethod
    def run_project_scan(
        project: Project,
        network_allowlist: list[str] | None = None,
        timeouts: dict[str, int] | None = None,
    ) -> Scan:
        """Runs a complete security scan for a given project using all configured runners."""
        scan = Scan(projectId=project.id, status="in_progress")
        all_findings: list[Finding] = []

        print(f"Starting scan for project: {project.name} ({project.url})")
        print(f"Project language: {project.language or 'Auto-detect'}")

        url_str = str(project.url)
        # If target is a live app URL, run DAST-only and skip cloning
        if url_str.startswith(("http://", "https://")) and not any(
            domain in url_str.lower()
            for domain in ["github.com", "gitlab.com", "bitbucket.org"]
        ):
            print(f"Detected application URL, running DAST-only: {project.url}")
            try:
                dast_timeout = timeouts.get("dast_seconds") if timeouts else None
                zap_findings = ZapRunner.run_scan(
                    url_str,
                    network_allowlist=network_allowlist,
                    timeout=dast_timeout,
                )
                all_findings.extend(zap_findings)
                scan.status = "completed"
            except Exception as e:
                print(f"Error during DAST scan for {project.url}: {e}")
                scan.status = "failed"
        # Check if URL is a local path
        elif url_str.startswith("/") or Path(url_str).exists():
            # Use local path directly
            project_path_str = url_str
            print(f"Using local path: {project_path_str}")
            try:
                all_findings.extend(
                    Workflow._run_security_scans(
                        project_path_str, project, network_allowlist, timeouts
                    )
                )
            except Exception as e:
                print(f"Error processing local path {project_path_str}: {e}")
                scan.status = "failed"
        else:
            # Clone the repository to a temporary directory with secure settings
            with tempfile.TemporaryDirectory() as temp_dir:
                project_path = Path(temp_dir) / project.name
                try:
                    print(f"Cloning repository {project.url} to {project_path}")
                    # Clone with security considerations
                    # Enhanced security: disable git hooks and templates to prevent execution
                    # of potentially malicious code during clone operations
                    secure_env = {
                        "GIT_TEMPLATE_DIR": "",  # Disable git template directory
                        "GIT_CONFIG_NOSYSTEM": "1",  # Ignore system-wide git config
                        "GIT_CONFIG_GLOBAL": "/dev/null",  # Ignore global git config
                    }
                    repo = git.Repo.clone_from(
                        str(project.url),
                        str(project_path),
                        depth=1,  # Shallow clone for efficiency
                        single_branch=True,  # Only default branch
                        no_hardlinks=True,  # Prevent hardlink attacks
                        env=secure_env,  # Apply security environment variables
                    )
                    print(f"Repository cloned successfully to {project_path}")
                    print(f"Repository head: {repo.head.commit.hexsha[:8]}")
                    # Run security scans on the cloned repository
                    all_findings.extend(
                        Workflow._run_security_scans(
                            str(project_path), project, network_allowlist, timeouts
                        )
                    )
                except git.GitCommandError as e:
                    print(f"Failed to clone repository {project.url}: {e}")
                    scan.status = "failed"
                except Exception as e:
                    print(f"Unexpected error while cloning {project.url}: {e}")
                    scan.status = "failed"

        scan.results = all_findings
        if scan.status != "failed":
            scan.status = "completed"
        print(
            f"Scan for {project.name} completed with {len(all_findings)} total findings."
        )
        return scan

    @staticmethod
    def _run_security_scans(
        project_path: str,
        project: Project,
        network_allowlist: list[str] | None,
        timeouts: dict[str, int] | None = None,
    ) -> list[Finding]:
        """
        Runs all security scanning tools on the given project path.
        All tools run in secure, isolated Podman containers.
        """
        all_findings: list[Finding] = []
        runner_timeout = timeouts.get("runner_seconds") if timeouts else None
        try:
            # SAST: Semgrep - Static code analysis
            print("🔍 Running Semgrep (SAST)...")
            try:
                semgrep_findings = SemgrepRunner.run_scan(
                    project_path, timeout=runner_timeout
                )
                all_findings.extend(semgrep_findings)
                print(f"✅ Semgrep found {len(semgrep_findings)} findings.")
            except Exception as e:
                print(f"❌ Semgrep scan failed: {e}")

            # SCA: Trivy - Vulnerability scanning
            print("🔍 Running Trivy (SCA)...")
            try:
                trivy_findings = TrivyRunner.run_scan(
                    project_path, scan_type="fs", timeout=runner_timeout
                )
                all_findings.extend(trivy_findings)
                print(f"✅ Trivy found {len(trivy_findings)} findings.")
            except Exception as e:
                print(f"❌ Trivy scan failed: {e}")

            # SCA: OSV-Scanner - Open Source Vulnerabilities
            print("🔍 Running OSV-Scanner (SCA)...")
            try:
                osv_findings = OSVRunner.run_scan(project_path, timeout=runner_timeout)
                all_findings.extend(osv_findings)
                print(f"✅ OSV-Scanner found {len(osv_findings)} findings.")
            except Exception as e:
                print(f"❌ OSV-Scanner scan failed: {e}")

            # DAST: OWASP ZAP - Dynamic analysis (skip for source code scanning)
            if Workflow._should_run_dast_scan(project):
                print("🔍 Running OWASP ZAP (DAST)...")
                dast_timeout = timeouts.get("dast_seconds") if timeouts else None
                try:
                    zap_findings = ZapRunner.run_scan(
                        str(project.url),
                        network_allowlist=network_allowlist,
                        timeout=dast_timeout,
                    )
                    all_findings.extend(zap_findings)
                    print(f"✅ OWASP ZAP found {len(zap_findings)} findings.")
                except Exception as e:
                    print(f"❌ OWASP ZAP scan failed: {e}")
            else:
                print(
                    "ℹ️  Skipping OWASP ZAP (DAST) - not applicable for source code analysis"
                )

        except subprocess.CalledProcessError as e:
            print(f"❌ Security scan subprocess failed: {e}")
            if e.stdout:
                print(f"STDOUT: {e.stdout}")
            if e.stderr:
                print(f"STDERR: {e.stderr}")
        except Exception as e:
            print(f"❌ Unexpected error during security scans: {e}")

        return all_findings

    @staticmethod
    def _should_run_dast_scan(project: Project) -> bool:
        """
        Determine if DAST scanning should be performed for this project.
        DAST is typically only useful for web applications.
        """
        url_str = str(project.url).lower()
        # Skip DAST for GitHub/GitLab/etc URLs (source repositories)
        if any(
            domain in url_str
            for domain in ["github.com", "gitlab.com", "bitbucket.org"]
        ):
            return False
        # Enable DAST for HTTP/HTTPS URLs that might be running applications
        if url_str.startswith(("http://", "https://")) and not any(
            domain in url_str
            for domain in ["github.com", "gitlab.com", "bitbucket.org"]
        ):
            return True
        return False
