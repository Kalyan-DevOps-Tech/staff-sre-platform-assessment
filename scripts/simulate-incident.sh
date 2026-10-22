#!/usr/bin/env bash
set -Eeuo pipefail

NAMESPACE="apps"
DEPLOYMENT="sample-api-assessment"
AGENT_URL="http://ai-sre-agent.apps.svc.cluster.local:8081"

command -v kubectl >/dev/null || {
  echo "kubectl is required." >&2
  exit 1
}

kubectl get deployment "$DEPLOYMENT" -n "$NAMESPACE" >/dev/null || {
  echo "Assessment deployment not found. Deploy it through Argo CD first." >&2
  exit 1
}

kubectl rollout status "deployment/$DEPLOYMENT" -n "$NAMESPACE" --timeout=120s

mkdir -p artifacts
OUT="artifacts/rca-$(date +%Y%m%d-%H%M%S).json"

echo "Running controlled incident simulation in $DEPLOYMENT..."
kubectl exec -i -n "$NAMESPACE" "deployment/$DEPLOYMENT" -- \
  python - "$AGENT_URL" <<'PY' | tee "$OUT"
import json
import sys
import time
import urllib.error
import urllib.request

agent_url = sys.argv[1].rstrip("/")
api_url = "http://127.0.0.1:8080"
token = __import__("os").environ.get("FAULT_INJECTION_TOKEN")

if not token:
    raise SystemExit("FAULT_INJECTION_TOKEN is missing from the assessment pod.")

def request(url, method="GET", payload=None, headers=None, timeout=10):
    data = None if payload is None else json.dumps(payload).encode()
    h = {"Content-Type": "application/json", **(headers or {})}
    req = urllib.request.Request(url, data=data, headers=h, method=method)
    with urllib.request.urlopen(req, timeout=timeout) as response:
        body = response.read().decode()
        return json.loads(body) if body else {}

def reset_fault():
    request(
        f"{api_url}/admin/fault",
        method="POST",
        payload={"latency_ms": 0, "error_rate": 0},
        headers={"x-fault-token": token},
        timeout=5,
    )

fault_configured = False
try:
    request(f"{api_url}/health/ready", timeout=5)
    request(f"{agent_url}/health/ready", timeout=5)

    start = int(time.time())
    # Set this before sending the request: the server might apply the
    # fault even if the client times out before receiving the response.
    fault_configured = True
    request(
        f"{api_url}/admin/fault",
        method="POST",
        payload={"latency_ms": 1200, "error_rate": 0.2},
        headers={"x-fault-token": token},
    )

    print("Generating 30 controlled requests...", file=sys.stderr)
    for _ in range(30):
        try:
            request(f"{api_url}/api/work", timeout=5)
        except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError):
            pass

    end = int(time.time())
    result = request(
        f"{agent_url}/analyze",
        method="POST",
        payload={
            "incident_id": f"assessment-{int(time.time())}",
            "service": "sample-api-assessment",
            "start_unix": start,
            "end_unix": end,
            "description": "Controlled assessment latency/error injection",
        },
        timeout=60,
    )
    print(json.dumps(result, indent=2))
finally:
    if fault_configured:
        try:
            reset_fault()
            print("Fault injection reset successfully.", file=sys.stderr)
        except Exception as exc:
            print(
                f"CRITICAL: Failed to reset assessment fault: {exc}",
                file=sys.stderr,
            )
            raise
PY

chmod +x scripts/simulate-incident.sh
