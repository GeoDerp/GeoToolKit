# GitHub Copilot Guides for GeoToolKit

This guide provides detailed instructions for developers working on GeoToolKit. It covers common workflows, development setup, and best practices for using the project's tools.

## 1. Development Environment Setup

Follow these steps to set up a local development environment for GeoToolKit.

### Prerequisites
- **Linux Host**: A Linux distribution like Fedora, Ubuntu, or Arch Linux.
- **Podman**: The container engine for running security tools.
- **Python 3.11+**: The core language for the project.
- **UV**: The recommended Python package manager.

### Installation Steps
1. **Clone the repository**:
   ```bash
   git clone https://github.com/GeoDerp/GeoToolKit.git
   cd GeoToolKit
   ```

2. **Create and activate a virtual environment**:
   ```bash
   uv venv
   source .venv/bin/activate
   ```

3. **Install dependencies**:
   ```bash
   uv sync
   ```

4. **Install pre-commit hooks** (optional but recommended):
   ```bash
   pre-commit install
   ```

## 2. Running Scans

GeoToolKit is primarily a command-line tool. Here’s how to run a scan.

### Configuration
1. **Edit `projects.json`**: This file defines the repositories to be scanned. Add a project entry with its URL, name, and language.
   ```json
   {
     "projects": [
       {
         "url": "https://github.com/example/project",
         "name": "example-project",
         "language": "Python"
       }
     ]
   }
   ```

2. **Offline Database**: For offline environments, you need to build the vulnerability database first.
   ```bash
   python scripts/build_offline_db.py --output data/offline-db.tar.gz
   ```

### Executing a Scan
Run the main script with the input and output paths:
```bash
python src/main.py --input projects.json --output report.md --database-path data/offline-db.tar.gz
```

### Timeouts and resource limits
Dynamic testing (DAST) and containerized scanners can hang or take a very long time against complex or misconfigured targets. Always configure reasonable timeouts and resource limits to prevent scans from running indefinitely.

Where to configure timeouts:
- `projects.json`: add a `timeouts` section per project to control DAST and overall scan timings.
- Environment variables or CLI flags: for global defaults (consider adding `--scan-timeout` to the CLI and respecting it in `Workflow`).

Example `projects.json` snippet with timeouts:
```json
{
  "projects": [
    {
      "url": "https://github.com/example/project",
      "name": "example-project",
      "language": "Python",
      "timeouts": {
        "dast_seconds": 300,
        "scan_seconds": 1800,
        "runner_seconds": 600
      }
    }
  ]
}
```

Implementation note for maintainers:
- `src/orchestration/workflow.py` and each runner (e.g., `zap_runner.py`) should read these timeout values and pass them to the container runtime (Podman) and any tool-specific timeout flags.
- For Podman, you can enforce timeouts by using subprocess timeouts or by running a controller that kills containers after the configured period.
- Prefer hard limits on CPU and memory for scans to avoid noisy neighbour effects (e.g., `--memory`, `--cpus` in Podman or equivalent).

Troubleshooting:
- If a DAST scan consistently hits the timeout, consider increasing the `dast_seconds` for that target or instrumenting the target to make testing easier (e.g., disable expensive background jobs).
- For flaky or slow scans, enable verbose logging in the runner to capture where time is being spent.

## 3. Working with Containers

All security tools are run in isolated Podman containers.

### Building Container Images
While pre-built images are used by default, you can build them locally if needed. The container definitions are not in the project, but you can pull them from their respective sources (e.g., Docker Hub).

### Security Best Practices
- **Rootless Containers**: Always run Podman in rootless mode.
- **Seccomp Profiles**: Use restrictive seccomp profiles to limit system calls. The profiles are located in the `seccomp/` directory.
- **Read-Only Filesystem**: Mount the project code as read-only in the container to prevent tampering.

## 4. Adding a New Security Tool

To integrate a new security scanner, follow these steps:

1. **Create a Runner**: Add a new runner script in `src/orchestration/runners/`. This script should handle running the tool in a Podman container and parsing its output.
2. **Update Workflow**: Integrate the new runner into the `Workflow` class in `src/orchestration/workflow.py`.
3. **Add a Seccomp Profile**: Create a new seccomp profile for the tool in the `seccomp/` directory.
4. **Update Documentation**: Add the new tool to the `README.md` and other relevant documentation.

## 5. MCP Server Usage

The Model Context Protocol (MCP) server provides a programmatic interface to GeoToolKit.

### Running the Server
The MCP server is a FastAPI application. To run it:
```bash
uvicorn mcp.server:app --host 0.0.0.0 --port 8000
```

### Interacting with the API
The server exposes endpoints for initiating scans and retrieving reports. You can interact with it using any HTTP client or the provided MCP client.

## 6. Troubleshooting

### Common Issues
- **Podman Errors**: Ensure the Podman service is running and you have the necessary permissions.
- **Python Dependencies**: If you encounter dependency issues, try recreating the virtual environment and running `uv sync`.
- **Offline Database**: Make sure the offline database is up-to-date. If not, rebuild it using the script.

### Getting Help
If you encounter an issue that is not covered here, please open an issue on the GitHub repository.
