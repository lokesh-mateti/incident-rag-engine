id: INC-006
title: CoreDNS pod failure causing cluster-wide DNS resolution errors
severity: SEV-1
service: platform
cluster: prod-us-west-2
date: 2025-03-11
duration: 35m
oncall: platform-eng

# INC-006: CoreDNS Failure — Cluster-Wide DNS Outage

## Detection
Multiple PagerDuty alerts at 08:05 UTC across services: connection timeouts, `dial tcp: lookup <service>.svc.cluster.local: no such host`. Grafana showed CoreDNS request rate drop to zero.

## Root Cause
A node scaling event terminated both CoreDNS pods simultaneously. The CoreDNS deployment had only 2 replicas with no `podAntiAffinity`, so both were scheduled on the same node. When that node was terminated by Cluster Autoscaler (scale-in), DNS resolution failed cluster-wide until replacements started.

## Timeline
- 08:02 — Cluster Autoscaler terminated node `ip-10-0-34-112` (low utilization)
- 08:03 — Both CoreDNS pods terminated
- 08:05 — Cascading alerts across 14 services
- 08:08 — On-call identified CoreDNS pods missing via `kubectl get pods -n kube-system`
- 08:12 — New CoreDNS pods scheduled on surviving nodes; DNS restored
- 08:15 — Manually scaled CoreDNS to 4 replicas
- 08:40 — All downstream services recovered; incident resolved

## Resolution
Scaled CoreDNS to 4 replicas immediately. Added `podAntiAffinity` with `requiredDuringSchedulingIgnoredDuringExecution` on `topology.kubernetes.io/zone` and `kubernetes.io/hostname`.

## Remediation
1. Added PodDisruptionBudget: `minAvailable: 2` for CoreDNS.
2. Configured Cluster Autoscaler to respect `cluster-autoscaler.kubernetes.io/safe-to-evict=false` annotation on system-critical pods.
3. Deployed NodeLocal DNSCache as a fallback.

## Lessons Learned
CoreDNS is a single point of failure if not properly spread across nodes and zones. Always set anti-affinity and PDBs for cluster-critical add-ons. Cluster Autoscaler can unknowingly terminate critical infrastructure.
