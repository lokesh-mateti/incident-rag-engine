id: INC-004
title: HPA thrashing causing request timeouts on checkout-api
severity: SEV-1
service: checkout-api
cluster: prod-eu-west-1
date: 2025-01-19
duration: 1h10m
oncall: platform-eng

# INC-004: HPA Thrashing — checkout-api

## Detection
Datadog alert at 11:15 UTC: `http_5xx_rate > 2%` on `checkout-api`. Investigation revealed HPA scaling the deployment between 4 and 20 replicas every 90 seconds.

## Root Cause
A CPU-based HPA with `stabilizationWindowSeconds=0` and `averageUtilization=30%` caused aggressive scale-up on traffic spikes, then immediate scale-down once new pods absorbed load and average CPU dropped. Each scale-down terminated in-flight requests (no `preStop` hook or `terminationGracePeriodSeconds` tuning).

## Timeline
- 11:00 — Flash sale started; traffic 4× baseline
- 11:05 — HPA scaled from 4 → 20 pods
- 11:08 — CPU average dropped below 30%; HPA scaled to 8
- 11:10 — Cycle repeated; pods terminated mid-request
- 11:15 — 5xx alert fired
- 11:30 — On-call patched HPA: set `behavior.scaleDown.stabilizationWindowSeconds=300`
- 11:45 — Replica count stabilized at 16
- 12:25 — Traffic normalized; incident resolved

## Resolution
Set scale-down stabilization to 300s and added a `preStop` lifecycle hook (`sleep 15`) to allow in-flight requests to drain. Also raised `terminationGracePeriodSeconds` to 30.

## Remediation
1. Standardized HPA template across all services with 300s scale-down window.
2. Added KEDA scaler based on RPS from Istio metrics as a secondary signal.
3. Load-tested HPA behavior under simulated flash-sale traffic.

## Lessons Learned
CPU-only HPA with aggressive scale-down is dangerous for latency-sensitive services. Always configure stabilization windows and graceful shutdown to prevent request drops during scale-down.
