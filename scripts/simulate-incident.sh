#!/usr/bin/env bash
set -euo pipefail
API_URL=${1:-http://127.0.0.1:18080}
AGENT_URL=${2:-http://127.0.0.1:18081}
TOKEN=${FAULT_INJECTION_TOKEN:-}
if [[ -z "$TOKEN" ]]; then echo "Set FAULT_INJECTION_TOKEN for the API configured with fault injection enabled." >&2; exit 2; fi
command -v curl >/dev/null || { echo "curl required" >&2; exit 1; }
mkdir -p artifacts
START=$(date +%s)
curl -fsS -X POST "$API_URL/admin/fault" -H "content-type: application/json" -H "x-fault-token: $TOKEN" -d '{"latency_ms":1200,"error_rate":0.2}' >/dev/null
cleanup(){ curl -sS -X POST "$API_URL/admin/fault" -H "content-type: application/json" -H "x-fault-token: $TOKEN" -d '{"latency_ms":0,"error_rate":0}' >/dev/null || true; }
trap cleanup EXIT
for i in $(seq 1 30); do curl -sS --max-time 4 "$API_URL/api/work" >/dev/null || true; done
END=$(date +%s)
curl -fsS -X POST "$AGENT_URL/analyze" -H 'content-type: application/json' -d "{"incident_id":"assessment-$(date +%s)","service":"sample-api","start_unix":$START,"end_unix":$END,"description":"Controlled assessment latency/error injection"}" | tee "artifacts/rca-$(date +%Y%m%d-%H%M%S).json"
echo; echo "RCA saved under artifacts/. Fault injection will be disabled by cleanup."
