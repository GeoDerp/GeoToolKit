# GeoToolKit Release Template

## 🛡️ GeoToolKit Security Scanner Release

### 📦 Distribution Packages

#### CLI Tool Package
- **Installation**: `uv pip install geotoolkit` or `pip install geotoolkit`
- **Entry Point**: `geotoolkit` command-line tool
- **Usage**: `geotoolkit --input projects.json --output report.md --database-path data/offline-db.tar.gz`

#### MCP Server Package
- **Entry Point**: `geotoolkit-mcp` or `python -m mcp.server`
- **Protocol**: Model Context Protocol server
- **Tools Available**:
  - `createProjects`: Create projects.json with network allowlist
  - `runScan`: Execute security scan and return report
  - `normalizeProjects`: Normalize existing projects.json

#### Container Image
- **Registry**: `ghcr.io/geoderp/geotoolkit:latest`
- **Usage**: `docker run -v $(pwd):/workspace ghcr.io/geoderp/geotoolkit:latest`

### 🔒 Security Features

- ✅ Semgrep static analysis scanning
- ✅ Trivy vulnerability scanning  
- ✅ Container security scanning
- ✅ Dependencies security validation
- ✅ SARIF output for GitHub Security tab

### 🚀 Installation Options

#### Quick Start
```bash
# Install CLI tool
uv pip install geotoolkit

# Run security scan
geotoolkit --input projects.json --output security-report.md --database-path data/offline-db.tar.gz
```

#### MCP Server Setup
```bash
# Start MCP server
geotoolkit-mcp

# Or run directly
python -m mcp.server
```

#### Docker Deployment
```bash
# Pull and run
docker pull ghcr.io/geoderp/geotoolkit:latest
docker run -v $(pwd):/workspace ghcr.io/geoderp/geotoolkit:latest
```

### 📝 Release Notes

<!-- Add specific changes, bug fixes, and new features here -->

### 🧪 Testing

All packages have been tested for:
- ✅ CLI functionality and entry points
- ✅ MCP server tools and manifest validation
- ✅ Container image functionality
- ✅ Package installation and imports
- ✅ Security scanning compliance

### 📋 Changelog

<!-- Add detailed changelog here -->

### 🔗 Links

- **Repository**: https://github.com/GeoDerp/GeoToolKit
- **Issues**: https://github.com/GeoDerp/GeoToolKit/issues
- **Documentation**: https://github.com/GeoDerp/GeoToolKit#readme