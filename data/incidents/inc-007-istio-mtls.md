id: INC-007
title: Istio mTLS strict mode broke cross-namespace communication
severity: SEV-2
service: api-gateway
cluster: prod-us-east-1
date: 2025-03-28
duration: 1h45m
oncall: platform-eng

# INC-007: Istio mTLS Strict Mode — Cross-Namespace Breakage

## Detection
Synthetic monitoring alert at 10:20 UTC: `api-gateway` returning 503 for all routes to `user-service` (namespace `identity`) and `inventory-service` (namespace `catalog`). Istio proxy logs showed `RBAC: access denied` and TLS handshake failures.

## Root Cause
A PeerAuthentication policy was applied cluster-wide setting `mtls.mode: STRICT`, but services in the `identity` and `catalog` namespaces had not yet been injected with Istio sidecars. Plain-text requests from non-mesh pods were rejected by the strict mTLS policy.

## Timeline
- 10:15 — Platform team applied `PeerAuthentication` with `mtls.mode: STRICT` at mesh level
- 10:18 — Cross-namespace calls to non-sidecar services began failing
- 10:20 — Synthetic monitor alert fired
- 10:30 — Identified 503s in Envoy access logs with `response_flags: UF,URX`
- 10:45 — Applied namespace-level `PeerAuthentication` override: `mtls.mode: PERMISSIVE` for `identity` and `catalog`
- 10:50 — Traffic restored to affected services
- 12:00 — Completed sidecar injection for remaining namespaces; re-enabled STRICT

## Resolution
Applied PERMISSIVE overrides for un-injected namespaces as immediate fix. Then injected sidecars into all remaining namespaces and re-enabled STRICT mode cluster-wide.

## Remediation
1. Created pre-flight checklist for mesh policy changes: verify sidecar injection status across all namespaces.
2. Added `istioctl analyze` to CI pipeline to catch policy/injection mismatches.
3. Rolled out sidecar injection via namespace label `istio-injection=enabled` as a standard.

## Lessons Learned
Mesh-wide mTLS enforcement must be coordinated with sidecar injection status. STRICT mode is safe only when every communicating workload is inside the mesh. Always use PERMISSIVE as a transitional step.
