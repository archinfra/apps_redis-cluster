# Redis Cluster Monitoring

## Overview

Redis Cluster monitoring follows the archinfra observability standard:

- Metrics: redis-exporter
- Collection: Prometheus ServiceMonitor
- Visualization: Grafana Dashboard
- Alerting: PrometheusRule

## Metrics Categories

### Availability

- redis_up
- redis_cluster_state
- redis_connected_clients

### Performance

- commands processed
- operations per second
- command latency

### Resource

- memory usage
- memory fragmentation
- disk usage

### Cluster Health

- master availability
- replica synchronization
- slot coverage

## Deployment

Monitoring components are optional and controlled by Helm values.
