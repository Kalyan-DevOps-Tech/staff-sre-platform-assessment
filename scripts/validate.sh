#!/usr/bin/env bash
set -euo pipefail
ROOT=$(cd "$(dirname "$0")/.." && pwd)
cd "$ROOT"
python3 -m compileall -q services scripts
if python3 -c "import yaml" >/dev/null 2>&1; then python3 scripts/validate_repo.py; else echo "PyYAML missing; install requirements-dev.txt to validate YAML."; fi
if command -v pytest >/dev/null 2>&1; then pytest -q; else echo "pytest not installed; run: python3 -m pip install pytest httpx fastapi prometheus-client opentelemetry-api opentelemetry-sdk opentelemetry-exporter-otlp-proto-http"; fi
if command -v kubectl >/dev/null 2>&1; then
  for d in gitops/sample-api gitops/ai-sre-agent gitops/temporal gitops/apps; do kubectl kustomize "$d" >/dev/null; done
else echo "kubectl unavailable; Kubernetes rendering checks skipped."; fi
echo "Static validation finished. This does not replace a clean cluster bootstrap or E2E incident drill."
