# Redis Cluster Version Matrix

## Current Production Baseline

| Component | Version / Source |
| --- | --- |
| Redis server | `8.10.1` (`redis/redis` commit `3399357e7c17b668289386b8a15a3037bc4527b1`) |
| Redis Cluster runtime image | `archinfra/redis-cluster:8.10.1-r1` |
| Redis Cluster Helm Chart | `13.0.5-archinfra.1` |
| Chart upstream baseline | Bitnami `redis-cluster` `13.0.5` |
| Redis Exporter | `1.89.0` |
| Helper image | BusyBox `1.37.0-glibc` |
| Runtime base | Debian 12 Bookworm |
| Architectures | amd64, arm64 |

archinfra owns the production distribution. Bitnami remains an upstream code reference, not the owner of the deployed runtime.

## Runtime Contract

The initial archinfra `8.10.1-r1` runtime builds Redis itself from the pinned upstream Redis source commit on `debian:bookworm-slim`. It does not inherit a Redis or Bitnami runtime image.

To avoid rewriting cluster bootstrap semantics in the same release, the first runtime keeps the public Bitnami shell contract under `/opt/bitnami/scripts/redis-cluster`. The compatibility shell source is pinned to Bitnami containers commit `31d7973ac4a12f31662cf06c0e636d858e984184`, corresponding to their public `8.10.1-debian-12-r1` source release.

The production BOM does **not** pull `bitnamilegacy/redis-cluster` or Bitnami Secure Images. The Redis binary and final runtime image are built by archinfra CI for both supported architectures.

## Compatibility

| Component | Requirement |
| --- | --- |
| Kubernetes | >= 1.28 |
| Helm | >= 3.x |
| Storage | Persistent Volume required |
| Redis image | archinfra-built runtime satisfying the current cluster contract |
| Architecture | amd64 or arm64 |

## Upgrade Policy

1. Redis security releases are evaluated independently from the original Bitnami chart `appVersion`.
2. The chart remains an archinfra fork; useful upstream Bitnami chart fixes are reviewed and selectively integrated.
3. Every upstream source used by the fork is pinned in `UPSTREAM.yaml`.
4. Redis is built from a pinned upstream source commit on an explicitly selected OS baseline.
5. The Redis runtime image must be reproducibly buildable by archinfra CI for amd64 and arm64.
6. No production release may fall back to `bitnamilegacy` merely because a newer free Bitnami binary image is unavailable.
7. Before promotion, validate clean install, cluster creation, rolling restart, node/pod loss recovery, failover, persistence, metrics and version upgrade in staging.
8. The transitional `/opt/bitnami/...` compatibility layer should shrink over time until cluster bootstrap is fully archinfra-owned.

## Next Baseline Work

After `8.10.1-r1` is proven in CI and staging, the next work is operational hardening rather than another immediate version jump: generated credentials, explicit Redis memory policy, Monitoring V2, production storage guidance and upgrade/failover tests.
