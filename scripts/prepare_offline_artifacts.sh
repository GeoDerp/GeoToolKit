#!/usr/bin/env bash
# Prepare offline artifacts for GeoToolKit (Trivy cache + OSV offline DB)
# Run this on a machine with network access and podman/docker installed.

set -euo pipefail

OUTDIR=${1:-./offline-artifacts}
mkdir -p "$OUTDIR"

echo "Using output directory: $OUTDIR"

# Find a container runtime: prefer podman, fallback to docker
RUNTIME=""
if command -v podman >/dev/null 2>&1; then
  RUNTIME=podman
elif command -v docker >/dev/null 2>&1; then
  RUNTIME=docker
else
  echo "Error: neither podman nor docker found in PATH. Install one to prepare artifacts." >&2
  exit 2
fi

echo "Preparing Trivy cache... (this may take several minutes)"
# Create a temporary directory for the cache
TMPCACHE=$(mktemp -d)
TMPDBDIR=$(mktemp -d)
# Use a single trap for cleanup of both dirs
cleanup() {
  rm -rf "$TMPCACHE" "$TMPDBDIR"
}
trap cleanup EXIT

# Run Trivy once allowing DB updates so it initializes cache
echo "Initializing Trivy cache in $TMPCACHE using image docker.io/aquasec/trivy"
${RUNTIME} run --rm -v "$TMPCACHE":/root/.cache/trivy:Z docker.io/aquasec/trivy fs --cache-dir /root/.cache/trivy / || true

# Package the cache
TRIVY_TGZ="$OUTDIR/trivy-cache.tgz"
tar -C "$TMPCACHE" -czf "$TRIVY_TGZ" .
echo "Trivy cache packaged to: $TRIVY_TGZ (size: $(stat -c%s "$TRIVY_TGZ") bytes)"

echo "Preparing OSV offline DB..."
OSV_IMAGE=${OSV_IMAGE:-ghcr.io/google/osv-scanner:latest}
echo "Using OSV image: $OSV_IMAGE (set OSV_IMAGE to override if registry access is restricted)"

# Use a temporary directory for any DB files
echo "Attempting OSV offline DB creation..."

# First, try a locally-installed osv-scanner binary
if command -v osv-scanner >/dev/null 2>&1; then
  echo "Found local osv-scanner binary; attempting offline DB download into $TMPDBDIR"
  # many versions support an experimental download flag; write to /data/osv_offline.db
  if osv-scanner --experimental-download-offline-databases --output "$TMPDBDIR/osv_offline.db" 2>&1 | tee /dev/stderr; then
    echo "osv-scanner local binary produced offline DB"
  else
    echo "Local osv-scanner binary present but offline download failed; will try container image fallback"
  fi
else
  echo "No local osv-scanner binary found; will probe container image"
fi

if [ ! -s "$TMPDBDIR/osv_offline.db" ]; then
  echo "Probing OSV image ($OSV_IMAGE) for offline download flags..."
  HELP_OUT=$(${RUNTIME} run --rm $OSV_IMAGE --help 2>&1 || true)
  echo "$HELP_OUT" | head -n 20

# Candidate flags and mapping for flags that require a path
CANDIDATES=("--offline-db" "--offline-vulnerabilities" "--download-offline-database" "--download-offline-db")
SELECTED_FLAG=""
for f in "${CANDIDATES[@]}"; do
  if echo "$HELP_OUT" | grep -q -- "$f"; then
    SELECTED_FLAG="$f"
    break
  fi
done

if [ -n "$SELECTED_FLAG" ]; then
  echo "OSV image supports $SELECTED_FLAG; attempting to download offline DB into $TMPDBDIR"
  # For flags that accept a path argument, map to mounted /data/osv-offline-db
  if [ "$SELECTED_FLAG" = "--offline-db" ] || [ "$SELECTED_FLAG" = "--download-offline-database" ] || [ "$SELECTED_FLAG" = "--download-offline-db" ]; then
    # Mount TMPDBDIR as a directory and write database files inside
    ${RUNTIME} run --rm -v "$TMPDBDIR":/data/osv-offline-db:Z $OSV_IMAGE scan source $SELECTED_FLAG /data/osv-offline-db -r /tmp || true
  else
    ${RUNTIME} run --rm -v "$TMPDBDIR":/data:Z $OSV_IMAGE scan source $SELECTED_FLAG -r /tmp || true
  fi
else
  echo "No known offline flag detected in OSV image; skipping automatic DB download."
fi

# Close the outer probe-if block
fi

# End of probing block

# Find any produced DB artifact in TMPDBDIR
OSV_DB_PATH=""
if [ -f "$TMPDBDIR/osv_offline.db" ] && [ -s "$TMPDBDIR/osv_offline.db" ]; then
  OSV_DB_PATH="$TMPDBDIR/osv_offline.db"
else
  for candidate in "$TMPDBDIR"/*; do
    if [ -f "$candidate" ] && [ -s "$candidate" ]; then
      OSV_DB_PATH="$candidate"
      break
    fi
  done
fi

if [ -n "$OSV_DB_PATH" ]; then
  OUT_OSV="$OUTDIR/osv_offline.db"
  mv "$OSV_DB_PATH" "$OUT_OSV"
  echo "OSV offline DB packaged to: $OUT_OSV (size: $(stat -c%s "$OUT_OSV") bytes)"
else
  echo "No OSV DB produced by image; please follow project docs to obtain an offline DB." >&2
fi

cat <<EOF
Artifacts written to: $OUTDIR

Next steps for CI:
- Upload $OUTDIR/trivy-cache.tgz to your CI runner storage and extract it in the job.
  Example (in CI job):
    mkdir -p /workspace/trivy-cache
    tar -xzf trivy-cache.tgz -C /workspace/trivy-cache
    export TRIVY_CACHE_DIR=/workspace/trivy-cache
    export GEOTOOLKIT_TRIVY_OFFLINE=1

- If you produced an OSV DB, upload it and set in CI:
    export GEOTOOLKIT_OSV_OFFLINE=1
    export GEOTOOLKIT_OSV_OFFLINE_DB=/path/to/osv_offline.db

Notes:
- Use the same tool image versions in CI as used to prepare artifacts to avoid incompatibilities.
- If your CI environment is SELinux enforcing, prefer mounting with the ':Z' option (the script already uses ':Z' when using podman).
EOF
