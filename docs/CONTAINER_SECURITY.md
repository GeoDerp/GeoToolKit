# GeoToolKit Offline Container Security Best Practices

## Overview
GeoToolKit runs all security scanning tools in isolated Podman containers with strict security controls. This document outlines the security best practices implemented across all runners.

## Core Security Principles

### 1. **Network Isolation (`--network=none`)**
**Default**: All containers run with `--network=none` to prevent any network access.

**Implementation**:
- ✅ **Semgrep**: Offline by default, optional `SEMGREP_NETWORK` override
- ✅ **Trivy**: Uses pre-populated offline database (`--skip-update --offline-scan`)
- ✅ **OSV-Scanner**: Uses offline database when `GEOTOOLKIT_OSV_OFFLINE=1`
- ⚠️  **ZAP**: Requires network for DAST testing (controlled via `ZAP_PODMAN_NETWORK`)

**Rationale**: Network isolation prevents:
- Data exfiltration from scanned code
- Malicious code reaching external resources
- Dependency confusion attacks
- Side-channel information leakage

### 2. **Capability Dropping (`--cap-drop=ALL`)**
All containers drop ALL Linux capabilities by default.

**Why**: Even in rootless mode, containers have some capabilities. Dropping all ensures minimal privilege.

### 3. **Seccomp Profiles**
Each tool has a tailored seccomp profile that restricts system calls:

```
seccomp/
├── default.json           # Generic restrictive profile
├── semgrep-seccomp.json  # Semgrep-specific syscalls
├── trivy-seccomp.json    # Trivy-specific syscalls
├── osv-scanner-seccomp.json  # OSV-Scanner syscalls
└── zap-seccomp.json      # ZAP DAST scanner syscalls
```

**Features**:
- Automatic fallback if seccomp causes issues
- Environment variable override: `<TOOL>_SECCOMP_PATH`
- Auto-detection of SELinux for proper volume labeling

### 4. **Rootless Execution**
All containers must be run with Podman in rootless mode:

```bash
# Check rootless status
podman info | grep rootless
# Should show: rootless: true
```

**Benefits**:
- Containers cannot escalate to root on host
- Improved isolation via user namespaces
- Reduced attack surface

### 5. **User Namespace Isolation (`--userns=keep-id`)**
Containers run with the caller's UID mapped inside the container.

**Rationale**:
- Prevents permission issues with bind mounts
- Ensures output files are owned by the caller
- Maintains least-privilege principle

### 6. **Read-Only Mounts**
Project source code is mounted read-only (`:ro`) wherever possible:

```bash
-v /host/project:/scan:ro,Z
```

**Protection**:
- Prevents container from modifying source code
- Protects against malicious tool behavior
- Ensures scan reproducibility

### 7. **SELinux Relabeling**
Automatic SELinux relabeling (`:Z`) when enforcing mode detected:

**Auto-detection**:
1. Check `/sys/fs/selinux/enforce`
2. Fall back to `getenforce` command
3. Override via `GEOTOOLKIT_SELINUX_RELABEL=1`

**Effect**: Ensures containers can read bind-mounted files on SELinux-enforcing hosts (Fedora, RHEL, etc.)

### 8. **Resource Limits**
All runners support timeout parameters to prevent runaway processes:

```python
# Example: 10-minute timeout for Semgrep
semgrep_findings = SemgrepRunner.run_scan(
    project_path, 
    timeout=600
)
```

**Recommended Timeouts** (from `copilot-guides.md`):
- DAST per-target: 300 seconds (5 minutes)
- Full scan: 1800 seconds (30 minutes)
- Individual runner: 600 seconds (10 minutes)

## Tool-Specific Configurations

### Semgrep (SAST)
```bash
# Offline operation
podman run --rm --network=none \
  --cap-drop=ALL \
  --security-opt=seccomp=/path/to/semgrep-seccomp.json \
  -v /project:/scan:ro,Z \
  returntocorp/semgrep:latest semgrep scan /scan
```

**Offline Capabilities**: ✅ Full offline support with custom rules

### Trivy (SCA)
```bash
# Pre-populated database required
podman run --rm --network=none \
  --cap-drop=ALL \
  --security-opt=seccomp=/path/to/trivy-seccomp.json \
  -v /project:/scan:ro,Z \
  -v /db/trivy-db:/root/.cache/trivy:ro \
  aquasec/trivy:latest fs --skip-update --offline-scan /scan
```

**Offline Capabilities**: ✅ Requires pre-built vulnerability database

### OSV-Scanner (SCA)
```bash
# Offline database optional but recommended
podman run --rm --network=none \
  --cap-drop=ALL \
  --security-opt=seccomp=/path/to/osv-scanner-seccomp.json \
  -v /project:/scan:ro,Z \
  -v /db/osv-offline.db:/data/osv-offline-db:ro \
  ghcr.io/google/osv-scanner:latest --experimental-offline=/data/osv-offline-db /scan
```

**Offline Capabilities**: ⚠️  Optional - falls back gracefully if offline DB unavailable

### OWASP ZAP (DAST)
```bash
# Network required for DAST - controlled isolation
podman run --rm \
  --network=<controlled-network> \
  --cap-drop=ALL \
  --security-opt=seccomp=/path/to/zap-seccomp.json \
  ghcr.io/zaproxy/zaproxy:latest zap-baseline.py -t <target-url>
```

**Offline Capabilities**: ⚠️  Requires network to target application under test
- Network is scoped to specific test environment
- Can use `--network=host` for localhost testing only
- Supports allowlist-based egress filtering

## Environment Variables Reference

### Global Security Controls
- `GEOTOOLKIT_USE_SECCOMP`: Enable/disable seccomp (default: `1`)
- `GEOTOOLKIT_ALLOW_PACKAGED_SECCOMP`: Allow built-in profiles (default: `true`)
- `GEOTOOLKIT_SELINUX_RELABEL`: Force SELinux relabeling (auto-detected by default)
- `GEOTOOLKIT_RUN_AS_HOST_USER`: Run container as host UID/GID (default: `0`)

### Tool-Specific
- `SEMGREP_NETWORK`: Override network mode for Semgrep
- `TRIVY_SECCOMP_PATH`: Custom seccomp profile for Trivy
- `OSV_SECCOMP_PATH`: Custom seccomp profile for OSV-Scanner
- `ZAP_PODMAN_NETWORK`: Network mode for ZAP (e.g., `host`, `bridge`)
- `GEOTOOLKIT_ZAP_KEEP_CONTAINER`: Keep ZAP container after exit for debugging

### Offline Database Paths
- `GEOTOOLKIT_OSV_OFFLINE`: Enable OSV offline mode (default: `0`)
- `GEOTOOLKIT_OSV_OFFLINE_DB`: Path to OSV offline database
- `TRIVY_DB_PATH`: Path to Trivy database (handled by runner)

## Verification Checklist

Before deploying GeoToolKit in a secure environment, verify:

- [ ] Podman is in rootless mode (`podman info | grep rootless`)
- [ ] All seccomp profiles exist and are readable
- [ ] Offline databases are pre-populated (Trivy, optionally OSV)
- [ ] SELinux is detected correctly if enforcing
- [ ] Network isolation is working (`--network=none`)
- [ ] Containers cannot escalate privileges
- [ ] Resource limits (timeouts) are configured
- [ ] Log directory is writable for audit trails

## Testing Offline Capabilities

### Test Network Isolation
```bash
# This should fail or timeout (no network access)
podman run --rm --network=none alpine:latest ping -c 1 google.com
```

### Test Seccomp Profile
```bash
# Should succeed with proper seccomp profile
podman run --rm --network=none \
  --security-opt=seccomp=seccomp/default.json \
  alpine:latest /bin/sh -c "echo test"
```

### Test SELinux Relabeling
```bash
# On SELinux-enforcing host, this should work:
podman run --rm --network=none \
  -v $(pwd):/data:ro,Z \
  alpine:latest ls /data
```

## Best Practices Summary

1. ✅ **Always use `--network=none`** except for DAST (which has controlled access)
2. ✅ **Drop all capabilities** with `--cap-drop=ALL`
3. ✅ **Use seccomp profiles** with automatic fallback
4. ✅ **Mount source code read-only** (`:ro`) to prevent modification
5. ✅ **Run rootless** for defense in depth
6. ✅ **Set timeouts** to prevent resource exhaustion
7. ✅ **Pre-populate databases** for true offline operation
8. ✅ **Log everything** to `logs/` for audit and debugging
9. ✅ **Auto-detect SELinux** and apply `:Z` labeling
10. ✅ **Isolate DAST testing** with network policies and allowlists

## Security Considerations

### Why Not Docker?
Podman is preferred over Docker because:
- **Rootless by design**: No daemon running as root
- **Daemonless**: Direct container execution
- **Better security**: No single point of failure
- **Drop-in replacement**: Docker CLI compatible

### Why Not Falco?
See `docs/FALCO_ANALYSIS.md` for detailed analysis. Summary:
- Requires privileged access (contradicts security model)
- Designed for runtime monitoring, not static scans
- Better suited for production Kubernetes environments

### Defense in Depth Layers
1. **Rootless Podman**: No root daemon
2. **Network Isolation**: `--network=none`
3. **Capability Drop**: No Linux capabilities
4. **Seccomp**: Syscall filtering
5. **User Namespaces**: UID mapping
6. **Read-Only Mounts**: Immutable source
7. **SELinux/AppArmor**: Mandatory access control
8. **Timeouts**: Resource limits

## Troubleshooting

### "Permission denied" on SELinux hosts
**Solution**: Ensure mounts have `:Z` suffix or set `GEOTOOLKIT_SELINUX_RELABEL=1`

### "Operation not permitted" with seccomp
**Solution**: The profile is too restrictive. Tool will auto-fallback without seccomp.

### OSV-Scanner tries network access
**Solution**: Set `GEOTOOLKIT_OSV_OFFLINE=1` and provide offline DB

### Trivy fails without network
**Solution**: Pre-populate database with `trivy image --download-db-only`

## References
- Podman Security: https://docs.podman.io/en/latest/markdown/podman-run.1.html#security-options
- Seccomp Profiles: https://github.com/moby/moby/blob/master/profiles/seccomp/default.json
- SELinux Container Labels: https://www.redhat.com/en/blog/selinux-containers
- OWASP Container Security: https://cheatsheetseries.owasp.org/cheatsheets/Docker_Security_Cheat_Sheet.html
