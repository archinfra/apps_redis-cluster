# Archinfra Redis Cluster distribution

`apps_redis-cluster` is now an archinfra-maintained fork of the public Bitnami `redis-cluster` chart.

The fork starts from Bitnami chart `13.0.5` (Apache-2.0), but archinfra owns the production distribution from this point forward.

```text
Bitnami redis-cluster 13.0.5 (upstream reference)
        |
        v
archinfra chart fork: 13.0.5-archinfra.1
        |
        +-- Redis 8.10.1 security baseline
        +-- archinfra-built Redis runtime image
        +-- archinfra-built redis_exporter image
        +-- amd64 / arm64 offline image BOM
        +-- production defaults / resources / monitoring
        +-- installer / registry rewrite / validation
        v
archinfra .run offline installer
```

## Ownership boundary

archinfra now owns:

- the forked Helm chart and its upgrade policy;
- Redis version/security baseline;
- Redis runtime image build;
- cluster bootstrap compatibility;
- offline image BOM and dual-architecture validation;
- production defaults, monitoring and installer UX.

Bitnami is an upstream reference only. The production Redis data plane must not depend on Bitnami Secure Images or `bitnamilegacy` images.

## Transitional runtime contract

The initial archinfra runtime keeps the public Bitnami `/opt/bitnami/scripts/redis-cluster/...` shell contract so that Redis can move to 8.10.1 without simultaneously rewriting cluster bootstrap semantics.

The compatibility source is pinned in `UPSTREAM.yaml` and the image is built by archinfra CI on top of `redis:8.10.1-bookworm`.

This is transitional. Later releases should progressively replace the Bitnami path/variable contract with archinfra-owned bootstrap code while preserving upgrade compatibility.

## Upgrade workflow

1. Track Redis security releases independently from Bitnami chart `appVersion`.
2. Review upstream Bitnami chart changes for useful fixes and Kubernetes API changes.
3. Cherry-pick/rebase selected upstream changes into the archinfra fork instead of replacing the chart blindly.
4. Update `VERSION` and `UPSTREAM.yaml` with explicit source refs.
5. Run `scripts/validate-upstream-contract.py`, `helm lint` and `helm template`.
6. Build amd64 and arm64 runtime images and offline installers.
7. Validate clean install, rolling restart, pod/node loss recovery, cluster health and version upgrade in staging.
8. Only then promote the distribution baseline.

## Licensing

Files derived from Bitnami retain the original Apache-2.0 notices. New archinfra files should identify their own ownership where appropriate. Upstream source refs are kept in `UPSTREAM.yaml` for traceability.
