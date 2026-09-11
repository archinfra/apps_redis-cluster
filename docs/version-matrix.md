# Redis Cluster Version Matrix

## Current Production Baseline

| Component | Version |
| --- | --- |
| Redis Cluster | 8.2.7 |
| Redis Cluster Helm Chart | 13.0.5 |
| Redis Exporter | 1.76.0 |
| Container Image Base | Debian 12 |

## Compatibility

| Component | Requirement |
| --- | --- |
| Kubernetes | >= 1.28 |
| Helm | >= 3.x |
| Storage | Persistent Volume required |

## Upgrade Policy

- Production environments should keep a fixed tested version.
- Image upgrades require validation in a staging environment first.
- Upgrade records should be maintained together with deployment metadata.
