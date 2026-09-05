id: INC-001
title: Pod CrashLoopBackOff in payment-service
severity: SEV-1
service: payment-service
cluster: prod-us-east-1
date: 2024-11-14
duration: 47m
oncall: platform-eng

# INC-001: Pod CrashLoopBackOff — payment-service

## Detection
PagerDuty alert fired at 03:12 UTC via Datadog monitor `pod_restart_rate > 5` on namespace `payments`. All 6 replicas of `payment-service` entered CrashLoopBackOff within 2 minutes.

## Root Cause
A config change merged at 02:58 UTC set `DB_POOL_SIZE=500` (previously 50). The Postgres RDS instance (`db.r6g.xlarge`, max_connections=200) rejected connections on startup, causing the health check to fail and kubelet to restart containers in a loop.

## Timeline
- 02:58 — Config PR #4821 merged to main, ArgoCD synced within 60s
- 03:00 — New pods start, immediately fail readiness probe
- 03:12 — PagerDuty fires SEV-1
- 03:18 — On-call identifies recent ArgoCD sync via `kubectl rollout history`
- 03:25 — Ran `kubectl rollout undo deployment/payment-service -n payments`
- 03:30 — Old ReplicaSet healthy, readiness probes pass
- 03:59 — RDS connection count back to baseline; incident resolved

## Resolution
Rolled back the deployment to the previous ReplicaSet. Follow-up PR #4830 set `DB_POOL_SIZE=50` and added a CI validation step that rejects pool sizes exceeding RDS `max_connections`.

## Remediation
1. Added OPA Gatekeeper policy: `db-pool-size-limit` constrains pool size to ≤80% of RDS max_connections.
2. Enabled ArgoCD diff notifications in #deploy-alerts.
3. Created runbook: `runbooks/payment-service-crashloop.md`.

## Lessons Learned
Config changes to connection pools must be coordinated with database capacity. The RDS instance had no headroom, and there was no pre-deploy validation. ArgoCD sync-on-merge meant no human gate before production.
