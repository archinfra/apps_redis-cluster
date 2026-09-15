# Redis Cluster Version Matrix

## Current Production Baseline

| Component | Version / Source |
| --- | --- |
| Redis server | `8.10.1` (`redis/redis` commit `3399357e7c17b668289386b8a15a3037bc4527b1`) |
| Redis Cluster runtime image | `archinfra/redis-cluster:8.10.1-r1` |
| Redis Cluster Helm Chart | `13.0.5-archinfra.1` |
| Chart upstream baseline | Bitnami `redis-cluster` `13.0.5` |
| Offline installer | `0.1.7` |
| Redis Exporter | `1.89.0` |
| Helper image | BusyBox `1.37.0-glibc` |
| Runtime base | Debian 12 Bookworm |
| Architectures | amd64, arm64 |
| Monitoring | V2: PrometheusRule + ServiceMonitor + 2 Grafana dashboards |

archinfra owns the production distribution. Bitnami remains an upstream code reference, not the owner of the deployed runtime.

## Runtime Contract

The archinfra `8.10.1-r1` runtime builds Redis itself from the pinned upstream Redis source commit on `debian:bookworm-slim`. It does not inherit a Redis or Bitnami runtime image.

Redis binary and default `redis.conf` come from the same pinned Redis source checkout. The Helm chart therefore does not vendor a second full Redis configuration snapshot; it renders a small operational overlay over the source-coupled image configuration.

To avoid rewriting cluster bootstrap semantics in the same release, this runtime keeps the public Bitnami shell contract under `/opt/bitnami/scripts/redis-cluster`. The compatibility shell source is pinned to Bitnami containers commit `31d7973ac4a12f31662cf06c0e636d858e984184`, corresponding to their public `8.10.1-debian-12-r1` source release.

The production BOM does **not** pull `bitnamilegacy/redis-cluster` or Bitnami Secure Images. Redis and redis_exporter runtime images are built by archinfra CI for both supported architectures.

## Authentication Baseline

The installer no longer contains a fixed Redis password and never supplies the Redis password through Helm CLI values.

Default behavior:

1. Create `${release}-auth` when no authentication Secret exists.
2. Generate a cryptographically random password and store it under key `redis-password`.
3. Reuse the Secret during upgrades and reinstalls.
4. Mount the credential through the chart's `existingSecret` + `usePasswordFiles` contract.
5. Allow operators to use an externally managed Secret with `--existing-secret`.
6. Allow password rotation explicitly with `--rotate-password`.
7. Keep the authentication Secret during uninstall so data/PVC restore does not silently change credentials.

`--password-file` is preferred when an operator must supply a password. The legacy `--password` input remains for compatibility but the value is converted immediately into a Kubernetes Secret and is not passed to Helm or printed by the installer.

Registry credentials are not embedded in the installer. Existing Docker credentials are used by default; explicit login supports `--registry-password-file`.

## Resource Baseline

The installer keeps Redis `maxmemory` below the container memory limit to reserve headroom for allocator metadata, client/replication buffers, AOF/RDB fork copy-on-write and process overhead.

| Profile | Redis request | Redis limit | maxmemory | repl-backlog-size |
| --- | --- | --- | --- | --- |
| low | 200m / 256Mi | 500m / 512Mi | 384mb | 16mb |
| mid | 500m / 1Gi | 1 CPU / 2Gi | 1536mb | 64mb |
| high | 1 CPU / 2Gi | 2 CPU / 4Gi | 3gb | 128mb |

Common production defaults include `maxmemory-policy noeviction`, `maxclients 10000`, `tcp-keepalive 300`, `cluster-node-timeout 15000`, AOF `everysec`, slowlog and automatic AOF rewrite thresholds.

## Monitoring V2

The sole alert-rule source is `charts/redis-cluster/values-archinfra.yaml`; the previous duplicate top-level alert file was removed.

Coverage includes:

- Prometheus/exporter scrape failure and Redis connectivity failure as separate signals
- cluster state, slot coverage, FAIL/PFAIL slots
- missing replicas and replication lag
- memory warning/critical, fragmentation and evictions
- connection utilization, rejected connections and blocked clients
- AOF rewrite/write failures and RDB save failure
- command latency and Redis container CPU saturation
- PVC 80%/90% capacity alerts
- pod restart loops and OOMKilled events

Grafana dashboards:

- `Redis / Overview`
- `Redis / Performance`

Monitoring resources use `monitoring.archinfra.io/stack=default` for automatic discovery by the archinfra monitoring stack.

## Runtime Validation

Both native amd64 and arm64 CI jobs run a real six-node Redis Cluster E2E test. The release gate covers:

- Redis 8.10.1 version and dynamic-linker validation
- non-root UID 1001 runtime
- password-file authentication including spaces, quotes, backslashes and `#`
- AOF enablement
- six-node cluster bootstrap with three masters and three replicas
- `cluster_state:ok` and all 16384 slots assigned
- cluster-routed SET/GET
- persistent volume reuse
- forced node IP replacement followed by `nodes.conf` repair and cluster recovery
- offline installer checksum and artifact generation

## Compatibility

| Component | Requirement |
| --- | --- |
| Kubernetes | >= 1.28 |
| Helm | >= 3.x |
| Storage | Persistent Volume required |
| Redis image | archinfra-built runtime satisfying the current cluster contract |
| Architecture | amd64 or arm64 |
| Target installer tools | Helm, kubectl; Docker only when image preparation is required |

The target installer does not require `jq`; `jq` is build-host-only tooling.

## Upgrade Policy

1. Redis security releases are evaluated independently from the original Bitnami chart `appVersion`.
2. The chart remains an archinfra fork; useful upstream Bitnami chart fixes are reviewed and selectively integrated.
3. Every upstream source used by the fork is pinned in `UPSTREAM.yaml`.
4. Redis is built from a pinned upstream source commit on an explicitly selected OS baseline.
5. Redis binary and default configuration must come from the same source commit.
6. The Redis runtime image must be reproducibly buildable by archinfra CI for amd64 and arm64.
7. No production release may fall back to `bitnamilegacy` merely because a newer free Bitnami binary image is unavailable.
8. Security, installer, Helm render and six-node runtime E2E gates must pass before merge.
9. The transitional `/opt/bitnami/...` compatibility layer should shrink over time only after equivalent contract tests protect each replaced behavior.
