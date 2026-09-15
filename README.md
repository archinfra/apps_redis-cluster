# apps_redis-cluster

Archinfra-maintained Redis Cluster offline delivery repository.

The repository packages an archinfra-maintained Helm chart fork, source-built Redis runtime, exporter, monitoring resources, and architecture-specific offline `.run` installers. The production baseline is Redis `8.10.1` for both amd64 and arm64.

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
```

Bitnami remains an upstream code reference. The production Redis image is not pulled from `bitnami/redis-cluster` or `bitnamilegacy`; archinfra builds Redis from the pinned official Redis source commit.

## Production Baseline

| Component | Baseline |
| --- | --- |
| Redis | `8.10.1` |
| Redis source commit | `3399357e7c17b668289386b8a15a3037bc4527b1` |
| Runtime | Debian 12, UID 1001 |
| Chart | `13.0.5-archinfra.1` |
| Upstream chart reference | Bitnami `redis-cluster 13.0.5` |
| redis_exporter | `1.89.0` |
| Architectures | amd64, arm64 |
| Offline installer | `0.1.7` |
| Monitoring | V2 |

See `UPSTREAM.yaml`, `VERSION`, and `docs/version-matrix.md` for pinned provenance and maintenance policy.

## What The Installer Does

The installer supports:

- `install`
- `status`
- `uninstall`
- `help`

During installation it:

1. Extracts the embedded chart and image payload.
2. Creates or reuses the Redis authentication Secret.
3. Loads, retags, and pushes packaged images unless `--skip-image-prepare` is used.
4. Detects ServiceMonitor and PrometheusRule CRDs.
5. Applies archinfra production defaults and the requested resource profile.
6. Runs `helm upgrade --install`.
7. Shows resulting Pods, Services, PVCs, and monitoring objects.

The target machine does **not** require `jq`. `jq` is used only on the build host.

## Quick Start

Default production-style install:

```bash
./redis-cluster-installer-amd64.run install -y
```

The first install automatically creates Secret `redis-cluster-auth` with a random password. Later upgrades reuse that Secret.

Use an externally managed Secret:

```bash
./redis-cluster-installer-amd64.run install \
  --existing-secret redis-prod-auth \
  --secret-key redis-password \
  -y
```

Seed a managed Secret from a password file:

```bash
./redis-cluster-installer-amd64.run install \
  --password-file /secure/redis.password \
  -y
```

Rotate an installer-managed password explicitly:

```bash
./redis-cluster-installer-amd64.run install \
  --rotate-password \
  -y
```

`--password` remains available for compatibility, but `--password-file` or `--existing-secret` is preferred because command-line values can remain in shell history.

## Default Deployment Contract

- namespace: `aict`
- release: `redis-cluster`
- total nodes: `6`
- replicas per master: `1`
- topology: `3 masters + 3 replicas`
- authentication: Kubernetes Secret mounted through `REDIS_PASSWORD_FILE`
- managed Secret: `${release}-auth`
- password key: `redis-password`
- storage class: `nfs`
- storage size: `10Gi` per Redis Pod
- resource profile: `mid`
- metrics: enabled
- ServiceMonitor: enabled when the CRD exists
- PrometheusRule: enabled when the CRD exists
- wait timeout: `10m`
- default image repository: `sealos.hub:5000/kube4`

The installer never passes the Redis password through Helm values and never prints the password in command previews or post-install output.

The authentication Secret is intentionally retained on uninstall so a reinstall against retained PVCs does not silently change credentials.

## Access

Internal endpoints with default release/namespace:

- Redis service: `redis-cluster.aict.svc.cluster.local:6379`
- headless service: `redis-cluster-headless.aict.svc.cluster.local`
- cluster bus: `16379`
- metrics service: `redis-cluster-metrics.aict.svc.cluster.local:9121`

Retrieve the password only when operationally required:

```bash
kubectl get secret redis-cluster-auth -n aict \
  -o jsonpath='{.data.redis-password}' | base64 -d
```

Example connectivity check without placing the password in the process arguments:

```bash
kubectl exec -n aict redis-cluster-0 -- sh -c \
  'REDISCLI_AUTH="$(cat /opt/bitnami/redis/secrets/redis-password)" redis-cli cluster info'
```

## Resource Profiles

| Profile | Redis request | Redis limit | Redis maxmemory | repl-backlog-size |
| --- | --- | --- | --- | --- |
| `low` | `200m / 256Mi` | `500m / 512Mi` | `384mb` | `16mb` |
| `mid` | `500m / 1Gi` | `1 CPU / 2Gi` | `1536mb` | `64mb` |
| `high` | `1 CPU / 2Gi` | `2 CPU / 4Gi` | `3gb` | `128mb` |

`mid` is the default. `midd`, `middle`, and `medium` remain accepted aliases.

`maxmemory` is intentionally lower than the container memory limit to reserve headroom for allocator metadata, client and replication buffers, AOF/RDB fork copy-on-write, and process overhead.

Common Redis production defaults include:

- `maxmemory-policy noeviction`
- `maxclients 10000`
- `tcp-keepalive 300`
- `cluster-node-timeout 15000`
- AOF enabled with `appendfsync everysec`
- automatic AOF rewrite thresholds
- explicit replication backlog
- slowlog defaults

## Monitoring V2

Monitoring is enabled by default and uses a single rule source in `charts/redis-cluster/values-archinfra.yaml`.

Created resources:

- redis_exporter sidecar
- metrics Service
- ServiceMonitor
- PrometheusRule
- Grafana dashboard ConfigMap

Discovery label:

```text
monitoring.archinfra.io/stack=default
```

Grafana dashboards:

- `Redis / Overview`
- `Redis / Performance`

Alert coverage includes:

- exporter scrape down
- Redis connectivity down
- cluster state not OK
- incomplete/FAIL/PFAIL slots
- missing replicas
- replication lag
- memory 80%/90%
- fragmentation and evictions
- connection utilization, rejected connections, blocked clients
- AOF rewrite/write failures
- RDB save failures
- command latency
- CPU saturation
- PVC 80%/90%
- repeated Pod restarts
- OOMKilled

If ServiceMonitor or PrometheusRule CRDs are absent, the installer disables the unsupported object instead of failing the Redis deployment.

## Registry Handling

No registry username or password is embedded in the installer.

By default the installer uses the current Docker credential configuration. To log in explicitly:

```bash
./redis-cluster-installer-amd64.run install \
  --registry harbor.example.com/kube4 \
  --registry-user robot-account \
  --registry-password-file /secure/harbor.password \
  -y
```

If the required images are already present in the target registry:

```bash
./redis-cluster-installer-amd64.run install \
  --skip-image-prepare \
  -y
```

## Advanced Installation Examples

Small environment:

```bash
./redis-cluster-installer-amd64.run install \
  --resource-profile low \
  -y
```

Higher-resource environment:

```bash
./redis-cluster-installer-amd64.run install \
  --resource-profile high \
  --storage-class nfs \
  -y
```

Disable monitoring objects:

```bash
./redis-cluster-installer-amd64.run install \
  --disable-metrics \
  --disable-servicemonitor \
  --disable-prometheusrule \
  -y
```

Pass non-secret advanced Helm values:

```bash
./redis-cluster-installer-amd64.run install -y -- \
  --set redis.extraEnvVars[0].name=TZ \
  --set redis.extraEnvVars[0].value=Asia/Shanghai
```

The installer rejects password-bearing Helm passthrough arguments. Authentication changes must use the Secret-oriented installer options.

## Installer Parameters

Authentication:

- `--existing-secret`
- `--secret-key`
- `--password-file`
- `--password` (compatibility only)
- `--rotate-password`

Deployment:

- `--namespace`
- `--release-name`
- `--nodes`
- `--replicas`
- `--storage-class`
- `--storage-size`
- `--resource-profile`
- `--wait-timeout`

Monitoring:

- `--enable-metrics` / `--disable-metrics`
- `--enable-servicemonitor` / `--disable-servicemonitor`
- `--enable-prometheusrule` / `--disable-prometheusrule`
- `--service-monitor-namespace`

Registry:

- `--registry`
- `--registry-user`
- `--registry-password-file`
- `--registry-password` (compatibility only)
- `--image-pull-policy`
- `--skip-image-prepare`

Lifecycle:

- `--delete-pvc`
- `--yes`
- `--`

Run the installer with `help` for the authoritative command reference.

## Verification

Status:

```bash
./redis-cluster-installer-amd64.run status -n aict
```

Pods and PVCs:

```bash
kubectl get pods,pvc -n aict -l app.kubernetes.io/instance=redis-cluster
```

Cluster health:

```bash
kubectl exec -n aict redis-cluster-0 -- sh -c \
  'REDISCLI_AUTH="$(cat /opt/bitnami/redis/secrets/redis-password)" redis-cli cluster info'
```

Expected signals include:

- all six Pods Running/Ready
- `cluster_state:ok`
- `cluster_slots_assigned:16384`
- three masters and three replicas
- all PVCs Bound
- exporter metrics scrape successfully
- ServiceMonitor/PrometheusRule exist when their CRDs are installed

## CI Release Gate

Both amd64 and arm64 native GitHub runners build the Redis runtime from source and execute a real six-node Redis Cluster E2E test.

The gate validates:

- pinned Redis `8.10.1`
- non-root runtime and dynamic linker dependencies
- password-file authentication with special characters
- AOF
- 3 masters + 3 replicas
- all 16384 slots
- cluster-routed SET/GET
- persistent data volume reuse
- forced node IP replacement and `nodes.conf` repair
- base Chart rendering
- production Chart rendering
- Secret-first installer policy
- Monitoring V2 rendering
- offline installer checksum and artifact upload

## Uninstall

Release only:

```bash
./redis-cluster-installer-amd64.run uninstall -y
```

Release plus PVCs:

```bash
./redis-cluster-installer-amd64.run uninstall --delete-pvc -y
```

The Redis authentication Secret is retained by design.

## Troubleshooting

If Pods are Pending, check resource capacity, StorageClass existence, PVC binding, and scheduling events.

If monitoring objects are missing, verify the corresponding Prometheus Operator CRDs and the `monitoring.archinfra.io/stack=default` selector contract.

If images fail to push or pull, verify registry reachability, Docker credentials, repository permissions, and whether `--skip-image-prepare` was selected appropriately.

Useful commands:

```bash
kubectl get pods -n aict
kubectl get pvc -n aict
kubectl get events -n aict --sort-by=.lastTimestamp
kubectl describe pod redis-cluster-0 -n aict
```

## Build

Build architecture-specific offline packages:

```bash
./build.sh --arch amd64
./build.sh --arch arm64
./build.sh --arch all
```

The build host requires Docker and `jq`. The generated target installer does not require `jq`.

GitHub Actions builds both architecture-specific `.run` artifacts on pull requests and `main`; tag workflows additionally publish release files.
