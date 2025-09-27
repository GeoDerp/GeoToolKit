# GeoToolKit: Automated Security Scanner 🛡️

[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](https://opensource.org/licenses/MIT)
[![Python](https://img.shields.io/badge/Python-3.11%2B-blue.svg)](https://www.python.org/downloads/)

GeoToolKit is a comprehensive, offline software assurance toolkit designed to scan open-source Git repositories for malicious code and vulnerabilities. It orchestrates industry-standard security scanning tools, running each in secure, isolated Podman containers for maximum safety and reliability.

## ✨ Features

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

### Model Context Protocol (MCP) Server

An optional FastMCP server is provided to programmatically manage `projects.json` and run scans. It can interpret `network_config` blocks into explicit allowlists for DAST. See the full guide in `mcp/README.md`.

```bash
# Start MCP server (requires fastmcp)
uv run python mcp/server.py
```

Tools:
- `createProjects(projects, outputPath?)` → writes projects.json and normalizes any `network_config` into `network_allow_hosts`, `network_allow_ip_ranges`, and `ports`
- `normalizeProjects(inputPath?, outputPath?)` → reads an existing projects.json and derives explicit allowlists from `network_config`
- `runScan(inputPath?, outputPath?, databasePath?)` → runs the scan and returns report text

Quick note on `network_config` interpretation:
- `allowed_egress.external_hosts` are turned into `host:port` using `network_config.ports` or protocol defaults (80/443)
- Other keys under `allowed_egress` are treated as hostnames/IPs; keys containing `/` are treated as CIDRs and added to `network_allow_ip_ranges`

### Validation (Multi-language quick test)

Try with the included `test-projects.json` to validate Python and Go scanning quickly:

```bash
python src/main.py --input test-projects.json --output quick-report.md --database-path data/offline-db.tar.gz
```

### Troubleshooting

- If containers fail to start due to seccomp paths, ensure the profiles exist at `seccomp/*.json` and you have Podman installed.
- If image pulls are blocked (e.g., corporate network), pre-pull required images:
  - `docker.io/semgrep/semgrep`
  - `docker.io/aquasec/trivy`
  - `ghcr.io/ossf/osv-scanner:latest`
  - `ghcr.io/zaproxy/zaproxy:latest`
- For strictly offline environments, consider mirroring images to a local registry and using Podman’s `--registries-conf`.

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

- Semgrep (SAST)
  - SEMGREP_PACK: When set, runs Semgrep using this config pack.
  - SEMGREP_NETWORK: Podman network mode for Semgrep container. Defaults to --network=none for isolation. Avoid host networking.

Security note: Host networking is intentionally avoided by default. Explicitly opt into networked modes only when required and understood.

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

### Troubleshooting

- If containers fail to start, ensure Podman is installed and seccomp profiles exist at `seccomp/*.json`
- For corporate networks with blocked image pulls, pre-pull required images:
  - `docker.io/semgrep/semgrep`
  - `docker.io/aquasec/trivy`
  - `ghcr.io/ossf/osv-scanner:latest`
  - `docker.io/owasp/zap2docker-stable:latest`
- For strictly offline environments, consider mirroring images to a local registry

## 🛠️ Development

### Running Tests

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

## 🤝 Contributing

Contributions are welcome! Please follow these guidelines:

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add or update tests
5. Ensure all tests pass
6. Submit a pull request

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
- **Documentation**: [Project Wiki](https://github.com/GeoDerp/GeoToolKit/wiki)
- **Security Issues**: Please report privately via email

---

**⚠️ Security Notice**: This tool is designed for security testing of software you own or have permission to test. Always ensure you have proper authorization before scanning any repositories or applications.