# Redis Cluster Version Matrix

## Current Production Baseline

| Component | Version / Source |
| --- | --- |
| Redis Cluster runtime | `8.2.1` Bitnami-compatible runtime |
| Redis Cluster Helm Chart | `13.0.5` from `bitnamicharts/redis-cluster` |
| Redis Exporter | `1.76.0` |
| Container Image Base | Debian 12 |
| Architectures | amd64, arm64 |

The Helm chart is owned by upstream Bitnami. archinfra maintains an adapter layer around the pinned chart instead of maintaining an independent Redis Cluster chart fork.

## Runtime Contract

Bitnami `redis-cluster` chart `13.0.5` executes the Bitnami runtime under `/opt/bitnami/scripts/redis-cluster` and uses the Bitnami filesystem/environment contract.

For this reason `docker.io/library/redis` is **not** a drop-in replacement for the chart image even when the Redis server version itself is newer.

The current public compatibility baseline uses the matching `bitnamilegacy/redis-cluster:8.2.1-debian-12-r0` image and mirrors it into the archinfra delivery registry. This is a compatibility bridge, not a long-term image lifecycle strategy.

## Compatibility

| Component | Requirement |
| --- | --- |
| Kubernetes | >= 1.28 |
| Helm | >= 3.x |
| Storage | Persistent Volume required |
| Redis image | Must satisfy the Bitnami redis-cluster runtime contract |

## Upgrade Policy

1. Prefer the latest tested upstream Bitnami `redis-cluster` chart; do not fork the topology/bootstrap implementation.
2. Pin the exact chart version in `UPSTREAM.yaml`.
3. Keep archinfra changes in the adapter/installer/monitoring layer.
4. Never replace the Bitnami runtime image with the Docker Official Redis image without a dedicated compatibility implementation and test suite.
5. Test both amd64 and arm64 package builds.
6. Validate install, rolling restart, failover/recovery and upgrade in staging before production rollout.

A future Redis server upgrade beyond `8.2.1` must first resolve the image distribution choice: Bitnami Secure Images or another image that has been explicitly proven compatible with the Bitnami chart runtime contract.
