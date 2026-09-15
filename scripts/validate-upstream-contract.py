#!/usr/bin/env python3

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
chart = (ROOT / "charts/redis-cluster/Chart.yaml").read_text()
images = json.loads((ROOT / "images/image.json").read_text())
upstream = (ROOT / "UPSTREAM.yaml").read_text()
statefulset = (ROOT / "charts/redis-cluster/templates/redis-statefulset.yaml").read_text()
runtime_dockerfile = (ROOT / "runtime/redis-cluster/Dockerfile").read_text()
exporter_dockerfile = (ROOT / "runtime/redis-exporter/Dockerfile").read_text()

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

# Transitional compatibility contract: the chart still invokes these paths while
# the Redis binary and final runtime image are now built by archinfra.
if "/opt/bitnami/scripts/redis-cluster/entrypoint.sh" not in statefulset:
    raise SystemExit("unexpected runtime contract: redis-cluster entrypoint path changed")

runtime_markers = [
    "REDIS_VERSION=8.10.1",
    "REDIS_COMMIT=3399357e7c17b668289386b8a15a3037bc4527b1",
    "FROM debian:bookworm-slim",
    "31d7973ac4a12f31662cf06c0e636d858e984184",
    "/opt/bitnami/scripts/redis-cluster/entrypoint.sh",
]
for marker in runtime_markers:
    if marker not in runtime_dockerfile:
        raise SystemExit(f"runtime image contract mismatch: missing {marker!r}")

if "FROM redis:" in runtime_dockerfile:
    raise SystemExit("runtime must build Redis from pinned source, not inherit an external Redis runtime image")

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

print("archinfra redis-cluster fork/runtime contract: OK")
