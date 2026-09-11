# Redis Cluster Architecture

## Overview

archinfra Redis Cluster provides a production-ready Redis deployment package based on Kubernetes and Helm.

## Logical Architecture

```
Application
    |
    v
Redis Cluster Service
    |
    +----------------+
    | Redis Masters  |
    |  redis-0       |
    |  redis-1       |
    |  redis-2       |
    +----------------+

    +----------------+
    | Redis Replicas |
    |  redis-3       |
    |  redis-4       |
    |  redis-5       |
    +----------------+

Storage:
  PVC -> StorageClass -> Backend Storage

Monitoring:
  Redis Exporter -> Prometheus -> Grafana / Alerting
```

## Production Principles

- Fixed and traceable component versions
- Declarative deployment through Helm
- Persistent storage for data safety
- Monitoring and alerting integration
- Standard operation and maintenance workflow
