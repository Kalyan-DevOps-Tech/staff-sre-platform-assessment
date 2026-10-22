# Operations Runbook

## Basic health
```bash
kubectl get applications -n argocd
kubectl get pods -A
kubectl get events -A --sort-by=.lastTimestamp | tail -50
kubectl -n apps logs deploy/sample-api --since=15m
kubectl -n apps logs deploy/ai-sre-agent --since=15m
```

## GitOps drift
- Check the Argo CD Application health/sync status.
- Inspect the diff before syncing.
- Fix the desired state in Git, open a pull request, run validation, then merge.
- Do not use manual edits as the permanent fix; temporary emergency changes must be documented and reconciled back to Git.

## API latency
1. Check request rate, 5xx ratio, and p95/p99 latency in Grafana.
2. Query Loki for errors around the incident time window.
3. Inspect trace spans for slow downstream operations.
4. Check pod restarts, throttling, memory pressure, and node capacity.
5. Mitigate using a reviewed rollback or safe fault disablement.
6. Verify success ratio and latency return to baseline.

## Observability backend unavailable
- Check pod readiness, PVC status, resource pressure, and recent Argo CD changes.
- Avoid deleting persistent volumes to recover a service.
- Capture logs/events before restarting components.
- Verify ingestion and query path after recovery.

## Temporal workflow failures
- Inspect worker logs and Temporal UI/service health.
- Check activity timeout, retry count, telemetry backend reachability, and malformed input.
- Activities must be idempotent; use incident IDs to avoid duplicate reports.
- Do not put secrets or sensitive payloads in workflow history.
