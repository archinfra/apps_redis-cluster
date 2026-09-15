# Third-party licensing and provenance

This repository contains an archinfra-maintained Redis Cluster distribution built from multiple upstream projects. Licenses remain attached to their respective upstream works; this document records the intended provenance and redistribution choice.

## Redis 8.10.1

- Upstream: https://github.com/redis/redis
- Version: 8.10.1
- Pinned source commit: `3399357e7c17b668289386b8a15a3037bc4527b1`
- Redis 8+ upstream licensing options: RSALv2, SSPLv1, or AGPLv3
- archinfra redistribution choice for this distribution: **AGPLv3**

The Redis server binary in `archinfra/redis-cluster` is built from the pinned upstream source. Redis copyright/license notices must not be removed from redistributed source or artifacts.

## Bitnami redis-cluster chart and compatibility scripts

- Chart upstream: https://github.com/bitnami/charts/tree/main/bitnami/redis-cluster
- Chart baseline: 13.0.5
- Recorded upstream chart ref: `e07d3319b61f49ddf6f431da3ed7ec0e0be3d5d0`
- Runtime compatibility source: https://github.com/bitnami/containers/tree/main/bitnami/redis-cluster
- Runtime compatibility ref: `31d7973ac4a12f31662cf06c0e636d858e984184`
- License: Apache License 2.0

Files derived from Bitnami retain their original copyright and SPDX notices. The Bitnami runtime scripts are a transitional compatibility layer and are expected to shrink as archinfra replaces the bootstrap implementation.

## redis_exporter

- Upstream: https://github.com/oliver006/redis_exporter
- Version: 1.89.0
- The upstream project license applies to the copied exporter binary.

## Maintenance rule

When changing an upstream version, update `UPSTREAM.yaml`, `VERSION`, this provenance record, and CI validation together. Do not introduce a binary into the offline BOM without a documented upstream source and license.
