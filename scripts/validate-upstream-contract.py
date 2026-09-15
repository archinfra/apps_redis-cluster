#!/usr/bin/env python3

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
chart = (ROOT / "charts/redis-cluster/Chart.yaml").read_text()
images = json.loads((ROOT / "images/image.json").read_text())
upstream = (ROOT / "UPSTREAM.yaml").read_text()
statefulset = (ROOT / "charts/redis-cluster/templates/redis-statefulset.yaml").read_text()
configmap = (ROOT / "charts/redis-cluster/templates/configmap.yaml").read_text()
values_archinfra = (ROOT / "charts/redis-cluster/values-archinfra.yaml").read_text()
dashboard = (ROOT / "charts/redis-cluster/templates/grafana-dashboard.yaml").read_text()
runtime_dockerfile = (ROOT / "runtime/redis-cluster/Dockerfile").read_text()
exporter_dockerfile = (ROOT / "runtime/redis-exporter/Dockerfile").read_text()
runtime_e2e = (ROOT / "scripts/test-runtime-cluster-e2e.sh").read_text()
installer = (ROOT / "install.sh").read_text()

required_chart_markers = [
    "name: redis-cluster",
    "version: 13.0.5-archinfra.1",
    "appVersion: 8.10.1",
    "archinfra.io/upstream-chart: bitnami/redis-cluster@13.0.5",
]
for marker in required_chart_markers:
    if marker not in chart:
        raise SystemExit(f"chart fork mismatch: missing {marker!r}")

required_upstream_markers = [
    "upstreamVersion: 13.0.5",
    "forkVersion: 13.0.5-archinfra.1",
    "appVersion: 8.10.1",
    "ownership: archinfra-fork",
    "strategy: fork-and-maintain",
]
for marker in required_upstream_markers:
    if marker not in upstream:
        raise SystemExit(f"UPSTREAM.yaml mismatch: missing {marker!r}")

if "/opt/bitnami/scripts/redis-cluster/entrypoint.sh" not in statefulset:
    raise SystemExit("unexpected runtime contract: redis-cluster entrypoint path changed")

runtime_markers = [
    "REDIS_VERSION=8.10.1",
    "REDIS_COMMIT=3399357e7c17b668289386b8a15a3037bc4527b1",
    "FROM debian:bookworm-slim",
    "31d7973ac4a12f31662cf06c0e636d858e984184",
    "/opt/bitnami/scripts/redis-cluster/entrypoint.sh",
    "COPY --from=redis-builder /src/redis/redis.conf /opt/bitnami/redis/etc/redis-default.conf",
    'io.archinfra.redis.config.commit="${REDIS_COMMIT}"',
]
for marker in runtime_markers:
    if marker not in runtime_dockerfile:
        raise SystemExit(f"runtime image contract mismatch: missing {marker!r}")

if "FROM redis:" in runtime_dockerfile:
    raise SystemExit("runtime must build Redis from pinned source, not inherit an external Redis runtime image")

required_config_markers = [
    'archinfra.io/redis-config-baseline: "8.10.1"',
    'archinfra.io/redis-config-source: "runtime-image"',
    "include /opt/bitnami/redis/etc.default/redis.conf",
    "maxmemory ",
    "maxmemory-policy ",
    "repl-backlog-size ",
    "appendfsync ",
    "cluster-node-timeout ",
    "cluster-enabled yes",
    "# tls-cluster yes",
    "# requirepass archinfra-placeholder",
]
for marker in required_config_markers:
    if marker not in configmap:
        raise SystemExit(f"chart config overlay mismatch: missing {marker!r}")

if len(configmap.encode()) > 20 * 1024:
    raise SystemExit("chart configmap is too large; do not re-vendor a full redis.conf snapshot")

required_production_markers = [
    "usePasswordFiles: true",
    "existingSecretPasswordKey: redis-password",
    "maxmemory: 1536mb",
    "maxmemoryPolicy: noeviction",
    "replBacklogSize: 64mb",
    "alert: RedisExporterDown",
    'expr: up{service=',
    "alert: RedisDown",
    "alert: RedisClusterStateNotOk",
    "alert: RedisClusterSlotsIncomplete",
    "alert: RedisReplicaMissing",
    "alert: RedisReplicationLagHigh",
    "alert: RedisMemoryUsageCritical",
    "alert: RedisAOFRewriteFailed",
    "alert: RedisRDBSaveFailed",
    "alert: RedisCommandLatencyHigh",
    "alert: RedisPVCUsageCritical",
    "alert: RedisPodOOMKilled",
]
for marker in required_production_markers:
    if marker not in values_archinfra:
        raise SystemExit(f"production values mismatch: missing {marker!r}")

required_dashboard_markers = [
    'redis-overview.json',
    'redis-performance.json',
    '"title": "Redis / Overview"',
    '"title": "Redis / Performance"',
    "redis_connected_slave_lag_seconds",
    "redis_commands_duration_seconds_total",
    "kubelet_volume_stats_used_bytes",
]
for marker in required_dashboard_markers:
    if marker not in dashboard:
        raise SystemExit(f"dashboard V2 mismatch: missing {marker!r}")

if (ROOT / "monitoring/redis-alert-rules.yaml").exists():
    raise SystemExit("duplicate alert source detected: keep Prometheus rules in values-archinfra.yaml only")

required_installer_markers = [
    'REDIS_PASSWORD=""',
    'REGISTRY_USER=""',
    'REGISTRY_PASS=""',
    '--password-file',
    '--existing-secret',
    '--registry-password-file',
    'existingSecret=${REDIS_SECRET_NAME}',
    'existingSecretPasswordKey=${REDIS_SECRET_KEY}',
    '--set "usePasswordFiles=true"',
    '-f "${CHART_DIR}/values-archinfra.yaml"',
    'redis.runtimeConfig.maxmemory=384mb',
    'redis.runtimeConfig.maxmemory=1536mb',
    'redis.runtimeConfig.maxmemory=3gb',
]
for marker in required_installer_markers:
    if marker not in installer:
        raise SystemExit(f"installer security contract mismatch: missing {marker!r}")

for forbidden in [
    "Redis@Passw0rd",
    'REGISTRY_PASS="passw0rd"',
    '--set-string "password=${REDIS_PASSWORD}"',
    '--set-string "global.redis.password=${REDIS_PASSWORD}"',
]:
    if forbidden in installer:
        raise SystemExit(f"installer contains forbidden credential pattern: {forbidden!r}")

if "jq " in installer or "command -v jq" in installer:
    raise SystemExit("target installer must not require jq")

required_e2e_markers = [
    "cluster_slots_assigned:16384",
    "cluster_known_nodes:6",
    "expected 3 masters",
    "expected 3 replicas",
    "REDIS_PASSWORD_FILE=/run/secrets/redis-password",
    "nodes.conf was not repaired",
]
for marker in required_e2e_markers:
    if marker not in runtime_e2e:
        raise SystemExit(f"runtime E2E contract mismatch: missing {marker!r}")

if "oliver006/redis_exporter:v1.89.0" not in exporter_dockerfile:
    raise SystemExit("redis exporter baseline must be v1.89.0")

arches = {"amd64", "arm64"}
for arch in arches:
    arch_items = [item for item in images if item.get("arch") == arch]
    if len(arch_items) != 3:
        raise SystemExit(f"expected exactly 3 image entries for {arch}, got {len(arch_items)}")

redis_images = [item for item in images if item["tar"].startswith("redis-cluster-")]
if len(redis_images) != 2:
    raise SystemExit("expected one redis-cluster image for each architecture")
for item in redis_images:
    if item.get("build") != "runtime/redis-cluster":
        raise SystemExit(f"redis-cluster must be built by archinfra CI: {item}")
    if item.get("pull"):
        raise SystemExit(f"redis-cluster must not pull an external runtime image: {item}")
    if not item["tag"].endswith("redis-cluster:8.10.1-r1"):
        raise SystemExit(f"unexpected redis-cluster target version: {item['tag']}")

exporter_images = [item for item in images if item["tar"].startswith("redis-exporter-")]
for item in exporter_images:
    if item.get("build") != "runtime/redis-exporter":
        raise SystemExit(f"redis-exporter must be built by archinfra CI: {item}")

for item in images:
    source = f"{item.get('pull', '')} {item.get('tag', '')}"
    if "bitnamilegacy" in source or "bitnami/redis-cluster" in source:
        raise SystemExit(f"production BOM still depends on Bitnami Redis image: {item}")
    if item.get("platform") != f"linux/{item.get('arch')}":
        raise SystemExit(f"platform mismatch: {item}")
    if bool(item.get("pull")) == bool(item.get("build")):
        raise SystemExit(f"image must have exactly one source (pull/build): {item}")

print("archinfra redis-cluster production contract: OK")
