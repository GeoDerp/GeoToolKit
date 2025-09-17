# Research & Analysis for Automated Malicious Code Scanner

## 1. Key Technical Challenges

### 1.1. Offline Operation
- **Challenge**: All specified tools (Semgrep, Trivy, OSV-Scanner, OWASP ZAP) require up-to-date vulnerability databases and rule sets. Operating offline means these databases must be pre-packaged or loaded from a local source.
- **Questions**:
    - How will the vulnerability databases and rule sets for each tool be updated in an offline environment?
    - What is the process for packaging these databases for distribution with the toolkit?

### 1.2. Sandbox Environment
- **Challenge**: Configuring a rootless Podman sandbox with restrictive seccomp profiles and a custom host-only network bridge requires careful setup and scripting.
- **Questions**:
    - What specific seccomp profile will be used?
    - How will the user specify the allow-list for ports and protocols for the host-only network?
    - How will the toolkit manage the lifecycle of the Podman containers?

### 1.3. Tool Orchestration
- **Challenge**: The workflow requires orchestrating multiple tools, each with its own command-line interface and output format. The outputs need to be parsed and consolidated into a single report.
- **Questions**:
    - What data format will be used for the intermediate results from each tool?
    - How will the final report be structured to accommodate findings from different tools?

### 1.4. Language Support
- **Challenge**: The feature specification requires support for "major programming languages." The selected tools have varying levels of support for different languages.
- **Questions**:
    - Which specific languages will be supported in the initial version?
    - How will the toolkit handle projects that contain multiple languages?

## 2. Proposed Solutions

### 2.1. Offline Operation
- **Solution**: The toolkit will include a separate script to download and package the latest vulnerability databases and rule sets for all tools. This package can then be distributed and used by the offline scanner. The scanner will have a command-line option to specify the path to this package.

### 2.2. Sandbox Environment
- **Solution**: A series of shell scripts will be created to manage the Podman sandbox. A default seccomp profile will be provided, with the option for the user to specify a custom profile. The network allow-list will be configured via a simple text file.

### 2.3. Tool Orchestration
- **Solution**: A main workflow script (e.g., in Bash or Python) will orchestrate the execution of the tools. Each tool will be configured to output its results in a machine-readable format (e.g., JSON). These JSON outputs will then be parsed and transformed into a standardized format before being used to generate the final report.

### 2.4. Language Support
- **Solution**: The initial version will focus on a core set of languages supported by all the selected tools (e.g., Python, JavaScript, Go, Java). The toolkit will detect the language of a project and only run the relevant tools.

## 3. Open Questions & Risks
- **Risk**: The size of the offline vulnerability database package could be very large.
- **Question**: How will the mapping of vulnerabilities to compliance frameworks (NIST, ISM, OWASP Top 10) be implemented? This will likely require a separate database or mapping file.
- **Question**: What are the performance implications of running multiple scans on large codebases?
