#!/usr/bin/env bash
set -euo pipefail
: "${GITOPS_REPO_URL:=https://github.com/Kalyan-DevOps-Tech/staff-sre-platform-assessment.git}"
: "${GITOPS_REVISION:=main}"
kubectl create namespace argocd --dry-run=client -o yaml | kubectl apply -f -
# Pre-create namespaces and local-only secrets at the bootstrap boundary. Secret values never enter Git.
for ns in apps observability platform; do kubectl create namespace "$ns" --dry-run=client -o yaml | kubectl apply -f -; done
command -v openssl >/dev/null || { echo "openssl is required to generate local secrets" >&2; exit 1; }
SECRETS_FILE="$(cd "$(dirname "$0")/.." && pwd)/.local-secrets.env"
if [[ ! -f "$SECRETS_FILE" ]]; then
  umask 077
  printf 'TEMPORAL_DB_PASSWORD=%s\nGRAFANA_ADMIN_PASSWORD=%s\nFAULT_INJECTION_TOKEN=%s\n' "$(openssl rand -hex 24)" "$(openssl rand -hex 18)" "$(openssl rand -hex 32)" > "$SECRETS_FILE"
fi
set -a; source "$SECRETS_FILE"; set +a
kubectl -n platform create secret generic temporal-db --from-literal=password="$TEMPORAL_DB_PASSWORD" --dry-run=client -o yaml | kubectl apply -f -
kubectl -n observability create secret generic grafana-admin-credentials --from-literal=admin-user=admin --from-literal=admin-password="$GRAFANA_ADMIN_PASSWORD" --dry-run=client -o yaml | kubectl apply -f -
kubectl -n apps create secret generic sample-api-fault-token --from-literal=token="$FAULT_INJECTION_TOKEN" --dry-run=client -o yaml | kubectl apply -f -
echo "Local secrets saved in .local-secrets.env (gitignored). Keep this file private."
kubectl apply -n argocd -f https://raw.githubusercontent.com/argoproj/argo-cd/v2.13.3/manifests/install.yaml
kubectl -n argocd rollout status deploy/argocd-server --timeout=300s
# This is the documented bootstrap boundary. After this, workloads are managed from Git.
TMP=$(mktemp); trap 'rm -f "$TMP"' EXIT
cat > "$TMP" <<EOF
apiVersion: argoproj.io/v1alpha1
kind: Application
metadata:
  name: platform-root
  namespace: argocd
spec:
  project: default
  source:
    repoURL: ${GITOPS_REPO_URL}
    targetRevision: ${GITOPS_REVISION}
    path: gitops/apps
  destination:
    server: https://kubernetes.default.svc
    namespace: argocd
  syncPolicy:
    automated:
      selfHeal: true
      prune: false
    syncOptions: [CreateNamespace=true]
EOF
kubectl apply -f "$TMP"
echo "Argo CD bootstrapped. Check: kubectl get applications -n argocd"
