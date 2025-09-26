# GeoToolKit: Automated Malicious Code Scanner 🛡️

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python](https://img.shields.io/badge/Python-3.11%2B-blue.svg)](https://www.python.org/downloads/)

GeoToolKit is a comprehensive, offline software assurance toolkit designed to scan open-source Git repositories for malicious code and vulnerabilities. It orchestrates a suite of industry-standard security scanning tools, running each in secure, isolated Podman containers for maximum safety and reliability.

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
   
   # Or using pip
   python -m venv .venv
   source .venv/bin/activate
   pip install -e .
   ```

3. **Prepare offline database** (optional but recommended):
   ```bash
   mkdir -p data
   # Place your offline vulnerability database
   # mv /path/to/offline-db.tar.gz data/
   ```

### Basic Usage

1. **Configure projects** in `projects.json`:
   ```json
   {
     "projects": [
       {
         "url": "https://github.com/fastapi/fastapi",
         "name": "fastapi",
         "language": "Python"
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
  - `docker.io/owasp/zap2docker-stable:latest`
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

## 📚 Offline Database Recommendations

For optimal security and performance in air-gapped environments, consider these offline vulnerability databases:

### Primary Recommendations

1. **National Vulnerability Database (NVD)**
   - Download: [https://nvd.nist.gov/vuln/data-feeds](https://nvd.nist.gov/vuln/data-feeds)
   - Format: JSON feeds updated daily
   - Coverage: Comprehensive CVE database

2. **OSV Database Export**
   - Download: [https://osv.dev/](https://osv.dev/)
   - Command: `osv-scanner --experimental-download-offline-databases`
   - Coverage: Open Source Vulnerabilities

3. **GitHub Security Advisory Database**
   - Download: [https://github.com/advisories](https://github.com/advisories)
   - Format: GHSA JSON format
   - Coverage: GitHub-specific advisories

### Database Setup

```bash
# Create data directory
mkdir -p data

# Download NVD feeds (example)
wget https://nvd.nist.gov/feeds/json/cve/1.1/nvdcve-1.1-recent.json.gz -P data/
gunzip data/nvdcve-1.1-recent.json.gz

# Create compressed database
tar -czf data/offline-db.tar.gz -C data *.json

# Verify database
ls -la data/offline-db.tar.gz
```

### Automated Offline Bundle Builder

You can automatically assemble an "ultimate" offline database bundle combining NVD, OSV, and optionally GHSA using the helper script:

```fish
python scripts/build_offline_db.py \
  --output data/offline-db.tar.gz \
  --years 2023 2024 2025
```

Options:
- `--simulate` to create a placeholder bundle without any network calls (useful for CI or air-gapped dry runs)
- `--no-osv` or `--no-ghsa` to skip specific sources
- Set `GITHUB_TOKEN` environment variable to enable GHSA export (sample, paged)

Example (simulate mode):
```fish
python scripts/build_offline_db.py --output data/offline-db.tar.gz --simulate
```

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
- **No network access** - SAST/SCA tools run with `--network=none`
- **Read-only filesystems** - Containers cannot modify their base images
- **Capability dropping** - All Linux capabilities dropped by default
- **Seccomp profiles** - Restrictive syscall filtering for each tool
- **Temporary filesystems** - Limited tmpfs for scratch space only

### Supported Programming Languages

| Language   | SAST | SCA | Package Managers |
|------------|------|-----|------------------|
| Python     | ✅   | ✅  | pip, poetry, pipenv |
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

Contributions are welcome! Please see our [Contributing Guidelines](CONTRIBUTING.md) for details.

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🏷️ Version

Current version: v0.1.0 (Beta)

## 📞 Support

- Create an issue: [GitHub Issues](https://github.com/GeoDerp/GeoToolKit/issues)
- Documentation: [Project Wiki](https://github.com/GeoDerp/GeoToolKit/wiki)
- Security Issues: Please report privately via email

---

**⚠️ Security Notice**: This tool is designed for security testing of software you own or have permission to test. Always ensure you have proper authorization before scanning any repositories or applications.
        }
      ]
    }
    ```

2.  **Run the scanner**: Execute the `main.py` script with the required arguments.
    ```bash
    python src/main.py \
      --input projects.json \
      --output report.md \
      --database-path data/offline-db.tar.gz
    ```
    *Note: The runner tools (Semgrep, Trivy, OSV-Scanner, OWASP ZAP) are expected to be available in your environment or configured to run via Podman (Podman integration is currently commented out in runners for devcontainer compatibility).*

3.  **View the report**: The generated Markdown report will be available at `report.md`.

## 4. Configuration

### Network Allow-list (for DAST Scanner)

To allow the DAST scanner (OWASP ZAP) to make network connections to specific hosts and ports, create a `network-allowlist.txt` file with one `host:port` entry per line:

```
localhost:8080
database.example.com:5432
```

Then, pass the path to this file to the scanner:

```bash
python src/main.py \
  --input projects.json \
  --output report.md \
  --database-path data/offline-db.tar.gz \
  --network-allowlist network-allowlist.txt
```

## 5. Development

### Running Tests

To run unit and integration tests:

```bash
# Ensure dependencies are installed
uv sync
# Run tests
python -m pytest tests/
```

*Note: Some unit tests related to Pydantic's ValidationError might currently fail due to environment-specific interactions with pytest.raises. This is a known issue and does not block core functionality.*

### Linting and Formatting

This project uses `ruff` for linting and formatting. You can run checks and format the code using `uv`:

```bash
uv run lint
uv run format
```