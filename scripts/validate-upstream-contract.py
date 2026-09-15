#!/usr/bin/env python3

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
chart = (ROOT / "charts/redis-cluster/Chart.yaml").read_text()
images = json.loads((ROOT / "images/image.json").read_text())
upstream = (ROOT / "UPSTREAM.yaml").read_text()
statefulset = (ROOT / "charts/redis-cluster/templates/redis-statefulset.yaml").read_text()

required_chart_markers = [
    "name: redis-cluster",
    "version: 13.0.5",
    "appVersion: 8.2.1",
    "repository: oci://registry-1.docker.io/bitnamicharts",
]
for marker in required_chart_markers:
    if marker not in chart:
        raise SystemExit(f"chart contract mismatch: missing {marker!r}")

required_upstream_markers = [
    "version: 13.0.5",
    "appVersion: 8.2.1",
    "contract: bitnami-redis-cluster-runtime",
]
for marker in required_upstream_markers:
    if marker not in upstream:
        raise SystemExit(f"UPSTREAM.yaml mismatch: missing {marker!r}")

if "/opt/bitnami/scripts/redis-cluster/entrypoint.sh" not in statefulset:
    raise SystemExit("unexpected chart runtime: Bitnami redis-cluster entrypoint contract not found")

arches = {"amd64", "arm64"}
for arch in arches:
    arch_items = [item for item in images if item.get("arch") == arch]
    if len(arch_items) != 3:
        raise SystemExit(f"expected exactly 3 image entries for {arch}, got {len(arch_items)}")

redis_images = [item for item in images if item["tar"].startswith("redis-cluster-")]
if len(redis_images) != 2:
    raise SystemExit("expected one redis-cluster image for each architecture")

for item in redis_images:
    pull = item["pull"]
    if pull.startswith("redis:") or "/library/redis:" in pull:
        raise SystemExit(
            f"incompatible Redis image for Bitnami chart runtime: {pull}; "
            "use an image that provides /opt/bitnami/scripts/redis-cluster"
        )
    if "bitnamilegacy/redis-cluster:8.2.1-debian-12-r0" not in pull:
        raise SystemExit(f"unexpected redis-cluster compatibility image: {pull}")

for item in images:
    if item.get("platform") != f"linux/{item.get('arch')}":
        raise SystemExit(f"platform mismatch: {item}")

print("upstream chart and image runtime contract: OK")
