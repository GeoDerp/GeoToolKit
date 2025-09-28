# GeoToolKit Installation & Usage Guide

## 🚀 Quick Start for Users

### CLI Tool Installation

**Option 1: From PyPI (when published)**
```bash
pip install geotoolkit
geotoolkit --input projects.json --output report.md --database-path data/offline-db.tar.gz
```

**Option 2: From GitHub Releases**
```bash
# Download the latest wheel from GitHub releases
pip install geotoolkit-*.whl
geotoolkit --input projects.json --output report.md --database-path data/offline-db.tar.gz
```

**Option 3: Development Installation**
```bash
git clone https://github.com/GeoDerp/GeoToolKit.git
cd GeoToolKit
pip install uv  # Modern Python package manager
uv sync
uv run geotoolkit --input projects.json --output report.md --database-path data/offline-db.tar.gz
```

### MCP Server Installation

The Model Context Protocol (MCP) server provides programmatic access to GeoToolKit features.

**Installation:**
```bash
# Install with MCP dependencies
uv sync --extra mcp

# Run MCP server
uv run python mcp/mcp_server.py
```

**Available Tools:**
- `createProjects(projects, outputPath?)` - Create and normalize projects.json
- `runScan(inputPath?, outputPath?, databasePath?)` - Execute security scan
- `normalizeProjects(inputPath?, outputPath?)` - Normalize network configurations

## 🔧 Key Changes Made

### Removed Docker Container Approach
- **Before**: Complex Dockerfile with multi-stage builds and container deployment
- **After**: Simple Python package installation with pip/uv

### Streamlined CI/CD
- **Before**: Docker image building, container registry publishing, container security scanning
- **After**: Python wheel/sdist building, GitHub releases, Python dependency scanning

### Simplified User Experience
- **Before**: Users needed to build Docker images or use complex container commands
- **After**: Standard `pip install` or `uv sync` for immediate usage

### Security Tools Still Containerized
- Security scanning tools (Semgrep, Trivy, OSV-Scanner, OWASP ZAP) still run in Podman containers for isolation
- Only the main GeoToolKit application distribution changed from containers to packages

## 📦 Distribution Artifacts

The project now produces these user-friendly artifacts:

1. **Python Wheel** (`geotoolkit-*.whl`) - Ready for `pip install`
2. **Source Distribution** (`geotoolkit-*.tar.gz`) - For development builds  
3. **MCP Server Package** (`geotoolkit-mcp-server-*.tar.gz`) - Standalone MCP server

## 🛡️ Security

- All packages are scanned with Semgrep and Trivy during CI/CD
- Python dependencies are security-checked
- Container isolation maintained for security tools
- No change to the actual security scanning capabilities