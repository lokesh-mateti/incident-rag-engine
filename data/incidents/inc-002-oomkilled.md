id: INC-002
title: OOMKilled on recommendation-engine pods
severity: SEV-2
service: recommendation-engine
cluster: prod-us-west-2
date: 2024-10-28
duration: 1h23m
oncall: ml-platform

# INC-002: OOMKilled — recommendation-engine

## Detection
Prometheus alert `container_oom_kill_total` triggered at 14:07 UTC. Grafana dashboard showed 4 of 8 pods restarting with OOMKilled exit code (137).

## Root Cause
Weekly model refresh loaded a new embedding matrix (v2.4) that was 3.2 GB in-memory vs. 1.1 GB for v2.3. Pod memory limit was set to 2Gi. The larger model exceeded the cgroup limit and the kernel OOM-killed the process.

## Timeline
- 14:00 — Cron job triggered model refresh, pulled `s3://models/rec-engine/v2.4`
- 14:05 — Pods began loading new model into memory
- 14:07 — First OOMKill; Prometheus alert fires
- 14:20 — On-call confirmed OOMKilled via `kubectl describe pod`; saw `Last State: Terminated, Reason: OOMKilled, Exit Code: 137`
- 14:35 — Patched deployment to `resources.limits.memory: 4Gi` via kubectl
- 14:42 — Pods stabilized with v2.4 model loaded
- 15:30 — Verified latency p99 normal; incident resolved

## Resolution
Increased memory limit from 2Gi to 4Gi. Added model-size metadata to the S3 artifact manifest so the loader can pre-check memory requirements before swapping.

## Remediation
1. CI pipeline now fails if model artifact exceeds a configurable threshold per service.
2. Added VPA (Vertical Pod Autoscaler) recommendation policy for ML workloads.
3. Runbook updated to include memory profiling step before model promotion.

## Lessons Learned
ML model artifacts can grow unpredictably between versions. Resource limits must be validated against the actual artifact being deployed, not just historical usage.
