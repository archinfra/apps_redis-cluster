# Redis Cluster adapter

`apps_redis-cluster` does not own Redis Cluster orchestration logic.

The deployment model is:

```text
Bitnami redis-cluster chart (pinned upstream version)
        |
        v
archinfra adapter
        |
        +-- image/BOM mapping for offline delivery
        +-- production defaults and resource profiles
        +-- monitoring labels/rules/dashboard additions
        +-- installer UX and validation
        +-- internal-registry rewrite
        v
archinfra .run offline installer
```

## Ownership boundary

Upstream owns StatefulSet layout, Redis Cluster bootstrap/update behavior, probes, services, PDB and the Bitnami runtime contract.

archinfra may adapt configuration, monitoring, resources, storage defaults, security defaults and image locations, but must not silently replace the runtime with an incompatible image.

The Bitnami chart executes `/opt/bitnami/scripts/redis-cluster/...`; therefore `docker.io/library/redis` is not a compatible drop-in replacement.

## Upgrade workflow

1. Check the latest upstream Bitnami `redis-cluster` chart.
2. Update `UPSTREAM.yaml` only after reviewing chart changes.
3. Refresh the chart snapshot from that upstream version.
4. Reapply only the allowlisted archinfra overlay.
5. Run `scripts/validate-upstream-contract.py`, `helm lint` and `helm template`.
6. Build both amd64 and arm64 offline packages.
7. Validate install, rolling restart, node loss/recovery and upgrade in a staging cluster.

Do not edit upstream templates to add product features when the same behavior can be expressed as values, an extra manifest, or installer logic.
