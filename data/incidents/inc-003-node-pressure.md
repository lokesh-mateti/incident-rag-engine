id: INC-003
title: Node NotReady due to disk pressure on EKS worker nodes
severity: SEV-2
service: platform
cluster: prod-us-east-1
date: 2024-12-03
duration: 55m
oncall: platform-eng

# INC-003: Node NotReady — Disk Pressure

## Detection
Slack alert from kube-state-metrics at 09:30 UTC: 3 of 12 worker nodes transitioned to `NotReady` with condition `DiskPressure=True`. Pod evictions began immediately.

## Root Cause
Container image layer cache on the nodes grew to consume 92% of the 100 GiB root EBS volume. The kubelet's `imageGCHighThresholdPercent` was set to the default (85%), but a burst of image pulls for a canary deployment (12 new tags in 20 minutes) outpaced garbage collection.

## Timeline
- 09:10 — Canary deployment for `search-api` rolled out 12 image variants
- 09:28 — Disk usage crossed 90% on 3 nodes
- 09:30 — Nodes marked NotReady; pods evicted
- 09:35 — On-call identified disk pressure via `kubectl describe node`
- 09:42 — Ran `crictl rmi --prune` on affected nodes to reclaim space
- 09:48 — Nodes returned to Ready; pods rescheduled
- 10:25 — Verified cluster health stable; incident resolved

## Resolution
Manually pruned unused images on affected nodes. Increased root EBS volume to 200 GiB via ASG launch template update and set `imageGCHighThresholdPercent=70` in kubelet config.

## Remediation
1. Switched to Bottlerocket OS with ephemeral storage on NVMe for image cache.
2. Added Datadog monitor for `disk.used_pct > 80` on node root volumes.
3. Limited canary deployments to 3 concurrent image variants.

## Lessons Learned
Disk pressure from image cache is a silent killer on EKS. Default kubelet GC thresholds are too generous for nodes with heavy image churn. Canary strategies that pull many unique images can overwhelm disk in minutes.
