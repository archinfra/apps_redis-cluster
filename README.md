# app_redis-cluster

Redis Cluster offline delivery repository.

This repository is not just a Helm chart wrapper. It packages chart, images, monitoring integration, and offline delivery into a single `.run` installer so that a new maintainer, or a general-purpose AI with no background context, can still deploy and verify Redis Cluster end to end.

## What This Installer Does

The installer provides four actions:

- `install`
- `status`
- `uninstall`
- `help`

During `install`, it will:

1. Extract the embedded chart and image metadata from the `.run` package.
2. Load, retag, and push required images to the target internal registry unless `--skip-image-prepare` is used.
3. Detect whether the cluster supports `ServiceMonitor`.
4. Render the final Helm arguments, including images, storage, monitoring, and resource profile.
5. Run `helm upgrade --install`.
6. Print the resulting Pods, Services, PVCs, and ServiceMonitor state.

That means users normally do not need to manually run:

- `docker load`
- `docker tag`
- `docker push`
- `helm dependency build`
- `kubectl apply` for monitoring objects

## Quick Start

Install with defaults:

```bash
./redis-cluster-installer-amd64.run install -y
```

Install with the recommended default profile for ordinary production-style traffic:

```bash
./redis-cluster-installer-amd64.run install \
  --resource-profile mid \
  --storage-class nfs \
  -y
```

Install for a small demo environment:

```bash
./redis-cluster-installer-amd64.run install \
  --resource-profile low \
  -y
```

Install for a heavier traffic scenario:

```bash
./redis-cluster-installer-amd64.run install \
  --resource-profile high \
  --storage-class nfs \
  -y
```

Pass through raw Helm arguments for advanced customization:

```bash
./redis-cluster-installer-amd64.run install -y -- \
  --set redis.extraEnvVars[0].name=TZ \
  --set redis.extraEnvVars[0].value=Asia/Shanghai
```

## Default Deployment Contract

Default installer values:

- namespace: `aict`
- release name: `redis-cluster`
- total nodes: `6`
- replicas per master: `1`
- resulting topology: `3 master + 3 replica`
- password: `Redis@Passw0rd`
- storage class: `nfs`
- storage size: `10Gi`
- metrics: `true`
- ServiceMonitor: `true`
- resource profile: `mid`
- wait timeout: `10m`
- target registry repo: `sealos.hub:5000/kube4`

The default `mid` profile is the baseline profile for a normal shared environment and is intended as the starting point for roughly `500-1000` concurrent requests and around `10000` active users. It is still a baseline, not a strict capacity guarantee. If workload shape is cache-heavy, key size is large, or write amplification is high, raise resources and possibly increase cluster size.

The installer also accepts `midd` as an alias of `mid` to match historical wording.

## Default Access, Endpoints, And Credentials

Internal Service endpoints:

- cluster entry: `redis-cluster.aict.svc.cluster.local:6379`
- headless service: `redis-cluster-headless.aict.svc.cluster.local`
- cluster bus port: `16379`
- metrics service: `redis-cluster-metrics.aict.svc.cluster.local:9121`

Default password:

- `Redis@Passw0rd`

Typical in-cluster client example:

```bash
redis-cli -c -h redis-cluster.aict.svc.cluster.local -p 6379 -a 'Redis@Passw0rd'
```

Production recommendation:

- always override the default password during first install
- keep the service internal unless there is a clear external access design

## Resource Profiles

Three resource profiles are built in:

- `low`: demo, development, or functional validation
- `mid`: normal shared environment, default profile, baseline for `500-1000` concurrency and `~10000` users
- `high`: higher concurrency or larger working set

The profile mainly controls:

- Redis main container requests and limits
- `redis-exporter` sidecar requests and limits
- init/helper containers such as `volumePermissions`, `sysctlImage`, and `updateJob`

### Per-Component Resource Matrix

| Profile | Scenario | Redis request | Redis limit | Exporter request | Exporter limit | Helper init/request | Helper init/limit |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `low` | demo or test | `200m / 256Mi` | `500m / 512Mi` | `50m / 64Mi` | `100m / 128Mi` | `20-30m / 32-64Mi` | `50-100m / 64-128Mi` |
| `mid` | normal shared environment | `500m / 1Gi` | `1 / 2Gi` | `100m / 128Mi` | `200m / 256Mi` | `30-50m / 64Mi` | `100-200m / 128Mi` |
| `high` | higher concurrency | `1 / 2Gi` | `2 / 4Gi` | `200m / 256Mi` | `500m / 512Mi` | `50-100m / 128Mi` | `200-300m / 256Mi` |

### Default Total Steady-State Demand

The table below assumes the default topology of `6` Redis Pods and metrics enabled:

| Profile | Total CPU request | Total memory request | Total CPU limit | Total memory limit | Storage |
| --- | --- | --- | --- | --- | --- |
| `low` | about `1.5 CPU` | about `1.875 GiB` | about `3.6 CPU` | about `3.75 GiB` | `60Gi` |
| `mid` | about `3.6 CPU` | about `6.75 GiB` | about `7.2 CPU` | about `13.5 GiB` | `60Gi` |
| `high` | about `7.2 CPU` | about `13.5 GiB` | about `15 CPU` | about `27 GiB` | `60Gi` |

Notes:

- totals above describe steady-state Redis Pods plus exporter sidecars
- init containers and update jobs add short-lived overhead during rollout
- if you increase node count, total demand scales almost linearly

## Monitoring Design

Monitoring is enabled by default:

- `metrics.enabled=true`
- `metrics.serviceMonitor.enabled=true`

What gets created by default:

- `redis-exporter` sidecar
- metrics Service
- `ServiceMonitor`

Default monitoring label:

- `monitoring.archinfra.io/stack=default`

This means a Prometheus stack that selects by that label will discover Redis automatically after install.

If the cluster does not have the `ServiceMonitor` CRD:

- exporter remains enabled
- `ServiceMonitor` creation is automatically disabled
- Redis install does not fail just because monitoring CRDs are missing

## Dependency And Integration View

### What Redis Depends On

Redis Cluster requires:

- a working Kubernetes cluster
- `kubectl`
- `helm`
- `docker` unless `--skip-image-prepare` is used
- a usable StorageClass, typically `nfs`

Redis does not require these components to start:

- MySQL
- Nacos
- MinIO
- RabbitMQ
- MongoDB
- Milvus

### What Usually Depends On Redis

In integrated business systems, Redis is usually consumed by:

- business API services
- web backends
- AI application services
- session, cache, token, or rate-limit components

Redis is usually a downstream shared capability, not a startup dependency for the other middleware packages.

### Relationship With Prometheus

If your Prometheus stack follows the shared label contract, Redis auto-registers into monitoring through:

- `ServiceMonitor`
- label `monitoring.archinfra.io/stack=default`

## Common Installation Scenarios

### 1. Default install

```bash
./redis-cluster-installer-amd64.run install -y
```

### 2. Demo or development install

```bash
./redis-cluster-installer-amd64.run install \
  --resource-profile low \
  -y
```

### 3. Normal shared environment

```bash
./redis-cluster-installer-amd64.run install \
  --resource-profile mid \
  --storage-class nfs \
  --password 'StrongRedis@2026' \
  -y
```

### 4. Higher concurrency environment

```bash
./redis-cluster-installer-amd64.run install \
  --resource-profile high \
  --nodes 6 \
  --replicas 1 \
  --storage-class nfs \
  -y
```

### 5. Disable monitoring

```bash
./redis-cluster-installer-amd64.run install \
  --disable-metrics \
  --disable-servicemonitor \
  -y
```

### 6. Images already exist in the target registry

```bash
./redis-cluster-installer-amd64.run install \
  --registry sealos.hub:5000/kube4 \
  --skip-image-prepare \
  -y
```

### 7. Pass through unsupported Helm arguments

```bash
./redis-cluster-installer-amd64.run install -y -- \
  --set cluster.externalAccess.enabled=true
```

## Installer Help Summary

Main parameters:

- `--namespace`
- `--release-name`
- `--nodes`
- `--replicas`
- `--password`
- `--storage-class`
- `--storage-size`
- `--resource-profile`
- `--enable-metrics`
- `--disable-metrics`
- `--enable-servicemonitor`
- `--disable-servicemonitor`
- `--service-monitor-namespace`
- `--registry`
- `--registry-user`
- `--registry-password`
- `--image-pull-policy`
- `--skip-image-prepare`
- `--wait-timeout`
- `--delete-pvc`
- `--`

The trailing `--` is the escape hatch for advanced Helm tuning when the installer does not expose a specific chart option.

## Post-Install Verification

Check release status:

```bash
./redis-cluster-installer-amd64.run status -n aict
```

Check Pods:

```bash
kubectl get pods -n aict -l app.kubernetes.io/instance=redis-cluster
```

Check Services:

```bash
kubectl get svc -n aict -l app.kubernetes.io/instance=redis-cluster
```

Check monitoring objects:

```bash
kubectl get servicemonitor -n aict
```

Quick connectivity test:

```bash
kubectl exec -it -n aict redis-cluster-0 -- redis-cli -a 'Redis@Passw0rd' cluster info
```

Success signals:

- all Redis Pods become `Running`
- cluster state reports `ok`
- PVCs are bound
- `ServiceMonitor` exists when the CRD is installed

## Uninstall

Uninstall release only:

```bash
./redis-cluster-installer-amd64.run uninstall -y
```

Uninstall and delete PVCs:

```bash
./redis-cluster-installer-amd64.run uninstall --delete-pvc -y
```

## Troubleshooting

### Pods stay Pending

Check:

- whether the cluster has enough CPU and memory for the selected profile
- whether the requested `StorageClass` exists
- whether PVCs are bound successfully

### ServiceMonitor not created

Check:

- whether `servicemonitors.monitoring.coreos.com` CRD exists
- whether `--disable-servicemonitor` was passed

### Images fail to pull

Check:

- whether the target internal registry is reachable
- whether `--registry` points to the correct repo prefix
- whether `--skip-image-prepare` was used only after images were already present

### Cluster is up but capacity is insufficient

Actions:

- raise `--resource-profile` from `low` to `mid` or `high`
- increase `--nodes`
- adjust advanced chart parameters through `--`

## Guidance For AI Or Automated Operators

If an AI agent is using this installer without human context, it should assume:

- `mid` is the safe default profile
- `low` is only for demo or lightweight testing
- `high` should be used when the cluster already has enough spare resources
- if the target registry already contains images, prefer `--skip-image-prepare`

Before installation, the AI should verify:

- current kube context is correct
- target namespace is intended
- the chosen `StorageClass` exists
- the cluster has enough allocatable CPU and memory for the selected profile

If installation fails, the AI should inspect:

- `kubectl get pods -n <namespace>`
- `kubectl describe pod <pod> -n <namespace>`
- `kubectl get pvc -n <namespace>`
- `kubectl get events -n <namespace> --sort-by=.lastTimestamp`

## Build And Release

Build architecture-specific offline packages:

```bash
./build.sh --arch amd64
./build.sh --arch arm64
./build.sh --arch all
```

The GitHub Actions workflow builds multi-arch release packages on `main` and on tags.
