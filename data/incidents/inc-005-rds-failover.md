id: INC-005
title: Unplanned RDS Multi-AZ failover caused 90s downtime
severity: SEV-1
service: order-service
cluster: prod-us-east-1
date: 2025-02-06
duration: 28m
oncall: backend-eng

# INC-005: Unplanned RDS Multi-AZ Failover

## Detection
CloudWatch alarm `DatabaseConnections > 0 AND ReadLatency > 500ms` fired at 16:42 UTC. Application logs showed `FATAL: connection to server lost` across all order-service pods.

## Root Cause
AWS performed automatic Multi-AZ failover on the `orders-primary` RDS instance (`db.r6g.2xlarge`, Postgres 15.4) due to underlying host degradation. The failover completed in ~35 seconds, but the application connection pool (HikariCP, `connectionTimeout=30s`) did not detect stale connections and continued routing queries to the old primary IP for an additional 55 seconds.

## Timeline
- 16:42 — RDS event `RDS-EVENT-0049` (Multi-AZ failover started)
- 16:42 — CloudWatch alarm triggered; PagerDuty notified
- 16:43 — Failover completed; new primary accepting connections
- 16:44 — Application still holding stale connections; 5xx errors continue
- 16:48 — On-call restarted order-service pods to force new connections
- 16:50 — All pods reconnected to new primary; errors cleared
- 17:10 — Full verification; incident resolved

## Resolution
Rolling restart of order-service pods to flush stale connection pools. Immediate config change: set HikariCP `maxLifetime=600000` (10 min) and `connectionTestQuery=SELECT 1` with `validationTimeout=5000`.

## Remediation
1. Switched DNS to RDS Proxy for automatic connection pooling and failover handling.
2. Added PgBouncer sidecar as a fallback for services not yet on RDS Proxy.
3. Enabled RDS event subscription to SNS → Slack for failover events.

## Lessons Learned
Application connection pools must be configured for failover scenarios. Default HikariCP settings assume stable endpoints and will hold dead connections. RDS Proxy or PgBouncer should front all production databases.
