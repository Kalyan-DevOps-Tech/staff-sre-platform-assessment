# Architecture and Data Flow

## Components
- **k3s:** local Kubernetes control plane for repeatable platform validation.
- **Argo CD:** watches the Git repository and reconciles declarative applications after one-time bootstrap.
- **Sample API:** FastAPI service with health checks, request metrics, JSON logs, and OpenTelemetry tracing.
- **Prometheus:** scrapes service metrics and evaluates recording/alerting rules.
- **Loki:** stores/query logs collected from container stdout by the cluster log pipeline.
- **Tempo:** receives OTLP traces through the OpenTelemetry Collector.
- **Grafana:** queries the metrics, logs, and traces data sources.
- **Temporal:** orchestrates incident-analysis activities with bounded retries and timeouts.
- **AI SRE agent:** queries backends and produces a structured evidence-based report; no cluster mutation permissions.

## Trust boundaries
1. Git repository and reviewed pull requests define desired state.
2. Argo CD has Kubernetes permissions required for declared workloads; avoid granting broad permissions to application service accounts.
3. Application namespaces are separate from observability and platform namespaces.
4. The fault endpoint is disabled by default and token protected when enabled.
5. The AI agent receives read-only network access to telemetry APIs; it does not receive Kubernetes API credentials.

## Incident flow
1. A test client sends requests to the API while latency injection is enabled.
2. The API increments request counters and latency histograms, writes structured logs, and emits spans.
3. Prometheus evaluates the alert rule; Loki and Tempo retain diagnostic evidence.
4. An incident request starts a Temporal workflow. An activity queries the telemetry backends in the incident time window.
5. The analyzer returns observed facts, likely causes, alternative hypotheses, evidence gaps, and safe recommended next steps.
6. The operator verifies recovery after disabling the injected fault.

## Design trade-offs
- Local single-node k3s is inexpensive and reproducible but cannot validate multi-node or multi-AZ resilience.
- Prometheus is the initial metrics backend; Mimir is optional and should be added only if long-term/multi-tenant metrics are a requirement.
- The local reference stack uses chart-based upstream components to reduce bespoke maintenance. Pin chart versions and inspect rendered manifests before production use.
- Deterministic analysis is the fallback so the demo remains testable without an external LLM; an LLM can summarize evidence but cannot invent it.
