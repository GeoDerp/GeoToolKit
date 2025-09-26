# Quickstart Guide for Automated Malicious Code Scanner

## 1. Prerequisites

- Linux host (Fedora, openSUSE, Ubuntu)
- Podman installed and able to pull container images (semgrep/semgrep, aquasec/trivy, ghcr.io/ossf/osv-scanner, owasp/zap2docker-stable)
- Python 3.11+
- Optional: offline vulnerability database package (for air-gapped use)

## 2. Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/GeoDerp/GeoToolKit.git
   ```
2. Navigate to the project directory:
   ```bash
   cd GeoToolKit
   ```
3. Place the offline vulnerability database package in the `data/` directory (optional):
  ```fish
  mkdir -p data
  # Place your offline-db tarball here
  ```

## 3. Usage

1. Create a `projects.json` file with the list of repositories to scan:
   ```json
   {
     "projects": [
       {
         "url": "https://github.com/fastapi/fastapi",
         "name": "fastapi",
         "language": "Python",
         "description": "Modern, fast web framework for building APIs with Python"
       },
       {
         "url": "https://github.com/gin-gonic/gin",
         "name": "gin",
         "language": "Go",
         "description": "HTTP web framework written in Go"
       }
     ]
   }
   ```
2. Run the scanner:
   ```fish
   python src/main.py --input projects.json --output report.md --database-path data/offline-db.tar.gz
   ```
3. The report will be generated at `report.md`.

## 4. Configuration

### Network Allow-list

To allow the DAST scanner to make network connections to specific hosts and ports, create a `network-allowlist.txt` file with one entry per line, in the format `host:port`:

```
localhost:8080
database.example.com:5432
```

Then, pass the path to this file to the scanner:

```fish
python src/main.py --input projects.json --output report.md --database-path data/offline-db.tar.gz --network-allowlist network-allowlist.txt
```
