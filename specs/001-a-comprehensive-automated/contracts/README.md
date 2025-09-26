# API Contracts for Automated Malicious Code Scanner

This directory will contain the API contracts for the toolkit, defined using a format like OpenAPI or JSON Schema. These contracts will define the structure of the input and output data for the workflow.

For example, the input to the workflow could be a JSON file with the following structure:

```json
{
  "projects": [
    {
      "url": "https://github.com/example/project1"
    },
    {
      "url": "https://github.com/example/project2"
    }
  ]
}
```
## CLI Contract
 - Input: `projects.json` with shape `{ "projects": [ { "url": string, "name"?: string, "language"?: string, "description"?: string } ] }`
 - Options:
   - `--input <path>` (required)
   - `--output <path>` (required, Markdown file)
   - `--database-path <path>` (required for offline DB path; placeholder accepted)
   - `--network-allowlist <path>` (optional)
 - Output: Markdown report at `--output`, summarizing findings by severity and tool.

## Runner Contract
 - Each runner returns `list[Finding]` per invocation.
 - Runners must run tools in isolated Podman containers with seccomp and no network (except ZAP when performing DAST).

The output report could also be a JSON file, following the structure defined in the data model.
