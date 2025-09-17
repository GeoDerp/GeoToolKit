# Data Model for Automated Malicious Code Scanner

## 1. Core Entities

### 1.1. `Project`
- **Description**: Represents a single source code repository to be scanned.
- **Attributes**:
    - `id` (string, UUID): Unique identifier for the project.
    - `url` (string): The Git URL of the repository.
    - `name` (string): The name of the repository.
    - `languages` (array of strings): A list of programming languages detected in the project.

### 1.2. `Scan`
- **Description**: Represents a single scan execution for a project.
- **Attributes**:
    - `id` (string, UUID): Unique identifier for the scan.
    - `projectId` (string, UUID): Foreign key to the `Project` entity.
    - `timestamp` (datetime): The time the scan was initiated.
    - `status` (string): The current status of the scan (e.g., "pending", "in_progress", "completed", "failed").
    - `results` (array of `Finding`): A list of findings from the scan.

### 1.3. `Finding`
- **Description**: Represents a single vulnerability or issue discovered by a tool.
- **Attributes**:
    - `id` (string, UUID): Unique identifier for the finding.
    - `tool` (string): The name of the tool that discovered the finding (e.g., "Semgrep", "Trivy", "OSV-Scanner", "OWASP ZAP").
    - `description` (string): A description of the finding.
    - `severity` (string): The severity level of the finding (e.g., "High", "Medium", "Low").
    - `filePath` (string): The path to the file where the finding was discovered.
    - `lineNumber` (integer): The line number of the finding.
    - `complianceMappings` (array of strings): A list of compliance frameworks the finding maps to (e.g., "NIST-800-53", "OWASP-Top-10-2021-A01").

## 2. Data Flow

1. The user provides a list of project URLs.
2. For each URL, a `Project` entity is created.
3. A `Scan` entity is created for each project.
4. The orchestration script executes the SAST, SCA, and DAST tools.
5. For each issue discovered by a tool, a `Finding` entity is created and associated with the current `Scan`.
6. After all scans are complete, the `Scan` entities are used to generate the final `Report`.

## 3. Report Structure

The final report will be a structured document (e.g., JSON or Markdown) containing the following information:

- A summary of the scan, including the number of projects scanned and the total number of findings.
- For each project:
    - The project name and URL.
    - A list of findings, grouped by severity.
    - For each finding, the details from the `Finding` entity.
