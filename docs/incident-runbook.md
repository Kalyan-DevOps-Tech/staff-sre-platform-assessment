# Incident Runbook: API Latency Spike

## Trigger
Prometheus detects elevated 5xx rate or latency from the sample API.

## Triage
1. Record incident ID, service, start time, and observed impact.
2. Inspect the API latency histogram and error ratio.
3. Query Loki for matching request IDs and error messages.
4. Query Tempo for slow traces when trace IDs are available.
5. Check Kubernetes restarts, CPU throttling, memory pressure, and recent GitOps changes.

## Mitigation
For the assessment, disable the injected latency through the authenticated fault-control endpoint. In a real deployment, use a reviewed rollback or a safe traffic-management action. The AI agent itself must not execute the mitigation.

## Recovery verification
- Send normal requests after disabling the fault.
- Confirm latency returns to baseline and success ratio recovers.
- Confirm the alert resolves.
- Save the RCA report and relevant query evidence.

## Post-incident
Record root cause, detection gap, customer impact (if any), corrective actions, owners, and due dates. Avoid blame; focus on system improvements.
