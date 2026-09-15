# Bitnami Redis Cluster Runtime Audit

This document records the Redis Cluster image/runtime behaviors that archinfra intentionally learns from the public Bitnami implementation while taking ownership of the Redis binary, chart fork, image build and release lifecycle.

## Reference baseline

- Bitnami redis-cluster container source: `bitnami/containers`
- compatibility source commit: `31d7973ac4a12f31662cf06c0e636d858e984184`
- Bitnami runtime release at that commit: `8.10.1-debian-12-r1`
- Bitnami chart fork point: `redis-cluster` chart `13.0.5`
- archinfra Redis source: Redis `8.10.1`, commit `3399357e7c17b668289386b8a15a3037bc4527b1`

## What the Bitnami image does beyond installing Redis

The upstream Dockerfile is a packaging and hardening layer, not only a Redis binary container. Important behaviors include:

1. explicit architecture metadata via `TARGETARCH` / `OS_ARCH`
2. explicit runtime dependency set
3. checksum verification for downloaded components
4. removal of package manager caches and temporary download tooling
5. OS package refresh during image build
6. group-writable application directories
7. removal of SUID/SGID bits from the final filesystem
8. non-root runtime (`USER 1001`)
9. build-time generation of Redis configuration/layout via `postunpack.sh`
10. OCI/application version metadata

archinfra should preserve the security and lifecycle intent of these controls without depending on Bitnami's private binary distribution.

## Runtime script contract

### `redis-cluster-env.sh`

The environment layer defines the filesystem contract and supports `*_FILE` values for secrets. This is especially important for Redis passwords and TLS material because credentials do not need to be supplied as literal command-line values.

Important contract areas:

- Redis data/config/log/tmp paths
- password and master password
- AOF/RDB settings
- TLS certificate/key/CA settings
- ACL file
- Redis IO threads
- Redis Cluster creator/replica settings
- dynamic/static cluster announce addressing
- DNS retry controls

### `entrypoint.sh`

The entrypoint copies default configuration into the writable configuration directory, performs setup for the normal `run.sh` path, then uses `exec` for the final command.

The `exec` behavior is important for Kubernetes termination signals.

### `setup.sh`

Setup performs preflight validation, initializes the Redis configuration, manages permissions, and repairs Redis Cluster node addresses when Pod IPs change.

### `run.sh`

The run layer:

- applies `requirepass` / `masterauth`
- supports password-file based credentials
- starts the creator node temporarily in the background during first cluster creation
- waits for peer nodes
- creates the Redis Cluster with `redis-cli --cluster create`
- returns Redis to the foreground or directly `exec`s Redis for normal starts

### `libredis.sh`

This library contains several behaviors that should not be lost during future archinfra rewrites:

- safe Redis config mutation
- removal of control characters from config values
- escaping/quoting of passwords before writing `redis.conf`
- strict config file permissions
- mounted custom configuration support
- AOF and RDB configuration
- TLS configuration and input validation
- ACL file support
- optional command disabling
- Redis IO-thread configuration
- stale PID cleanup
- graceful shutdown helpers

### `librediscluster.sh`

Cluster-specific behavior includes:

- Redis Cluster environment validation
- cluster announce IP/hostname/port configuration
- TLS cluster and TLS replication configuration
- cluster creation and slot coverage verification
- DNS retry behavior
- persistence of hostname-to-IP mappings
- repair of `nodes.conf` after Kubernetes Pod IP changes

The dynamic-IP recovery path is one of the most important behaviors to preserve in Kubernetes.

## Chart-to-image coupling

The Helm chart is tightly coupled to this runtime contract. It directly executes:

- `/opt/bitnami/scripts/redis-cluster/entrypoint.sh`
- `/opt/bitnami/scripts/redis-cluster/run.sh`

It also injects environment variables such as `REDIS_NODES`, `REDIS_CLUSTER_CREATOR`, `REDIS_AOF_ENABLED`, TLS variables and password-file paths.

The chart additionally mounts its own generated `redis-default.conf` into `/opt/bitnami/redis/etc/redis-default.conf`.

This means upgrading the Redis binary alone is insufficient. The chart configuration baseline must be reviewed against the Redis server version as well.

## P0 configuration baseline issue

The archinfra fork currently uses Redis `8.10.1`, while the fork point was Bitnami chart `13.0.5` whose original app baseline was Redis `8.2.1`.

Redis upstream `redis.conf` differs between `8.2.1` and `8.10.1`. Therefore the large default Redis configuration embedded in `templates/configmap.yaml` must be reconciled with Redis `8.10.1` before the fork is considered a fully aligned production baseline.

The preferred maintenance model is:

1. import the Redis `8.10.1` upstream configuration as the version baseline
2. apply a small, reviewable archinfra production overlay
3. test every explicitly overridden directive
4. keep application-specific settings out of the image where possible

## What archinfra should keep

- non-root runtime
- secret-file contract
- strict environment validation
- safe Redis config writer/escaping
- dynamic Pod IP recovery
- cluster slot verification
- TLS and ACL support
- AOF/RDB handling
- explicit runtime dependencies
- filesystem hardening
- provenance/version metadata

## What archinfra should replace over time

- Bitnami binary component downloads
- Stacksmith download endpoints
- Bitnami `minideb` dependency
- generic Bitnami shell library namespace
- the `/opt/bitnami` namespace once chart compatibility no longer requires it
- build-time dependency on cloning the Bitnami repository

The final target should vendor or rewrite only the small Redis/Redis-Cluster functionality that archinfra actually needs, with compatibility tests protecting behavior during the migration.

## Required contract tests before removing Bitnami compatibility scripts

The test suite should cover at least:

- non-root startup
- `REDIS_PASSWORD_FILE`
- password containing spaces, quotes, backslashes and `#`
- AOF enabled/disabled behavior
- RDB policy overrides
- TLS startup and cluster replication
- ACL file loading
- 6-node cluster creation
- all 16384 slots covered
- Pod IP change and `nodes.conf` repair
- master loss and replica promotion
- rolling restart
- PVC reuse
- custom mounted `redis.conf`
- external announce IP/hostname mode
- graceful SIGTERM shutdown

Only after those tests exist should the compatibility shell layer be replaced function-by-function.
