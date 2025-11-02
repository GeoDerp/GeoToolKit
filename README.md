<h1 >GeoToolKit — Automated Security Scanner 🛡️</h1>
<p >Podman-based orchestration for SAST, SCA, and DAST — automated security scanning and reporting for Git repositories.</p>

[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](https://opensource.org/licenses/MIT)
[![Python](https://img.shields.io/badge/Python-3.11%2B-blue.svg)](https://www.python.org/downloads/)

---

GeoToolKit is a comprehensive, offline software assurance toolkit designed to scan open-source Git repositories for malicious code and vulnerabilities. It orchestrates industry-standard security scanning tools, running each in secure, isolated Podman containers for maximum safety and reliability.



- **🔒 Secure Container Execution**: All scanning tools run in locked-down, rootless Podman containers with restrictive seccomp profiles
- **🌐 Multi-Language Support**: Scans projects in Python, JavaScript, TypeScript, Java, Go, Ruby, C#, PHP, and more
- **📊 Comprehensive Analysis**: 
  - **SAST** (Static Application Security Testing) with Semgrep
  - **SCA** (Software Composition Analysis) with Trivy and OSV-Scanner
  - **DAST** (Dynamic Application Security Testing) with OWASP ZAP
- **🚫 Offline Operation**: Designed for air-gapped environments with offline vulnerability databases
- **📋 Professional Reporting**: Generates structured Markdown reports with risk levels and compliance mapping
- **⚡ Automated Workflow**: Clone, scan, report - fully automated from start to finish

## 🏗️ Architecture

```
┌─────────────────┐    ┌──────────────┐    ┌─────────────────┐
│   Git Repos     │───▶│  GeoToolKit  │───▶│  Security Report│
└─────────────────┘    └──────────────┘    └─────────────────┘
                              │
          ┌───────────────────┼───────────────────┐
          │                   │                   │
          ▼                   ▼                   ▼
    ┌──────────┐        ┌──────────┐        ┌──────────┐
    │ Semgrep  │        │  Trivy   │        │OSV-Scan  │
    │Container │        │Container │        │Container │
    └──────────┘        └──────────┘        └──────────┘
                              │
                              ▼
                        ┌──────────┐
                        │OWASP ZAP │
                        │Container │
                        └──────────┘
```

## 🚀 Quick Start

### Prerequisites

- **Linux Host** (Fedora, OpenSUSE, Ubuntu, etc.)
- **Podman** installed and configured
- **Python 3.11+**
- **uv** package manager (recommended)

### Installation

#### Quick Installation (for users)

If you just want to use GeoToolKit without development setup:

```bash
# Install from PyPI (when published)
pip install geotoolkit

# Or install from GitHub releases
pip install https://github.com/GeoDerp/GeoToolKit/releases/latest/download/geotoolkit-*.whl

# Run the CLI
geotoolkit --input projects.json --output report.md --database-path data/offline-db.tar.gz
```
#### Run the MCP server (optional)

You can start the Model Context Protocol (MCP) server to manage `projects.json` and trigger scans programmatically.

From an installed environment (preferred):
```bash
# Start built-in MCP server (default host 127.0.0.1, default port 9000)
# --mcp-server enables MCP mode; --mcp-host/--mcp-port override listen address.
geotoolkit --mcp-server --mcp-host 127.0.0.1 --mcp-port 9000 --database-path data/offline-db.tar.gz
```

Quick API example:
```bash
# Trigger a scan by POSTing a projects.json (server returns report text)
curl -s -X POST "http://127.0.0.1:9000/runScan" \
  -H "Content-Type: application/json" \
  --data-binary @projects.json > security-report.md
```

Example MCP propts 
```
createProjects from txt list
```
*Generates projects.json from a list of github repos

```
runScan
```
Runns GeoToolKit scanner with projects.json file 

#### Development Installation

For development:

1. **Clone the repository**:
   ```bash
   git clone https://github.com/GeoDerp/GeoToolKit.git
   cd GeoToolKit
   ```

2. **Set up Python environment**:
   ```bash
   # Using uv (recommended)
   uv venv
   source .venv/bin/activate
   uv sync
   
   # For MCP server support
   uv sync --extra mcp
   
   <!-- # Or using pip
   python -m venv .venv
   source .venv/bin/activate
   pip install -e . -->
   ```

3. **Prepare offline database** (optional but recommended):
   ```bash
   mkdir -p data
   # Use the automated builder script
   python scripts/build_offline_db.py --output data/offline-db.tar.gz --simulate
   ```

### Basic Usage

1. **Configure projects** in `projects.json` (with optional inline network allowlist for DAST):
   ```json
   {
     "projects": [
       {
         "url": "https://github.com/fastapi/fastapi",
         "name": "fastapi",
         "language": "Python",
         "description": "Modern, fast web framework",
         "ports": ["8000"],
         "network_allow_hosts": ["127.0.0.1:8000", "localhost:8000"],
         "network_allow_ip_ranges": ["127.0.0.1/32"]
       }
     ]
   }
   ```

2. **Run the scanner**:
   ```bash
   python src/main.py \
     --input projects.json \
     --output security-report.md \
     --database-path data/offline-db.tar.gz
   ```

## ✅ Recent scan verification (default workflow)

The default workflow now includes the following behavior which has been validated in local runs:

- Semgrep (SAST) runs against the cloned repository and reports findings (example: Semgrep reported 18 findings when run against the Juice Shop sample project).
- Trivy (SCA) mounts a Trivy cache when `TRIVY_CACHE_DIR` or `GEOTOOLKIT_TRIVY_CACHE_DIR` is provided. When `GEOTOOLKIT_TRIVY_OFFLINE=1` is set and no cache is present, Trivy will skip to avoid attempting DB downloads in air-gapped CI.
- OSV-Scanner (SCA) uses an explicit image if `OSV_IMAGE` is set. We recommend setting:

```bash
export OSV_IMAGE=ghcr.io/google/osv-scanner:latest
```

  If OSV cannot find package manifests in the repository it will report "No package sources found" (this is expected for repositories without package metadata). For offline CI use, prepare an OSV offline DB and set `GEOTOOLKIT_OSV_OFFLINE=1` and `GEOTOOLKIT_OSV_OFFLINE_DB=/path/to/osv_offline.db` (see Offline Artifacts section).

- DAST (OWASP ZAP) will be run when a project configuration includes a reachable network allowlist and ports (for example, when using `validation/configs/container-projects.json` to start a local Juice Shop target). Recommended ZAP environment tunables (already used in validation runs):

```bash
export ZAP_SPIDER_TIMEOUT=120
export ZAP_ASCAN_TIMEOUT=600
export ZAP_READY_TIMEOUT=300
```

This ensures ZAP has enough time to start and perform longer scans in CI.

If you run a full end-to-end validation locally, start the DAST target first:

```bash
python3 scripts/start_dast_targets.py validation/configs/container-projects.json
```

Then run the scanner:

```bash
export OSV_IMAGE=ghcr.io/google/osv-scanner:latest
export ZAP_SPIDER_TIMEOUT=120
export ZAP_ASCAN_TIMEOUT=600
export ZAP_READY_TIMEOUT=300
PYTHONPATH=. python3 -m src.main --input validation/configs/container-projects.json --output validation/reports/security-report.md --database-path data/offline-db.tar.gz
```

If you observe that Trivy attempted to download DB updates in a restricted environment, prepare an offline Trivy cache using `scripts/prepare_offline_artifacts.sh` and set `TRIVY_CACHE_DIR` in your CI.


### Model Context Protocol (MCP) Server

An optional FastMCP server is provided to programmatically manage `projects.json` and run scans. It can interpret `network_config` blocks into explicit allowlists for DAST. See the full guide in `mcp_server/README.md`.

The recommended way to run the server is via the main CLI:
```bash
# Start built-in MCP server (requires mcp dependencies)
# The --mcp-server flag enables MCP mode.
geotoolkit --mcp-server --mcp-host 127.0.0.1 --mcp-port 9000 --database-path data/offline-db.tar.gz
```

For development, you can also run the server script directly:
```bash
# Start MCP server directly (requires fastmcp)
uv run python mcp_server/mcp_server.py
```

Tools:
- `createProjects(projects, outputPath?)` → writes `projects.json` and normalizes any `network_config` into `network_allow_hosts`, `network_allow_ip_ranges`, and `ports`.
- `normalizeProjects(inputPath?, outputPath?)` → reads an existing `projects.json` and derives explicit allowlists from `network_config`.
- `runScan(inputPath?, outputPath?, databasePath?)` → runs the scan and returns the report text as a string.

Quick note on `network_config` interpretation:
- `allowed_egress.external_hosts` are turned into `host:port` using `network_config.ports` or protocol defaults (80/443)
- Other keys under `allowed_egress` are treated as hostnames/IPs; keys containing `/` are treated as CIDRs and added to `network_allow_ip_ranges`

### Validation (Multi-language quick test)

Try with the included `test-projects.json` to validate Python and Go scanning quickly:

```bash
# Quick CLI smoke test using included test-projects.json
python src/main.py --input test-projects.json --output quick-report.md --database-path data/offline-db.tar.gz

# End-to-end validation helpers
python scripts/quick_validation.py
python scripts/validation_executor.py
```

### Troubleshooting

- If containers fail to start due to seccomp paths, ensure the profiles exist at `seccomp/*.json` and you have Podman installed.
- If image pulls are blocked (e.g., corporate network), pre-pull required images:
  - `docker.io/semgrep/semgrep`
  - `docker.io/aquasec/trivy`
  - `ghcr.io/ossf/osv-scanner:latest`
  - `ghcr.io/zaproxy/zaproxy:latest`
- For strictly offline environments, consider mirroring images to a local registry and using Podman's `--registries-conf`.

#### Podman Hanging or Stuck Containers

If you interrupt a scan (Ctrl+C) or encounter Podman commands hanging:

1. **Check for stuck processes:**
   ```bash
   ps aux | grep podman | grep -v grep
   ```

2. **Kill stuck Podman processes:**
   ```bash
   # Kill any hanging podman commands
   pkill -9 podman
   ```

3. **Restart Podman socket:**
   ```bash
   systemctl --user restart podman.socket
   ```

4. **Clean up containers:**
   ```bash
   # Remove stopped containers
   podman container prune -f
   
   # Remove all containers (if safe to do so)
   podman rm -f $(podman ps -aq)
   ```

5. **Verify Podman is working:**
   ```bash
   podman ps
   podman version
   ```

**Prevention:** Always allow scans to complete gracefully. The ZAP runner includes timeout protection (configurable via `ZAP_SPIDER_TIMEOUT`, `ZAP_ASCAN_TIMEOUT`, and `ZAP_READY_TIMEOUT` environment variables) to prevent infinite hangs.

3. **View the results**: Open `security-report.md` in your favorite editor

## 🔧 Configuration

### Projects Configuration

The `projects.json` file supports the following format:

```json
{
  "projects": [
    {
      "url": "https://github.com/owner/repo",
      "name": "project-name",
      "language": "Programming Language",
      "description": "Brief description (optional)"
    }
  ]
}
```

### Network Allow-list (for DAST)

For Dynamic Application Security Testing with OWASP ZAP, create a `network-allowlist.txt`:

```
localhost:8080
api.example.com:443
database.internal:5432
```

Then run with:
```bash
python src/main.py \
  --input projects.json \
  --output report.md \
  --database-path data/offline-db.tar.gz \
  --network-allowlist network-allowlist.txt
```

### Environment Variables

You can tune container networking and authentication via environment variables. Sensible, secure defaults are used when not set.

- ZAP (DAST)
  - ZAP_API_KEY: If set, the ZAP container is started with API key authentication enabled and the provided key configured.
  - ZAP_DISABLE_API_KEY: Set to 1/true to explicitly disable API key auth. Avoid in production.
  - ZAP_PORT: Local port to expose the ZAP API (default 8080).
  - ZAP_IMAGE: Container image to use (default ghcr.io/zaproxy/zaproxy:latest).
  - ZAP_BASE_URL: Connect to an existing ZAP instance instead of starting a container.
  - ZAP_PODMAN_NETWORK: Podman --network value to use (e.g., bridge). Optional.
  - ZAP_PODMAN_PULL: Podman --pull policy: always|missing|never (default missing).
  - ZAP_PODMAN_ARGS: Extra Podman args appended as-is.
  - CONTAINER_HOST_HOSTNAME: Hostname used inside containers to reach the host (default host.containers.internal). Set for environments where the default isn't available.

Additional runtime recommendations
-------------------------------

- If you encounter registry access errors pulling OSV images, set an explicit image that is reachable from your host, for example:

```bash
export OSV_IMAGE=ghcr.io/google/osv-scanner:latest
```

- For longer or more thorough ZAP scans, tune these environment variables (defaults used by GeoToolKit):

```bash
export ZAP_SPIDER_TIMEOUT=120   # seconds (default used by toolkit)
export ZAP_ASCAN_TIMEOUT=600    # seconds (default used by toolkit)
export ZAP_READY_TIMEOUT=300    # seconds (default used by toolkit)
```

- Semgrep (SAST)
  - SEMGREP_PACK: When set, runs Semgrep using this config pack.
  - SEMGREP_NETWORK: Podman network mode for Semgrep container. Defaults to --network=none for isolation. Avoid host networking.

Security note: Host networking is intentionally avoided by default. Explicitly opt into networked modes only when required and understood.

## 📚 Offline Artifacts (Trivy & OSV)

For air-gapped or restricted CI environments, GeoToolKit can operate fully offline using pre-generated artifact bundles. This eliminates network dependencies and significantly speeds up scan execution.

### Quick Setup (Recommended)

1. **Generate artifacts** on a networked host:

```bash
bash scripts/prepare_offline_artifacts.sh data/offline-artifacts
```

This creates:
- `trivy-cache.tgz` - Trivy vulnerability database (~75-80 MB)
- `osv_offline.db` - OSV vulnerability database (if available)

2. **Extract and configure** in your GeoToolKit workspace:

```bash
# Extract Trivy cache
mkdir -p data/trivy-cache
tar -xzf data/offline-artifacts/trivy-cache.tgz -C data/trivy-cache

# Move OSV database (if available)
mv data/offline-artifacts/osv_offline.db data/osv_offline.db
```

3. **Set environment variables** (already configured in `run_production_test.sh`):

```bash
# Trivy offline mode
export TRIVY_CACHE_DIR="$(pwd)/data/trivy-cache"
export GEOTOOLKIT_TRIVY_OFFLINE=1

# OSV offline mode (if database available)
export GEOTOOLKIT_OSV_OFFLINE=1
export GEOTOOLKIT_OSV_OFFLINE_DB="$(pwd)/data/osv_offline.db"
```

4. **Run scans** - GeoToolKit will automatically use offline databases:

```bash
bash run_production_test.sh
# Or directly:
python -m src.main --input projects.json --output report.md --database-path data/offline-db.tar.gz
```

### CI/CD Integration

For CI environments, upload artifacts to your CI storage and extract before scanning:

```bash
# In your CI pipeline (e.g., GitHub Actions, GitLab CI)
mkdir -p /workspace/trivy-cache
tar -xzf trivy-cache.tgz -C /workspace/trivy-cache

export TRIVY_CACHE_DIR=/workspace/trivy-cache
export GEOTOOLKIT_TRIVY_OFFLINE=1

# If OSV database available:
export GEOTOOLKIT_OSV_OFFLINE=1
export GEOTOOLKIT_OSV_OFFLINE_DB=/workspace/osv/osv_offline.db
```

### Verification

Confirm your offline setup is working correctly:

```bash
# Check Trivy cache structure
ls -lh data/trivy-cache/db/
# Should show: trivy.db (~780 MB) and metadata.json

# Check OSV database (optional)
ls -lh data/osv_offline.db
```

### Benefits

- **No network access required** - Scans work in fully air-gapped environments
- **Faster execution** - No database downloads during scans (saves ~5-10 seconds per project)
- **Predictable results** - Same vulnerability data across all runs until you update artifacts
- **Reduced failures** - No network timeouts or registry access issues

### Updating Artifacts

Regenerate artifacts periodically (weekly/monthly) to get latest vulnerability data:

```bash
# On networked host
bash scripts/prepare_offline_artifacts.sh data/offline-artifacts

# Distribute updated artifacts to your CI/development environments
```

### Troubleshooting

**Trivy complains about missing database:**
- Verify `data/trivy-cache/db/trivy.db` and `data/trivy-cache/db/metadata.json` exist
- Ensure `TRIVY_CACHE_DIR` points to the extracted cache directory (not the .tgz file)
- Check file permissions - Trivy needs read access to cache files

**OSV Scanner skips scanning:**
- This is expected if `data/osv_offline.db` doesn't exist
- OSV artifact generation requires specific OSV Scanner versions - check `scripts/prepare_offline_artifacts.sh` output
- You can still get SCA coverage from Trivy without OSV

**Performance still slow:**
- Verify environment variables are set correctly before running scans
- Check that large repos aren't being cloned repeatedly (use local paths if testing)
- Consider using `validation/configs/production-mcp-projects.json` instead of full `production-projects.json` for faster iteration

For detailed offline operation documentation, see `docs/OFFLINE.md`.

## 📚 Offline Database Setup

For optimal security and performance in air-gapped environments, GeoToolKit supports offline vulnerability databases.

### Automated Database Builder

You can automatically assemble an offline database bundle combining multiple vulnerability sources:

```bash
# Create a comprehensive offline database
python scripts/build_offline_db.py \
  --output data/offline-db.tar.gz \
  --years 2023 2024 2025

# For air-gapped environments (simulation mode)
python scripts/build_offline_db.py --output data/offline-db.tar.gz --simulate
```

**Options:**
- `--simulate`: Create a placeholder bundle without network calls (useful for CI or air-gapped environments)
- `--no-osv` or `--no-ghsa`: Skip specific vulnerability sources
- Set `GITHUB_TOKEN` environment variable to enable GitHub Security Advisory export

### Manual Database Setup

For manual database configuration:

1. **National Vulnerability Database (NVD)**
   - Download: [https://nvd.nist.gov/vuln/data-feeds](https://nvd.nist.gov/vuln/data-feeds)

2. **OSV Database**
   - Command: `osv-scanner --experimental-download-offline-databases`

3. **GitHub Security Advisories**
   - Download: [https://github.com/advisories](https://github.com/advisories)

## 🛠️ Development

### Running Tests

Contributing and development notes are available in `CONTRIBUTING.md`.

If your shell is fish (the default for some developers), use syntax compatible with fish when following examples in CI snippets (for example, use `env VAR=value command` or `set -x VAR value; command`).

```bash
# Run all tests
python -m pytest tests/

# Run with coverage
python -m pytest tests/ --cov=src --cov-report=html

# Run specific test suite
python -m pytest tests/unit/
python -m pytest tests/integration/
```

### Code Quality

```bash
# Lint and format
uv run ruff check src/ tests/
uv run ruff format src/ tests/

# Type checking
uv run mypy src/
```

### Adding New Scanners

1. Create a new runner in `src/orchestration/runners/`
2. Implement the `run_scan()` method
3. Add parsing logic in `src/orchestration/parser.py`
4. Add appropriate seccomp profile in `seccomp/`
5. Update workflow in `src/orchestration/workflow.py`

## 🔐 Security Features

### Container Security

- **Rootless execution** - All containers run without root privileges
- **Network isolation** - SAST/SCA tools run with `--network=none`
- **Read-only filesystems** - Containers cannot modify their base images
- **Capability dropping** - All Linux capabilities dropped by default
- **Seccomp profiles** - Restrictive syscall filtering for each tool
- **Temporary filesystems** - Limited tmpfs for scratch space only

### Supported Programming Languages

| Language   | SAST | SCA | Package Managers |
|------------|------|-----|------------------|
| Python     | ✅   | ✅  | pip, poetry, pipenv, uv |
| JavaScript | ✅   | ✅  | npm, yarn, pnpm |
| TypeScript | ✅   | ✅  | npm, yarn, pnpm |
| Java       | ✅   | ✅  | maven, gradle |
| Go         | ✅   | ✅  | go modules |
| Ruby       | ✅   | ✅  | bundler, gems |
| C#         | ✅   | ✅  | nuget, paket |
| PHP        | ✅   | ✅  | composer |
| Rust       | ✅   | ✅  | cargo |
| C/C++      | ✅   | ✅  | conan, vcpkg |

## 📊 Report Format

The generated reports include:

- **Executive Summary** - High-level findings overview
- **Project Details** - Scanned repositories and metadata
- **Vulnerability Analysis** - Detailed findings with severity levels
- **Compliance Mapping** - NIST, OWASP Top 10, ISM alignment
- **Recommendations** - Actionable remediation steps

### Development Setup

```bash
# Install development dependencies
uv sync --dev

# Run pre-commit hooks
uv run ruff check --fix src/ tests/
uv run ruff format src/ tests/
```

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🏷️ Version

Current version: **v0.1.0** (Beta)

## 📞 Support

- **Issues**: [GitHub Issues](https://github.com/GeoDerp/GeoToolKit/issues)
- **Security Issues**: Please report privately via email

---

**⚠️ Security Notice**: This tool is designed for security testing of software you own or have permission to test. Always ensure you have proper authorization before scanning any repositories or applications.

## 🙌 Shoutouts

Big thanks to the open-source security scanners and projects that make GeoToolKit possible:

- Semgrep — powerful, fast SAST (https://semgrep.dev)
- Trivy — container and dependency SCA from Aqua Security (https://github.com/aquasecurity/trivy)
- OSV-Scanner — offline scanner that uses Google’s OSV (Open Source Vulnerabilities) data to detect known vulnerabilities in packages and SBOMs (https://github.com/ossf/osv-scanner)
- OWASP ZAP — DAST tooling from the OWASP project (https://www.zaproxy.org/)

If you've contributed integrations for other scanners or tools, thank you — please add them to this list by submitting a PR.

## 🤖 AI assistance

This project was developed with assistance from AI tools to speed up development and help generate documentation and examples. All code and contributions were reviewed by human maintainers. If you have questions about any part of the codebase or believe an AI-assisted change needs clarification, please open an issue or a pull request so maintainers can review and address it.
