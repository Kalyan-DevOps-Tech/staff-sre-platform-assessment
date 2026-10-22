#!/usr/bin/env bash
set -euo pipefail
REGISTRY=${REGISTRY:-ghcr.io/kalyan-devops-tech}
TAG=${TAG:-0.1.0}
ROOT=$(cd "$(dirname "$0")/.." && pwd)
command -v docker >/dev/null || { echo "docker is required" >&2; exit 1; }
for service in sample-api ai-sre-agent temporal-worker; do
  docker build -t "$REGISTRY/$service:$TAG" "$ROOT/services/$service"
  docker push "$REGISTRY/$service:$TAG"
done
printf '\nImages pushed. Review and update GitOps image references before syncing. Prefer immutable digest references for final submission.\n'
