# Preparing offline artifacts for GeoToolKit CI

This document explains how to prepare and package offline artifacts for running GeoToolKit in an air-gapped or restricted CI environment. Two artifacts are commonly needed:

- Trivy local cache (so `trivy` doesn't need to download its vulnerability DB)
- OSV offline database (so `osv-scanner` can operate without network access)

These steps should be executed on a machine with network access and Docker/Podman installed. After creating the artifacts, upload the archive to your CI environment and set environment variables as described below.

## Trivy cache

1. On a machine with network access, run Trivy at least once to populate its cache. Use the same Trivy image you plan to use in CI.

Example (podman):

```sh
# Run Trivy against a small repo to populate cache
podman run --rm -v "$PWD":/src:ro docker.io/aquasec/trivy fs --cache-dir /root/.cache/trivy --skip-db-update /src || true
```

2. Package the cache directory into a tarball for CI transfer:

```sh
tar -C ~/.cache -czf trivy-cache.tgz trivy
# or if using the path you mounted above
# tar -C /root/.cache -czf trivy-cache.tgz trivy
```

3. In your CI, extract the tarball and point GeoToolKit to it:

```sh
# Extract the cache into a stable path for the job
mkdir -p /workspace/trivy-cache
tar -xzf trivy-cache.tgz -C /workspace/trivy-cache
export TRIVY_CACHE_DIR=/workspace/trivy-cache
export GEOTOOLKIT_TRIVY_OFFLINE=1
```

## OSV offline DB

OSV-Scanner supports downloading an offline database in some versions.

1. On a networked machine, use the OSV-Scanner (or provided helper) to download the offline DB if supported. If the image supports flags shown in the help (e.g. `--download-offline-database`), use those to fetch a database file.

2. If the image doesn't provide a direct download, check the OSV project's documentation for a packaged offline DB or use the Python `osv` tooling to download a dump.

3. Package the offline DB file and upload it to CI.

In CI, copy or mount the DB into the job workspace and set:

```sh
# Example CI job steps
mkdir -p /workspace/osv
cp osv_offline.db /workspace/osv/osv_offline.db
export GEOTOOLKIT_OSV_OFFLINE=1
export GEOTOOLKIT_OSV_OFFLINE_DB=/workspace/osv/osv_offline.db
```

Notes on compatibility:
- Use the same `OSV_IMAGE` tag in CI that was used to prepare the DB. Flags and file locations can vary across image versions.
- If your CI runner uses SELinux (for example, GitLab runners on RHEL/CentOS), mount volumes with `:Z` where possible.

## Notes
- Versions vary: when preparing artifacts, use the same tool image versions as CI to avoid incompatibilities.
- Trivy's cache format may change across major versions; pin the Trivy image to the same tag used in CI.
- OSV offline flags vary by image version; GeoToolKit probes the image help to select a supported flag. You can override via `OSV_IMAGE_OFFLINE_FLAGS`.

## Example script
See `scripts/prepare_offline_artifacts.sh` for an automated helper to build both artifacts.
