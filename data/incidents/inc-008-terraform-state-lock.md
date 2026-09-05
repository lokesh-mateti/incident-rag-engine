id: INC-008
title: Terraform state lock blocked infra changes during active incident
severity: SEV-2
service: platform
cluster: prod-us-east-1
date: 2025-04-10
duration: 2h15m
oncall: infra-eng

# INC-008: Terraform State Lock During Active Incident

## Detection
During INC-009 response (unrelated ALB issue), the on-call engineer attempted to run `terraform apply` to add a new target group. Terraform exited with `Error acquiring the state lock` — a previous CI pipeline run had crashed mid-apply and left a DynamoDB lock.

## Root Cause
A GitHub Actions workflow running `terraform apply` was terminated by a 60-minute job timeout mid-resource-creation. The DynamoDB lock item was never released. The team did not have a documented procedure for force-unlocking state, and the on-call hesitated to run `terraform force-unlock` without approval.

## Timeline
- 14:00 — Unrelated ALB incident (INC-009) required infra change
- 14:05 — `terraform plan` succeeded; `terraform apply` failed with lock error
- 14:10 — On-call found stale lock in DynamoDB via AWS Console
- 14:25 — Escalated to infra lead for approval to force-unlock
- 14:40 — Ran `terraform force-unlock <LOCK_ID>`
- 14:45 — `terraform apply` succeeded; ALB target group added
- 16:15 — Root cause documented; incident resolved

## Resolution
Force-unlocked Terraform state via `terraform force-unlock`. Applied the required infrastructure change to resolve the concurrent ALB incident.

## Remediation
1. Set GitHub Actions job timeout to 30 minutes for apply jobs; added `terraform force-unlock` as a manual workflow dispatch.
2. Added DynamoDB TTL (1 hour) on lock items as a safety net.
3. Documented force-unlock procedure in on-call runbook with approval matrix.
4. Moved to Atlantis for Terraform PR-based workflow with built-in lock management.

## Lessons Learned
Terraform state locking without a TTL or documented unlock procedure creates a meta-incident during real incidents. On-call engineers must be empowered to force-unlock with clear guardrails.
