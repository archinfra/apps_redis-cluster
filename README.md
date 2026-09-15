# apps_redis-cluster

Archinfra-maintained Redis Cluster offline delivery repository.

This repository packages an archinfra-maintained Helm chart fork, source-built Redis runtime, exporter, monitoring resources, and architecture-specific offline `.run` installers. The current production baseline is Redis `8.10.1` for both `amd64` and `arm64`.

> This README is the operator-facing contract for installation, upgrade, security, monitoring, offline delivery, verification, and troubleshooting. Exact pinned source provenance is recorded in `UPSTREAM.yaml`, `VERSION`, and `docs/version-matrix.md`.

## Current Production Baseline

| Component | Baseline |
| --- | --- |
| Redis | `8.10.1` |
| Redis source commit | `3399357e7c17b668289386b8a15a3037bc4527b1` |
| Runtime | Debian 12, non-root UID `1001` |
| Chart | `13.0.5-archinfra.1` |
| Upstream chart reference | Bitnami `redis-cluster 13.0.5` |
| redis_exporter | `1.89.0` |
| Helper image | BusyBox `1.37.0-glibc` |
| Architectures | `amd64`, `arm64` |
| Offline installer | `0.1.7` |
| Monitoring schema | V2 |
| Runtime contract | `bitnami-redis-cluster-runtime-v1` |

## What Changed In 0.1.7

This release is a production-baseline update, not only a Redis version bump.

### Runtime and supply chain

- Redis upgraded to `8.10.1`.
- Redis is built by archinfra CI from the pinned official Redis source commit.
- The production BOM no longer depends on `bitnamilegacy/redis-cluster` or a Bitnami Redis binary image.
- The image keeps the Bitnami-compatible `/opt/bitnami/...` cluster bootstrap contract temporarily so the chart topology/bootstrap behavior does not have to be rewritten in the same release.
- Redis binary and the default `redis.conf` come from the same pinned Redis source checkout.
- Runtime is Debian 12 and runs as non-root UID `1001`.
- Native `amd64` and native `arm64` builds are both CI-gated.

### Authentication and installer security

- Removed the historical fixed Redis password.
- First install creates a cryptographically random password by default.
- Existing installer-managed Secret is reused on later upgrades.
- Added `--existing-secret` for externally managed credentials.
- Added `--password-file` for safe credential input.
- Added explicit `--rotate-password`.
- Redis credentials are mounted from Kubernetes Secret files with `usePasswordFiles=true`.
- Redis passwords are not passed in Helm CLI values and are not printed in command previews.
- Removed embedded registry username/password defaults.
- Added `--registry-password-file`.
- The target installer no longer requires `jq`.

### Runtime guardrails

- Added resource-profile-aware `maxmemory`.
- Added explicit `maxmemory-policy`.
- Added `maxclients`, TCP keepalive, cluster node timeout, replication backlog, slowlog, AOF sync, and AOF rewrite defaults.
- `maxmemory` is kept below the pod cgroup memory limit to leave headroom for allocator metadata, client/replication buffers, fork copy-on-write, and process overhead.

### Monitoring V2

- Consolidated Prometheus rules into one source of truth: `charts/redis-cluster/values-archinfra.yaml`.
- Split exporter availability from Redis availability.
- Added cluster, replication, memory, connection, persistence, latency, CPU, PVC, restart, and OOM alerts.
- Added two Grafana dashboards:
  - `Redis / Overview`
  - `Redis / Performance`
- Monitoring discovery follows `monitoring.archinfra.io/stack=default`.

### CI and release gate

Every supported architecture now validates:

- source-built Redis `8.10.1`
- non-root runtime
- runtime linker dependencies
- password-file contract, including special characters
- real six-node Redis Cluster creation
- `3 masters + 3 replicas`
- `cluster_state:ok`
- all `16384` slots assigned
- cluster-routed `SET/GET`
- persistent data directory reuse
- forced node-IP replacement and `nodes.conf` repair
- installer checksum
- workflow artifact upload

Helm CI additionally validates base chart rendering, archinfra production rendering, installer credential policy, Monitoring V2, and explicit full-config override behavior.

## Architecture

```text
Redis 8.10.1 pinned source
        |
        +-- redis-server / redis-cli
        +-- matching upstream redis.conf
        v
archinfra Redis Cluster runtime
        |
        +-- transitional Bitnami-compatible cluster bootstrap contract
        +-- non-root UID 1001
        +-- Debian 12 runtime
        v
archinfra redis-cluster chart fork
        |
        +-- production values
        +-- Kubernetes Secret authentication
        +-- ServiceMonitor / PrometheusRule
        +-- Grafana dashboards
        v
offline .run installer
        |
        +-- embedded chart
        +-- architecture-specific image tarballs
        +-- image metadata
        v
internal registry + Kubernetes
```

Bitnami remains an upstream code reference. Archinfra owns the deployed Redis binary/image, production defaults, offline packaging, authentication policy, monitoring integration, and CI release gate.

## Repository Layout

| Path | Responsibility |
| --- | --- |
| `charts/redis-cluster/` | Archinfra-maintained Redis Cluster Helm chart fork |
| `charts/redis-cluster/values-archinfra.yaml` | Production defaults, runtime guardrails, Monitoring V2 |
| `runtime/redis-cluster/` | Source-built Redis runtime and compatibility layer |
| `runtime/redis-exporter/` | Redis exporter runtime |
| `images/image.json` | Offline image BOM for both architectures |
| `scripts/` | Runtime contract validation and six-node E2E |
| `build.sh` | Offline `.run` package builder |
| `install.sh` | Target-side installer logic |
| `UPSTREAM.yaml` | Pinned upstream provenance |
| `VERSION` | Distribution/component version contract |
| `docs/version-matrix.md` | Version and upgrade maintenance policy |

## Installer Actions

The `.run` package supports four actions:

| Action | Purpose |
| --- | --- |
| `install` | Prepare images and install or upgrade the Helm release |
| `status` | Show Helm release and Kubernetes resource status |
| `uninstall` | Remove the Helm release, optionally PVCs |
| `help` | Print the authoritative built-in command reference |

General syntax:

```bash
./redis-cluster-installer-amd64.run <install|status|uninstall|help> [options] [-- <helm_args>]
```

For ARM64 use `redis-cluster-installer-arm64.run`.

## Target-Side Dependencies

Required on the target node:

- `helm`
- `kubectl`
- `base64`
- `docker` when image preparation is enabled

`docker` is not required when `--skip-image-prepare` is used.

The target machine does **not** require `jq`.

The current Kubernetes context is used. Always verify it before install:

```bash
kubectl config current-context
kubectl get nodes
```

## Quick Start

### Default production-style install

```bash
./redis-cluster-installer-amd64.run install -y
```

Default result:

- namespace: `aict`
- release: `redis-cluster`
- total nodes: `6`
- topology: `3 masters + 3 replicas`
- storage: `10Gi` per Redis Pod
- resource profile: `mid`
- metrics enabled
- ServiceMonitor/PrometheusRule enabled when their CRDs exist
- internal image repository: `sealos.hub:5000/kube4`

The first install automatically creates Secret `redis-cluster-auth` with a random password. Later upgrades reuse it.

### Use an externally managed Secret

```bash
./redis-cluster-installer-amd64.run install \
  --existing-secret redis-prod-auth \
  --secret-key redis-password \
  -y
```

The Secret must already exist in the target namespace and contain the requested key. The installer will not modify an externally managed Secret.

### Seed the managed Secret from a file

```bash
./redis-cluster-installer-amd64.run install \
  --password-file /secure/redis.password \
  -y
```

### Explicit password rotation

```bash
./redis-cluster-installer-amd64.run install \
  --rotate-password \
  -y
```

If `--rotate-password` is used without password input, a new random password is generated.

For controlled rotation to a predetermined credential:

```bash
./redis-cluster-installer-amd64.run install \
  --rotate-password \
  --password-file /secure/new-redis.password \
  -y
```

Do password rotation in a maintenance window and verify cluster health after rollout.

`--password` remains available for compatibility, but `--password-file` or `--existing-secret` is preferred because command-line arguments may remain in shell history or process accounting.

## Default Deployment Contract

| Setting | Default |
| --- | --- |
| Namespace | `aict` |
| Release | `redis-cluster` |
| Nodes | `6` |
| Replicas per master | `1` |
| Topology | `3 master + 3 replica` |
| Managed Secret | `${release}-auth` |
| Secret key | `redis-password` |
| StorageClass | `nfs` |
| Storage size | `10Gi` per Redis Pod |
| Resource profile | `mid` |
| Metrics | enabled |
| ServiceMonitor | enabled when CRD exists |
| PrometheusRule | enabled when CRD exists |
| Wait timeout | `10m` |
| Registry repo | `sealos.hub:5000/kube4` |
| Image pull policy | `IfNotPresent` |
| External Redis access | disabled by chart default |

Node-count validation is enforced by the installer:

- `nodes` must be divisible by `replicas + 1`
- the resulting cluster must contain at least three masters

For the default `6 / 1` topology:

```text
6 / (1 replica + 1 master) = 3 masters
```

## Authentication Model

Redis authentication is Secret-first.

```text
Kubernetes Secret
      |
      v
Secret volume
      |
      v
REDIS_PASSWORD_FILE
      |
      v
Redis runtime
```

The installer does not pass Redis credentials through Helm command-line values.

### Retrieve the password when operationally required

```bash
kubectl get secret redis-cluster-auth -n aict \
  -o jsonpath='{.data.redis-password}' | base64 -d
```

Avoid copying the value into shell command history.

### Verify Redis from inside the Pod

```bash
kubectl exec -n aict redis-cluster-0 -- sh -c \
  'REDISCLI_AUTH="$(cat /opt/bitnami/redis/secrets/redis-password)" redis-cli cluster info'
```

### Secret behavior during uninstall

The authentication Secret is intentionally retained on uninstall. This prevents a reinstall against retained PVCs from silently changing the Redis credential.

If you intentionally want to destroy both data and credentials, remove the Secret separately after uninstall/PVC cleanup:

```bash
kubectl delete secret redis-cluster-auth -n aict
```

Do this only when the old data will no longer be reused.

## Upgrade Guide

### Normal 0.1.7-to-later upgrade using the same managed Secret

Run the new installer with the same release name and namespace:

```bash
./redis-cluster-installer-amd64.run install \
  --release-name redis-cluster \
  --namespace aict \
  -y
```

If `${release}-auth` already exists, it is reused automatically.

### Migrating from the historical fixed-password installer

Older packages used a fixed Redis credential and did not use the new `${release}-auth` Secret contract. Do **not** combine the Redis version migration and a credential change unless you have explicitly tested that path.

Recommended first migration:

1. Record the credential currently used by the existing cluster into a protected file.
2. Use that same credential to seed the new managed Secret.
3. Upgrade Redis/runtime/chart.
4. Verify the complete cluster.
5. Rotate the password later in a separate maintenance change if required.

Example:

```bash
chmod 600 /secure/redis-current.password

./redis-cluster-installer-amd64.run install \
  --namespace aict \
  --release-name redis-cluster \
  --password-file /secure/redis-current.password \
  -y
```

After the first successful migration, later upgrades reuse `redis-cluster-auth` automatically.

### Redis 8.2.x to 8.10.1

The current CI proves clean deployment, cluster behavior, restart/persistence reuse, and node-address repair on Redis `8.10.1`. It does **not** claim exhaustive in-place data-upgrade coverage for every historical Redis/Chart combination.

Before upgrading an existing production 8.2.x cluster:

- confirm a recoverable backup/snapshot exists
- test the exact production dataset and client workload in staging
- preserve the existing password during the first version migration
- confirm clients support Redis Cluster redirects and the target Redis version
- verify `cluster_state`, slots, replica health, AOF/RDB state, latency, and application traffic after rollout
- do not delete old PVCs until rollback/data-recovery decisions are complete

Backup/data-protection orchestration belongs in the centralized archinfra data-protection layer rather than being embedded in this Redis installer.

## Resource Profiles

| Profile | Redis request | Redis limit | Redis maxmemory | repl-backlog-size |
| --- | --- | --- | --- | --- |
| `low` | `200m / 256Mi` | `500m / 512Mi` | `384mb` | `16mb` |
| `mid` | `500m / 1Gi` | `1 CPU / 2Gi` | `1536mb` | `64mb` |
| `high` | `1 CPU / 2Gi` | `2 CPU / 4Gi` | `3gb` | `128mb` |

`mid` is the production default. `midd`, `middle`, and `medium` remain accepted aliases for compatibility.

Common Redis runtime defaults:

```text
maxmemory-policy           noeviction
maxclients                 10000
tcp-keepalive              300
cluster-node-timeout       15000
appendfsync                everysec
auto-aof-rewrite-percentage 100
slowlog-log-slower-than    10000
slowlog-max-len            256
```

`maxmemory` is intentionally lower than the container memory limit. Do not simply set Redis `maxmemory` equal to the Kubernetes limit.

## Storage

Persistence is enabled by default.

Default capacity:

```text
6 Pods x 10Gi = 60Gi requested storage
```

The default StorageClass is `nfs`, but it is configurable:

```bash
./redis-cluster-installer-amd64.run install \
  --storage-class fast-ssd \
  --storage-size 50Gi \
  -y
```

Before installation:

```bash
kubectl get storageclass
```

For Redis workloads, validate actual storage latency and fsync behavior rather than assuming all NFS implementations are suitable for the same workload profile.

## Monitoring V2

Monitoring is enabled by default.

Created resources:

- `redis_exporter` sidecar
- metrics Service
- ServiceMonitor
- PrometheusRule
- Grafana dashboard ConfigMap

Monitoring discovery label:

```text
monitoring.archinfra.io/stack=default
```

Grafana auto-import contract:

```text
grafana_dashboard=1
grafana_folder=Middleware/Redis
```

### Dashboards

- `Redis / Overview`
- `Redis / Performance`

### Alert coverage

Availability:

- `RedisExporterDown`
- `RedisDown`

Cluster:

- cluster state not OK
- incomplete slots
- FAIL slots
- PFAIL slots

Replication:

- missing replicas
- replication lag

Capacity and clients:

- memory 80% / 90%
- fragmentation
- evictions
- client connection utilization
- rejected connections
- blocked clients

Persistence and performance:

- AOF background rewrite failure
- AOF write failure
- RDB background save failure
- command latency
- CPU saturation

Kubernetes/storage:

- PVC 80% / 90%
- repeated Pod restart
- OOMKilled

If the ServiceMonitor or PrometheusRule CRD does not exist, the installer disables only the unsupported object instead of failing Redis installation.

### Completely disable monitoring

Because ServiceMonitor and PrometheusRule automatically imply metrics, disable all three when you want no exporter/monitoring resources:

```bash
./redis-cluster-installer-amd64.run install \
  --disable-metrics \
  --disable-servicemonitor \
  --disable-prometheusrule \
  -y
```

## Network and Exposure

Redis external access is disabled by default.

The chart enables NetworkPolicy support, but the current compatibility default still allows external selected traffic so existing workloads are not broken unexpectedly. Treat this as a compatibility baseline, not strict tenant isolation.

For hardened environments, explicitly restrict callers by namespace/pod selectors as part of the application deployment policy.

Do not enable external Redis access casually. If external access is required, define the exposure, authentication, network policy, TLS, and client-routing model explicitly.

## Registry and Offline Image Handling

No registry username or password is embedded in the installer.

During a normal offline-target install the `.run` package:

1. extracts architecture-specific image tarballs
2. runs `docker load`
3. retags images when a custom registry is requested
4. pushes images into the target registry
5. installs the chart referencing those target images

### Use existing Docker credentials

If the build/installation host already has valid Docker credentials, no registry credential flags are needed.

### Explicit registry login

```bash
./redis-cluster-installer-amd64.run install \
  --registry harbor.example.com/kube4 \
  --registry-user robot-account \
  --registry-password-file /secure/harbor.password \
  -y
```

`--registry-password` exists for compatibility but a password file is preferred.

### Images already exist in the target registry

```bash
./redis-cluster-installer-amd64.run install \
  --skip-image-prepare \
  -y
```

When `--skip-image-prepare` is used, the referenced images must already exist and be pullable by Kubernetes nodes.

Registry login used by the installer is for pushing images from the installation host. If Kubernetes nodes require image-pull authentication, configure the cluster/node credential mechanism or an `imagePullSecret` separately.

## Access and Endpoints

With the default release/namespace:

| Endpoint | Address |
| --- | --- |
| Redis Service | `redis-cluster.aict.svc.cluster.local:6379` |
| Headless Service | `redis-cluster-headless.aict.svc.cluster.local` |
| Cluster bus | `16379` |
| Metrics Service | `redis-cluster-metrics.aict.svc.cluster.local:9121` |

Redis Cluster-aware clients should be used for applications that need normal cluster redirect handling.

## Common Installation Examples

### Small environment

```bash
./redis-cluster-installer-amd64.run install \
  --resource-profile low \
  -y
```

### Standard production baseline

```bash
./redis-cluster-installer-amd64.run install \
  --resource-profile mid \
  --storage-class nfs \
  -y
```

### Higher-resource environment

```bash
./redis-cluster-installer-amd64.run install \
  --resource-profile high \
  --storage-class nfs \
  -y
```

### Custom topology

For example, 9 nodes with 2 replicas per master gives 3 masters + 6 replicas:

```bash
./redis-cluster-installer-amd64.run install \
  --nodes 9 \
  --replicas 2 \
  -y
```

### Separate ServiceMonitor namespace

```bash
./redis-cluster-installer-amd64.run install \
  --service-monitor-namespace monitoring \
  -y
```

### Pass advanced non-secret Helm parameters

```bash
./redis-cluster-installer-amd64.run install -y -- \
  --set redis.extraEnvVars[0].name=TZ \
  --set redis.extraEnvVars[0].value=Asia/Shanghai
```

Password-bearing Helm passthrough arguments are rejected. Authentication changes must use the Secret-oriented installer options.

## Complete Installer Option Reference

### Core deployment

| Option | Meaning | Default |
| --- | --- | --- |
| `-n, --namespace <ns>` | Kubernetes namespace | `aict` |
| `--release-name <name>` | Helm release name | `redis-cluster` |
| `--nodes <num>` | Total Redis Cluster nodes | `6` |
| `--replicas <num>` | Replicas per master | `1` |
| `--storage-class <name>` | StorageClass | `nfs` |
| `--storage-size <size>` | PVC size per Redis Pod | `10Gi` |
| `--resource-profile <name>` | `low|mid|midd|high` | `mid` |
| `--wait-timeout <duration>` | Helm wait timeout | `10m` |

### Authentication

| Option | Meaning |
| --- | --- |
| `--existing-secret <name>` | Use an existing Secret; installer will not modify it |
| `--secret-key <key>` | Password key inside the Secret; default `redis-password` |
| `--password-file <path>` | Seed/create/rotate managed Secret from a local file; recommended |
| `--password <pwd>` | Compatibility input; may remain in shell history |
| `--rotate-password` | Replace installer-managed Secret password |

Rules:

- `--password` and `--password-file` are mutually exclusive.
- `--existing-secret` cannot be combined with password input.
- `--existing-secret` cannot be combined with `--rotate-password`.
- Empty passwords are rejected.

### Monitoring

| Option | Meaning |
| --- | --- |
| `--enable-metrics` | Enable exporter and metrics Service |
| `--disable-metrics` | Disable exporter and metrics Service unless a monitoring CR requires metrics |
| `--enable-servicemonitor` | Enable ServiceMonitor and metrics |
| `--disable-servicemonitor` | Disable ServiceMonitor |
| `--enable-prometheusrule` | Enable PrometheusRule and metrics |
| `--disable-prometheusrule` | Disable PrometheusRule |
| `--service-monitor-namespace <ns>` | Place ServiceMonitor in another namespace |

### Registry and image rollout

| Option | Meaning | Default |
| --- | --- | --- |
| `--registry <repo-prefix>` | Target repository prefix | `sealos.hub:5000/kube4` |
| `--registry-user <user>` | Optional explicit registry user | none |
| `--registry-password-file <path>` | Registry password file; recommended | none |
| `--registry-password <pwd>` | Compatibility password input | none |
| `--image-pull-policy <policy>` | `Always|IfNotPresent|Never` | `IfNotPresent` |
| `--skip-image-prepare` | Do not load/tag/push embedded images | false |

`--registry-user` requires a registry password/password file, and a registry password cannot be supplied without a registry user.

### Lifecycle and passthrough

| Option | Meaning |
| --- | --- |
| `--delete-pvc` | With `uninstall`, also delete release PVCs |
| `-y, --yes` | Skip interactive confirmation |
| `-h, --help` | Show built-in help |
| `--` | Pass remaining non-secret arguments directly to Helm |

The built-in help remains authoritative:

```bash
./redis-cluster-installer-amd64.run help
```

## Status and Verification

### Installer status

```bash
./redis-cluster-installer-amd64.run status -n aict
```

### Pods, Services, PVCs

```bash
kubectl get pods -n aict -l app.kubernetes.io/instance=redis-cluster
kubectl get svc -n aict -l app.kubernetes.io/instance=redis-cluster
kubectl get pvc -n aict
```

### Cluster health

```bash
kubectl exec -n aict redis-cluster-0 -- sh -c \
  'REDISCLI_AUTH="$(cat /opt/bitnami/redis/secrets/redis-password)" redis-cli cluster info'
```

Expected core signals:

```text
cluster_state:ok
cluster_slots_assigned:16384
cluster_slots_ok:16384
cluster_slots_fail:0
```

### Cluster node roles

```bash
kubectl exec -n aict redis-cluster-0 -- sh -c \
  'REDISCLI_AUTH="$(cat /opt/bitnami/redis/secrets/redis-password)" redis-cli cluster nodes'
```

For the default topology, expect three masters and three replicas.

### Exporter metrics

```bash
kubectl get servicemonitor,prometheusrule -n aict
kubectl get svc redis-cluster-metrics -n aict
```

Depending on your monitoring stack, ServiceMonitor may live in the explicitly configured monitoring namespace.

## Uninstall

### Remove Helm release only

```bash
./redis-cluster-installer-amd64.run uninstall -y
```

PVCs and the Redis authentication Secret are retained.

### Remove release and PVCs

```bash
./redis-cluster-installer-amd64.run uninstall \
  --delete-pvc \
  -y
```

The Redis authentication Secret is still retained by design.

Deleting PVCs is destructive. Verify backup/recovery requirements first.

## Troubleshooting

### Pods are Pending

Check:

```bash
kubectl get pods -n aict
kubectl get pvc -n aict
kubectl get storageclass
kubectl get events -n aict --sort-by=.lastTimestamp
```

Common causes:

- insufficient CPU/memory for the selected resource profile
- missing StorageClass
- unbound PVC
- node selectors/taints
- image pull failures

### Pod starts but Redis is unhealthy

```bash
kubectl describe pod redis-cluster-0 -n aict
kubectl logs redis-cluster-0 -n aict -c redis-cluster --tail=200
```

Then inspect cluster state using the password-file command from the verification section.

### Secret error during upgrade

Check:

```bash
kubectl get secret redis-cluster-auth -n aict
kubectl get secret redis-cluster-auth -n aict -o jsonpath='{.data.redis-password}' | wc -c
```

If migrating from an old installer, seed the current production password with `--password-file` during the first migration rather than generating a new password unexpectedly.

### ServiceMonitor or PrometheusRule is missing

```bash
kubectl get crd servicemonitors.monitoring.coreos.com
kubectl get crd prometheusrules.monitoring.coreos.com
```

If a CRD is absent, the installer intentionally disables that object.

### Prometheus has no Redis targets

Verify:

- ServiceMonitor exists
- Prometheus selects `monitoring.archinfra.io/stack=default`
- metrics Service exists
- port `9121` is reachable from Prometheus
- Redis exporter is running in each Pod

### Images fail to push

Verify:

```bash
docker info
docker login <registry-host>
```

Check registry reachability, credentials, repository permissions, and certificate trust.

### Images push successfully but Pods cannot pull

Installer-side Docker credentials do not automatically become Kubernetes image-pull credentials. Verify node/container-runtime registry trust and authentication, or configure the appropriate Kubernetes `imagePullSecret` contract.

### Memory pressure / OOMKilled

Inspect:

```bash
kubectl describe pod redis-cluster-0 -n aict
kubectl top pod -n aict
```

Do not raise Redis `maxmemory` to the full cgroup limit. Increase the resource profile or explicitly tune both the pod limit and Redis memory guardrail together.

### Cluster state is FAIL

Inspect:

```bash
kubectl exec -n aict redis-cluster-0 -- sh -c \
  'REDISCLI_AUTH="$(cat /opt/bitnami/redis/secrets/redis-password)" redis-cli cluster info'

kubectl exec -n aict redis-cluster-0 -- sh -c \
  'REDISCLI_AUTH="$(cat /opt/bitnami/redis/secrets/redis-password)" redis-cli cluster nodes'
```

Then check Pod readiness, node-to-node port `6379`, cluster bus port `16379`, DNS, CNI/NetworkPolicy, and persistent `nodes.conf` state.

## Build Offline Packages

Build one architecture:

```bash
./build.sh --arch amd64
./build.sh --arch arm64
```

Build both:

```bash
./build.sh --arch all
```

Build-host requirements include Docker and `jq`. The generated target installer does not require `jq`.

Expected local outputs:

```text
dist/redis-cluster-installer-amd64.run
dist/redis-cluster-installer-amd64.run.sha256
dist/redis-cluster-installer-arm64.run
dist/redis-cluster-installer-arm64.run.sha256
```

Verify a package before transfer/use:

```bash
cd dist
sha256sum -c <(printf '%s  %s\n' \
  "$(cat redis-cluster-installer-amd64.run.sha256)" \
  redis-cluster-installer-amd64.run)
```

## GitHub Actions Artifacts and Releases

The `Build Redis Cluster Offline Installer` workflow builds both native architectures on relevant pull requests and pushes to `main`.

Workflow artifact names:

```text
redis-cluster-installer-amd64
redis-cluster-installer-arm64
```

Each artifact contains:

```text
redis-cluster-installer-<arch>.run
redis-cluster-installer-<arch>.run.sha256
```

For normal `main` builds, download them from the corresponding GitHub Actions run.

Tags matching `v*` additionally publish both installers and checksum files as GitHub Release assets.

Recommended release flow:

```text
PR validation
  -> merge main
  -> main artifacts verified
  -> create version tag
  -> tag CI rebuilds amd64 + arm64
  -> GitHub Release assets published
```

## Production Checklist

Before deployment:

- verify current kube context
- verify StorageClass
- verify cluster CPU/memory capacity
- verify registry reachability and Kubernetes image-pull capability
- verify backup/recovery state for upgrades
- choose managed Secret vs external Secret intentionally
- keep the current credential for the first migration from the historical installer
- verify Prometheus Operator CRDs if monitoring integration is expected

After deployment:

- all Redis Pods Ready
- all PVCs Bound
- `cluster_state:ok`
- all `16384` slots assigned
- expected master/replica count
- application cluster-routed reads/writes succeed
- exporter targets are up
- PrometheusRule loaded
- Grafana dashboards imported
- no unexpected restart/OOM/replication alerts

## Known Boundaries

- The runtime still carries a transitional Bitnami-compatible bootstrap shell contract. Redis binary distribution is already archinfra-owned; bootstrap logic can be progressively replaced later.
- The installer owns Redis delivery, not centralized backup orchestration. Use the archinfra data-protection layer for backup/restore policy.
- Strict application-to-Redis NetworkPolicy isolation is environment-specific and is not forced by the compatibility default.
- External Redis exposure is not enabled by default and should be designed explicitly when required.
- CI validates the current `8.10.1` runtime thoroughly, but production upgrades from older historical Redis versions still require staging validation with the real dataset/workload.
