#!/usr/bin/env python3
"""
Production Deployment Readiness Validator for GeoToolKit

This script executes a comprehensive production readiness test suite that validates:
1. Core functionality across all supported programming languages
2. Load testing and performance validation
3. Security configuration validation
4. Container isolation and resource limits
5. Error handling and edge cases
6. Memory usage and resource management
7. Network isolation and security
8. Report generation under various conditions

Usage:
    python scripts/production_validator.py --full-test
    python scripts/production_validator.py --quick-test
    python scripts/production_validator.py --load-test --concurrent-scans 20
"""

import argparse
import json
import logging
import subprocess
import sys
import time
from pathlib import Path

# Setup logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class ProductionValidator:
    """Main production validation orchestrator."""

    def __init__(self):
        self.project_root = Path(__file__).parent.parent
        self.test_results = {
            "validation_timestamp": time.strftime(
                "%Y-%m-%d %H:%M:%S UTC", time.gmtime()
            ),
            "tests": {},
            "summary": {},
            "issues_found": [],
            "recommendations": [],
        }

    def validate_environment(self):
        """Validate the test environment is properly set up."""
        logger.info("Validating test environment...")

        # Check Python environment
        try:
            result = subprocess.run(
                [sys.executable, "--version"], capture_output=True, text=True
            )
            python_version = result.stdout.strip()
            logger.info(f"Python version: {python_version}")
        except Exception as e:
            logger.error(f"Python environment check failed: {e}")
            return False

        # Check required directories exist
        required_dirs = ["src", "tests", "seccomp", "scripts"]

        for dir_name in required_dirs:
            dir_path = self.project_root / dir_name
            if not dir_path.exists():
                logger.error(f"Required directory missing: {dir_name}")
                return False

        # Check configuration files
        required_files = [
            "pyproject.toml",
            "projects.json",
            "languages.json",
            "seccomp/default.json",
        ]

        for file_name in required_files:
            file_path = self.project_root / file_name
            if not file_path.exists():
                logger.error(f"Required file missing: {file_name}")
                return False

        logger.info("✅ Environment validation passed")
        return True

    def run_unit_tests(self):
        """Run all unit tests."""
        logger.info("Running unit tests...")

        start_time = time.time()

        try:
            result = subprocess.run(
                [sys.executable, "-m", "pytest", "tests/unit/", "-v"],
                cwd=self.project_root,
                capture_output=True,
                text=True,
                timeout=300,
            )

            duration = time.time() - start_time

            test_result = {
                "status": "passed" if result.returncode == 0 else "failed",
                "duration": duration,
                "return_code": result.returncode,
                "stdout": result.stdout,
                "stderr": result.stderr,
            }

            self.test_results["tests"]["unit_tests"] = test_result

            if result.returncode == 0:
                logger.info(f"✅ Unit tests passed in {duration:.2f}s")
            else:
                logger.error(f"❌ Unit tests failed (exit code: {result.returncode})")
                self.test_results["issues_found"].append(
                    {
                        "type": "unit_test_failure",
                        "description": "Unit tests failed",
                        "details": result.stderr,
                    }
                )

        except subprocess.TimeoutExpired:
            logger.error("❌ Unit tests timed out")
            self.test_results["tests"]["unit_tests"] = {
                "status": "timeout",
                "duration": 300,
                "error": "Test execution timed out",
            }

        return self.test_results["tests"]["unit_tests"]["status"] == "passed"

    def run_integration_tests(self):
        """Run integration tests."""
        logger.info("Running integration tests...")

        start_time = time.time()

        try:
            result = subprocess.run(
                [sys.executable, "-m", "pytest", "tests/integration/", "-v"],
                cwd=self.project_root,
                capture_output=True,
                text=True,
                timeout=600,
            )

            duration = time.time() - start_time

            test_result = {
                "status": "passed" if result.returncode == 0 else "failed",
                "duration": duration,
                "return_code": result.returncode,
                "stdout": result.stdout,
                "stderr": result.stderr,
            }

            self.test_results["tests"]["integration_tests"] = test_result

            if result.returncode == 0:
                logger.info(f"✅ Integration tests passed in {duration:.2f}s")
            else:
                logger.error("❌ Integration tests failed")
                self.test_results["issues_found"].append(
                    {
                        "type": "integration_test_failure",
                        "description": "Integration tests failed",
                        "details": result.stderr,
                    }
                )

        except subprocess.TimeoutExpired:
            logger.error("❌ Integration tests timed out")
            self.test_results["tests"]["integration_tests"] = {
                "status": "timeout",
                "duration": 600,
                "error": "Test execution timed out",
            }

        return self.test_results["tests"]["integration_tests"]["status"] == "passed"

    def run_production_tests(self):
        """Run production-specific tests."""
        logger.info("Running production readiness tests...")

        start_time = time.time()

        try:
            result = subprocess.run(
                [sys.executable, "-m", "pytest", "tests/production/", "-v", "-s"],
                cwd=self.project_root,
                capture_output=True,
                text=True,
                timeout=900,  # 15 minutes
            )

            duration = time.time() - start_time

            test_result = {
                "status": "passed" if result.returncode == 0 else "failed",
                "duration": duration,
                "return_code": result.returncode,
                "stdout": result.stdout,
                "stderr": result.stderr,
            }

            self.test_results["tests"]["production_tests"] = test_result

            if result.returncode == 0:
                logger.info(f"✅ Production tests passed in {duration:.2f}s")
            else:
                logger.error("❌ Production tests failed")
                self.test_results["issues_found"].append(
                    {
                        "type": "production_test_failure",
                        "description": "Production readiness tests failed",
                        "details": result.stderr,
                    }
                )

        except subprocess.TimeoutExpired:
            logger.error("❌ Production tests timed out")
            self.test_results["tests"]["production_tests"] = {
                "status": "timeout",
                "duration": 900,
                "error": "Test execution timed out",
            }

        return self.test_results["tests"]["production_tests"]["status"] == "passed"

    def run_load_tests(self, concurrent_scans=10):
        """Run load testing."""
        logger.info(f"Running load tests with {concurrent_scans} concurrent scans...")

        load_script = self.project_root / "scripts" / "load_testing.py"
        if not load_script.exists():
            logger.error("Load testing script not found")
            return False

        start_time = time.time()

        try:
            result = subprocess.run(
                [
                    sys.executable,
                    str(load_script),
                    "--full-suite",
                    "--concurrent-scans",
                    str(concurrent_scans),
                    "--output",
                    "load_test_results.json",
                ],
                cwd=self.project_root,
                capture_output=True,
                text=True,
                timeout=1200,  # 20 minutes
            )

            duration = time.time() - start_time

            # Load results if available
            load_results = {}
            results_file = self.project_root / "load_test_results.json"
            if results_file.exists():
                try:
                    with open(results_file) as f:
                        load_results = json.load(f)
                except Exception as e:
                    logger.warning(f"Could not load test results: {e}")

            test_result = {
                "status": "passed" if result.returncode == 0 else "failed",
                "duration": duration,
                "return_code": result.returncode,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "load_results": load_results,
            }

            self.test_results["tests"]["load_tests"] = test_result

            if result.returncode == 0:
                logger.info(f"✅ Load tests passed in {duration:.2f}s")

                # Analyze load test results
                if load_results:
                    self._analyze_load_test_results(load_results)
            else:
                logger.error("❌ Load tests failed")
                self.test_results["issues_found"].append(
                    {
                        "type": "load_test_failure",
                        "description": "Load testing failed",
                        "details": result.stderr,
                    }
                )

        except subprocess.TimeoutExpired:
            logger.error("❌ Load tests timed out")
            self.test_results["tests"]["load_tests"] = {
                "status": "timeout",
                "duration": 1200,
                "error": "Load test execution timed out",
            }

        return self.test_results["tests"]["load_tests"]["status"] == "passed"

    def validate_security_configurations(self):
        """Validate security configurations."""
        logger.info("Validating security configurations...")

        issues = []

        # Check seccomp profiles
        seccomp_dir = self.project_root / "seccomp"
        required_profiles = [
            "default.json",
            "osv-scanner-seccomp.json",
            "semgrep-seccomp.json",
            "trivy-seccomp.json",
            "zap-seccomp.json",
        ]

        for profile in required_profiles:
            profile_path = seccomp_dir / profile
            if not profile_path.exists():
                issues.append(f"Missing seccomp profile: {profile}")
                continue

            try:
                with open(profile_path) as f:
                    profile_data = json.load(f)
                    if "syscalls" not in profile_data:
                        issues.append(f"Invalid seccomp profile format: {profile}")
            except json.JSONDecodeError:
                issues.append(f"Invalid JSON in seccomp profile: {profile}")

        # Note: Dockerfile has been removed - the project now focuses on Python package distribution
        # Container security is now handled at runtime by Podman when running individual security tools
        logger.info(
            "Docker container building disabled - using Python package distribution model"
        )

        # Check for hardcoded secrets in config files
        config_files = ["src/main.py", "projects.json", "pyproject.toml"]

        secret_patterns = ["password", "secret", "key", "token", "api_key"]

        for config_file in config_files:
            file_path = self.project_root / config_file
            if file_path.exists():
                content = file_path.read_text().lower()
                for pattern in secret_patterns:
                    if f"{pattern}=" in content or f'"{pattern}"' in content:
                        # This is just a warning for review
                        logger.warning(
                            f"Potential hardcoded secret in {config_file}: {pattern}"
                        )

        security_result = {
            "status": "passed" if not issues else "failed",
            "issues": issues,
            "checks_performed": len(required_profiles)
            + 1,  # profiles + secrets (removed dockerfile check)
            "issues_count": len(issues),
        }

        self.test_results["tests"]["security_validation"] = security_result

        if issues:
            logger.error(f"❌ Security validation failed with {len(issues)} issues")
            self.test_results["issues_found"].extend(
                [{"type": "security_issue", "description": issue} for issue in issues]
            )
        else:
            logger.info("✅ Security validation passed")

        return len(issues) == 0

    def validate_performance_requirements(self):
        """Validate performance requirements are met."""
        logger.info("Validating performance requirements...")

        # Check if load test results are available
        load_results = (
            self.test_results["tests"].get("load_tests", {}).get("load_results", {})
        )

        performance_issues = []

        if load_results:
            # Analyze concurrent scan performance
            for test in load_results.get("load_tests", []):
                if test.get("test_type") == "concurrent_scans":
                    avg_scan_time = test.get("average_scan_time", 0)
                    if avg_scan_time > 10.0:  # 10 seconds per scan is too slow
                        performance_issues.append(
                            f"Average scan time too slow: {avg_scan_time:.2f}s"
                        )

                    scans_per_second = test.get("scans_per_second", 0)
                    if scans_per_second < 0.1:  # Less than 1 scan per 10 seconds
                        performance_issues.append(
                            f"Scan throughput too low: {scans_per_second:.2f} scans/sec"
                        )

            # Check memory usage
            memory_metrics = load_results.get("performance_metrics", {}).get(
                "memory_stress", {}
            )
            if memory_metrics:
                memory_increase = memory_metrics.get("memory_increase_mb", 0)
                if memory_increase > 500:  # More than 500MB increase
                    performance_issues.append(
                        f"Memory usage too high: {memory_increase:.1f}MB increase"
                    )

            # Check report generation performance
            report_metrics = load_results.get("performance_metrics", {}).get(
                "report_generation", {}
            )
            for size, metrics in report_metrics.items():
                generation_time = metrics.get("generation_time", 0)
                findings_count = metrics.get("findings", 0)
                if findings_count > 0:
                    time_per_finding = generation_time / findings_count
                    if time_per_finding > 0.01:  # More than 10ms per finding
                        performance_issues.append(
                            f"Report generation too slow for {size}: {time_per_finding * 1000:.1f}ms per finding"
                        )

        else:
            performance_issues.append(
                "No load test results available for performance validation"
            )

        performance_result = {
            "status": "passed" if not performance_issues else "failed",
            "issues": performance_issues,
            "load_test_available": bool(load_results),
            "issues_count": len(performance_issues),
        }

        self.test_results["tests"]["performance_validation"] = performance_result

        if performance_issues:
            logger.error(
                f"❌ Performance validation failed with {len(performance_issues)} issues"
            )
            self.test_results["issues_found"].extend(
                [
                    {"type": "performance_issue", "description": issue}
                    for issue in performance_issues
                ]
            )
        else:
            logger.info("✅ Performance validation passed")

        return len(performance_issues) == 0

    def validate_code_quality(self):
        """Validate code quality using linting tools."""
        logger.info("Validating code quality...")

        # Run ruff for linting
        try:
            result = subprocess.run(
                [
                    "uv",
                    "run",
                    "ruff",
                    "check",
                    "src/",
                    "tests/",
                    "--output-format=json",
                ],
                cwd=self.project_root,
                capture_output=True,
                text=True,
                timeout=120,
            )

            lint_issues = []
            if result.stdout:
                try:
                    lint_data = json.loads(result.stdout)
                    lint_issues = lint_data if isinstance(lint_data, list) else []
                except json.JSONDecodeError:
                    pass

            # Run mypy for type checking
            mypy_result = subprocess.run(
                ["uv", "run", "mypy", "src/", "--ignore-missing-imports"],
                cwd=self.project_root,
                capture_output=True,
                text=True,
                timeout=120,
            )

            # Determine advisory vs pass: code quality should not block deployment
            has_issues = (
                (result.returncode != 0)
                or (mypy_result.returncode != 0)
                or (len(lint_issues) > 0)
            )
            code_quality_result = {
                # Mark as advisory when issues exist instead of failed (non-blocking)
                "status": "passed" if not has_issues else "advisory",
                "advisory": True if has_issues else False,
                "ruff_issues": len(lint_issues),
                "ruff_return_code": result.returncode,
                "mypy_return_code": mypy_result.returncode,
                "mypy_output": mypy_result.stdout + mypy_result.stderr,
            }

            self.test_results["tests"]["code_quality"] = code_quality_result

            total_issues = len(lint_issues)

            if not code_quality_result.get("advisory"):
                logger.info("✅ Code quality validation passed")
            else:
                logger.warning(
                    f"⚠️ Code quality issues found: {total_issues} lint issues"
                )
                if mypy_result.returncode != 0:
                    logger.warning("⚠️ Type checking issues found")
                    logger.warning(
                        f"Type checking issues: {(mypy_result.stdout + mypy_result.stderr)[:200]}"
                    )

        except (subprocess.TimeoutExpired, FileNotFoundError) as e:
            logger.warning(f"Code quality validation skipped: {e}")
            self.test_results["tests"]["code_quality"] = {
                "status": "skipped",
                "error": str(e),
            }

        return True  # Don't fail overall validation for code quality issues

    def _analyze_load_test_results(self, load_results):
        """Analyze load test results and provide insights."""

        insights = []

        # Analyze concurrent scan performance
        concurrent_tests = [
            t
            for t in load_results.get("load_tests", [])
            if t.get("test_type") == "concurrent_scans"
        ]

        if concurrent_tests:
            best_test = min(
                concurrent_tests, key=lambda x: x.get("average_scan_time", float("inf"))
            )
            worst_test = max(
                concurrent_tests, key=lambda x: x.get("average_scan_time", 0)
            )

            insights.append(
                f"Best concurrent performance: {best_test.get('average_scan_time', 0):.2f}s avg scan time"
            )
            insights.append(
                f"Worst concurrent performance: {worst_test.get('average_scan_time', 0):.2f}s avg scan time"
            )

        # Memory analysis
        memory_metrics = load_results.get("performance_metrics", {}).get(
            "memory_stress", {}
        )
        if memory_metrics:
            memory_efficiency = memory_metrics.get("memory_recovered", 0)
            if memory_efficiency > 0:
                insights.append(
                    f"Good memory management: {memory_efficiency:.1f}MB recovered"
                )
            else:
                insights.append("Memory leak detected: poor cleanup")

        self.test_results["load_test_insights"] = insights

    def generate_recommendations(self):
        """Generate recommendations based on test results."""

        recommendations = []

        # Analyze test results and generate recommendations
        if self.test_results["issues_found"]:
            issue_types = {}
            for issue in self.test_results["issues_found"]:
                issue_type = issue["type"]
                issue_types[issue_type] = issue_types.get(issue_type, 0) + 1

            for issue_type, count in issue_types.items():
                if issue_type == "unit_test_failure":
                    recommendations.append(
                        {
                            "priority": "high",
                            "category": "testing",
                            "description": f"Fix {count} unit test failures before deployment",
                        }
                    )
                elif issue_type == "security_issue":
                    recommendations.append(
                        {
                            "priority": "critical",
                            "category": "security",
                            "description": f"Address {count} security configuration issues",
                        }
                    )
                elif issue_type == "performance_issue":
                    recommendations.append(
                        {
                            "priority": "medium",
                            "category": "performance",
                            "description": f"Optimize performance to address {count} issues",
                        }
                    )

        # General recommendations
        if (
            not self.test_results["tests"].get("load_tests", {}).get("status")
            == "passed"
        ):
            recommendations.append(
                {
                    "priority": "high",
                    "category": "testing",
                    "description": "Run comprehensive load testing before production deployment",
                }
            )

        # Deployment readiness (exclude advisory/non-blocking checks like code_quality)
        critical_tests = {
            name: test
            for name, test in self.test_results["tests"].items()
            if not test.get("advisory", False)
        }
        passed_tests = sum(
            1 for test in critical_tests.values() if test.get("status") == "passed"
        )
        total_tests = len(critical_tests)

        if passed_tests == total_tests:
            recommendations.append(
                {
                    "priority": "info",
                    "category": "deployment",
                    "description": "All tests passed - system ready for production deployment",
                }
            )
        else:
            recommendations.append(
                {
                    "priority": "critical",
                    "category": "deployment",
                    "description": f"Only {passed_tests}/{total_tests} test suites passed - not ready for production",
                }
            )

        self.test_results["recommendations"] = recommendations

    def generate_summary(self):
        """Generate test execution summary."""

        # Only consider non-advisory (critical) tests when computing readiness
        critical_tests = {
            name: test
            for name, test in self.test_results["tests"].items()
            if not test.get("advisory", False)
        }
        total_tests = len(critical_tests)
        passed_tests = sum(
            1 for test in critical_tests.values() if test.get("status") == "passed"
        )
        failed_tests = sum(
            1 for test in critical_tests.values() if test.get("status") == "failed"
        )
        timeout_tests = sum(
            1 for test in critical_tests.values() if test.get("status") == "timeout"
        )

        total_duration = sum(
            test.get("duration", 0) for test in self.test_results["tests"].values()
        )

        issues_count = len(self.test_results["issues_found"])
        critical_issues = sum(
            1
            for rec in self.test_results.get("recommendations", [])
            if rec.get("priority") == "critical"
        )

        deployment_ready = passed_tests == total_tests and critical_issues == 0

        summary = {
            "total_test_suites": total_tests,
            "passed": passed_tests,
            "failed": failed_tests,
            "timeout": timeout_tests,
            "total_duration_seconds": total_duration,
            "issues_found": issues_count,
            "critical_issues": critical_issues,
            "deployment_ready": deployment_ready,
            "readiness_score": (passed_tests / total_tests * 100)
            if total_tests > 0
            else 0,
        }

        self.test_results["summary"] = summary

    def run_full_validation(self, quick_mode=False, load_test_concurrency=10):
        """Run complete production validation suite."""

        logger.info("🚀 Starting production deployment validation...")

        validation_start = time.time()

        # Step 1: Validate environment
        if not self.validate_environment():
            logger.error("❌ Environment validation failed - stopping")
            return False

        # Step 2: Run unit tests
        self.run_unit_tests()

        # Step 3: Run integration tests
        if not quick_mode:
            self.run_integration_tests()

        # Step 4: Run production-specific tests
        if not quick_mode:
            self.run_production_tests()

        # Step 5: Run load tests
        if not quick_mode:
            self.run_load_tests(load_test_concurrency)

        # Step 6: Validate security configurations
        self.validate_security_configurations()

        # Step 7: Validate performance requirements
        if not quick_mode:
            self.validate_performance_requirements()

        # Step 8: Code quality validation
        self.validate_code_quality()

        # Step 9: Generate recommendations
        self.generate_recommendations()

        # Step 10: Generate summary
        self.generate_summary()

        total_duration = time.time() - validation_start
        self.test_results["total_validation_duration"] = total_duration

        # Log summary
        summary = self.test_results["summary"]
        logger.info(f"""
=== PRODUCTION VALIDATION SUMMARY ===
Total Test Suites: {summary["total_test_suites"]}
✅ Passed: {summary["passed"]}
❌ Failed: {summary["failed"]}
⏱️ Timeout: {summary["timeout"]}
🐛 Issues Found: {summary["issues_found"]}
🚨 Critical Issues: {summary["critical_issues"]}
📈 Readiness Score: {summary["readiness_score"]:.1f}%
⏱️ Total Duration: {summary["total_duration_seconds"]:.1f}s

🚀 DEPLOYMENT READY: {"YES" if summary["deployment_ready"] else "NO"}
""")

        return summary["deployment_ready"]


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="GeoToolKit Production Deployment Validator"
    )
    parser.add_argument(
        "--full-test",
        action="store_true",
        help="Run complete validation suite (default)",
    )
    parser.add_argument(
        "--quick-test",
        action="store_true",
        help="Run quick validation (skip load tests and some checks)",
    )
    parser.add_argument(
        "--load-test", action="store_true", help="Run only load testing"
    )
    parser.add_argument(
        "--concurrent-scans",
        type=int,
        default=10,
        help="Number of concurrent scans for load testing (default: 10)",
    )
    parser.add_argument(
        "--output",
        default="production_validation_results.json",
        help="Output file for validation results",
    )

    args = parser.parse_args()

    # Default to full test if no specific mode chosen
    if not any([args.quick_test, args.load_test]):
        args.full_test = True

    validator = ProductionValidator()

    try:
        if args.load_test:
            # Run only load testing
            success = validator.run_load_tests(args.concurrent_scans)
        elif args.quick_test:
            # Run quick validation
            success = validator.run_full_validation(quick_mode=True)
        else:
            # Run full validation
            success = validator.run_full_validation(
                quick_mode=False, load_test_concurrency=args.concurrent_scans
            )

        # Save results
        with open(args.output, "w") as f:
            json.dump(validator.test_results, f, indent=2)

        logger.info(f"📄 Validation results saved to: {args.output}")

        if success:
            logger.info("🎉 Production validation PASSED - Ready for deployment!")
            return 0
        else:
            logger.error("💥 Production validation FAILED - NOT ready for deployment")
            return 1

    except KeyboardInterrupt:
        logger.info("Validation interrupted by user")
        return 130
    except Exception as e:
        logger.error(f"Validation failed with error: {e}")
        return 1


if __name__ == "__main__":
    exit(main())
