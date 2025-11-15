#!/bin/bash
# Production test with optimized timeouts for faster validation

set -e

echo "=== Starting Production MCP Test with Optimized Timeouts ==="

# Set optimized timeouts for production validation
# Spider: 60s (reduced from 120s)
# Active scan: 180s (reduced from 600s - 3 minutes per target)
# Ready timeout: 120s (reduced from 300s)
export ZAP_SPIDER_TIMEOUT=60
export ZAP_ASCAN_TIMEOUT=180
export ZAP_READY_TIMEOUT=120

# Set OSV image explicitly
export OSV_IMAGE=ghcr.io/google/osv-scanner:latest

# Trivy cache (if available) - MUST be properly populated with db/trivy.db and db/metadata.json
if [ -d "data/trivy-cache/db" ] && [ -f "data/trivy-cache/db/trivy.db" ] && [ -f "data/trivy-cache/db/metadata.json" ]; then
    export TRIVY_CACHE_DIR="$(pwd)/data/trivy-cache"
    export GEOTOOLKIT_TRIVY_OFFLINE=1
    # Do NOT set TRIVY_SKIP_UPDATE - let Trivy use the cache without forcing skip on first run
    echo "Using Trivy cache: $TRIVY_CACHE_DIR (offline mode)"
    echo "  - Database: $(ls -lh data/trivy-cache/db/trivy.db | awk '{print $5}')"
else
    echo "⚠️  Trivy cache not found or incomplete - Trivy will be skipped in offline mode"
    echo "    Run: bash scripts/prepare_offline_artifacts.sh data/offline-artifacts"
    echo "    Then: tar -xzf data/offline-artifacts/trivy-cache.tgz -C data/trivy-cache"
    export GEOTOOLKIT_TRIVY_OFFLINE=1
fi

# OSV offline mode (gracefully skip if not available)
export GEOTOOLKIT_OSV_OFFLINE=1
if [ -f "data/osv_offline.db" ]; then
    export GEOTOOLKIT_OSV_OFFLINE_DB="$(pwd)/data/osv_offline.db"
    echo "Using OSV offline DB: $GEOTOOLKIT_OSV_OFFLINE_DB"
else
    echo "No OSV offline DB - OSV will be skipped gracefully"
fi

# Verify DAST targets are running
echo ""
echo "=== Checking DAST targets ==="
echo -n "Juice Shop (port 3000): "
if curl -s -o /dev/null -w '%{http_code}\n' http://127.0.0.1:3000/ | grep -q 200; then
    echo "✓ Running"
else
    echo "✗ Not responding"
    echo "Start with: podman run -d --name juice-shop-dast -p 3000:3000 bkimminich/juice-shop"
fi

echo -n "Httpbin (port 5000): "
if curl -s -o /dev/null -w '%{http_code}\n' http://127.0.0.1:5000/status/200 | grep -q 200; then
    echo "✓ Running"
else
    echo "✗ Not responding"
    echo "Start with: podman run -d --name httpbin-dast -p 5000:80 kennethreitz/httpbin"
fi

echo ""
echo "=== Running scan with timeouts: Spider=${ZAP_SPIDER_TIMEOUT}s, Active Scan=${ZAP_ASCAN_TIMEOUT}s ==="
echo "Expected time: ~15-20 minutes for 10 projects (8 static + 2 DAST)"
echo ""

time python -m src.main \
    --input validation/configs/production-mcp-projects.json \
    --output validation/reports/production-final-report.md \
    --database-path data/offline-db.tar.gz

echo ""
echo "=== Scan Complete ==="
echo "Report: validation/reports/production-final-report.md"
