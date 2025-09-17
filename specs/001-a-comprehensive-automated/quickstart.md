# Quickstart Guide for Automated Malicious Code Scanner

## 1. Prerequisites

- A Linux host (e.g., Fedora, Opensuse).
- Podman installed.
- The offline vulnerability database package.

## 2. Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/GeoDerp/GeoToolKit.git
   ```
2. Navigate to the project directory:
   ```bash
   cd GeoToolKit
   ```
3. Place the offline vulnerability database package in the `data/` directory.

## 3. Usage

1. Create a `projects.json` file with the list of repositories to scan:
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
2. Run the scanner:
   ```bash
   ./scan.sh --input projects.json --output report.md --database-path data/offline-db.tar.gz
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

```bash
./scan.sh --input projects.json --output report.md --database-path data/offline-db.tar.gz --network-allowlist network-allowlist.txt
```
