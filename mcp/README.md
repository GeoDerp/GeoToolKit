# GeoToolKit MCP Server

Model Context Protocol (MCP) extension for GeoToolKit, implemented with FastMCP. It helps you:

- Create and normalize `projects.json`, including interpreting `network_config` into explicit allowlists
- Run GeoToolKit scans and return the report content to the client

## Requirements

- Python 3.11+
- The GeoToolKit repository (this project)
- Optional: `uv` for fast and reproducible execution

## Entry and Manifest

- Entry script: `mcp/server.py`
- Manifest: `mcp/manifest.json`

## Tools

1) createProjects
	 - Input: `{ projects: object[], outputPath?: string }`
	 - Behavior: Writes `projects.json` and, if a project contains a `network_config`, derives:
		 - `network_allow_hosts`: host:port entries
		 - `network_allow_ip_ranges`: CIDR ranges
		 - `ports`: service ports
	 - Output: `{ ok, path, project_count }`

2) normalizeProjects
	 - Input: `{ inputPath?: string, outputPath?: string }`
	 - Behavior: Reads an existing `projects.json`, interprets `network_config` into the explicit fields above, and writes the result.
	 - Output: `{ ok, path, preview }` where `preview` shows a few derived hosts, cidrs, and ports per project.

3) runScan
	 - Input: `{ inputPath?: string, outputPath?: string, databasePath?: string }`
	 - Behavior: Executes `src.main` via `uv run` if available (fallback to `python -m src.main`), returning the report content.
	 - Output: `{ exitCode, report, log }`

## Interpreting network_config

When present in a project object, `network_config` is normalized into allowlists used by DAST:

```
network_config: {
	ports: ["3000", "8080"],
	protocol: "http" | "https",
	health_endpoint: "/health",
	startup_time_seconds: 30,
	allowed_egress: {
		"localhost": ["3000"],
		"192.168.1.0/24": ["8080"],
		"external_hosts": ["example.com"]
	}
}
```

Normalization rules:
- external_hosts → host:port using `network_config.ports` if present, else default 80/443 by protocol
- map keys that look like hosts/IPs → host:port for each listed port (or the same fallback)
- keys containing `/` are treated as CIDR ranges and added to `network_allow_ip_ranges`

The explicit fields can also be provided directly and take precedence over derived values.

## How GeoToolKit uses allowlists

- `src/main.py` merges per-project allowlists and passes them to DAST (OWASP ZAP). CIDR ranges are included so runners can apply egress controls.
- When ports are present, `localhost:PORT` and `127.0.0.1:PORT` entries are automatically included to ease local testing.

## Example

Input project:

```
{
	"url": "https://github.com/postmanlabs/httpbin",
	"name": "httpbin",
	"network_config": {
		"ports": ["8000"],
		"protocol": "http",
		"allowed_egress": {
			"localhost": ["8000"],
			"external_hosts": ["example.com"]
		}
	}
}
```

Derived fields:

```
network_allow_hosts: ["localhost:8000", "example.com:8000"]
network_allow_ip_ranges: []
ports: ["8000"]
```

## Running

You can start the MCP server directly for local testing:

```
uv run python mcp/server.py
```

Clients can invoke the tools declared in `mcp/manifest.json`. When integrated, call `createProjects` or `normalizeProjects` before `runScan`.

