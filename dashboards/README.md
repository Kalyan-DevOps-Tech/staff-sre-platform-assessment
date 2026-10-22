# Grafana dashboard

Create/provision a dashboard with panels for request rate, 5xx ratio, p50/p95/p99 latency, pod restarts, CPU throttling, and API target health. The API metrics include:

- `http_server_requests_total{method,route,status_code}`
- `http_server_request_duration_seconds_bucket{method,route,le}`
- `assessment_fault_injections_total{type}`

Do not add high-cardinality labels such as raw request IDs or user IDs to metrics. Provision the dashboard through GitOps before final submission and include a screenshot/export from a real run.
