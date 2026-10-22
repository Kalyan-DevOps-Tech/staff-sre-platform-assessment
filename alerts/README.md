# Alert rules

PrometheusRule examples are in `gitops/observability/alert-rules.yaml`. The 5xx ratio rule is a short-window test alert. Validate that the kube-prometheus-stack Prometheus selector discovers the rule and that the expression matches the actual metric labels in your deployed Prometheus. Adjust namespace/service labels after checking live series.
