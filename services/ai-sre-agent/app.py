"""Read-only observability investigator with deterministic and optional LLM summarization."""
import os, time, uuid, json
from typing import Any
import httpx
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
PROM_URL=os.getenv("PROMETHEUS_URL","http://platform-kube-prometheus-prometheus.observability.svc.cluster.local:9090")
LOKI_URL=os.getenv("LOKI_URL","http://loki.observability.svc.cluster.local:3100")
TEMPO_URL=os.getenv("TEMPO_URL","http://tempo.observability.svc.cluster.local:3200")
OPENAI_API_KEY=os.getenv("OPENAI_API_KEY", ""); OPENAI_MODEL=os.getenv("OPENAI_MODEL","gpt-4.1-mini")
app=FastAPI(title="AI SRE Agent", version="1.0.0")
class IncidentRequest(BaseModel):
    incident_id: str = Field(default_factory=lambda: "inc-"+uuid.uuid4().hex[:12], max_length=80)
    service: str = Field(default="sample-api", min_length=1, max_length=100)
    start_unix: int = Field(default_factory=lambda: int(time.time())-900, ge=0)
    end_unix: int = Field(default_factory=lambda: int(time.time()), ge=0)
    description: str = Field(default="Investigate elevated API latency", max_length=1000)
    trace_id: str | None = Field(default=None, pattern=r"^[0-9a-fA-F]{32}$")

async def get_json(client, url, params=None):
    try:
        r=await client.get(url, params=params, timeout=8.0); r.raise_for_status(); return r.json()
    except Exception as exc: return {"query_error":type(exc).__name__,"detail":"telemetry query unavailable"}

async def gather_evidence(req: IncidentRequest):
    if req.end_unix < req.start_unix or req.end_unix-req.start_unix > 3600: raise HTTPException(400,"invalid time range: end must be after start and window <= 1 hour")
    async with httpx.AsyncClient() as client:
        prom=await get_json(client, PROM_URL.rstrip("/")+"/api/v1/query_range", {"query":'histogram_quantile(0.95, sum by (le) (rate(http_server_request_duration_seconds_bucket[5m])))',"start":str(req.start_unix),"end":str(req.end_unix),"step":"15s"})
        prom_error=await get_json(client, PROM_URL.rstrip("/")+"/api/v1/query_range", {"query":'sum(rate(http_server_requests_total{status_code=~"5.."}[5m]))',"start":str(req.start_unix),"end":str(req.end_unix),"step":"15s"})
        # Loki query is bounded to the supplied incident window; escape label values by using a fixed selector.
        loki=await get_json(client, LOKI_URL.rstrip("/")+"/loki/api/v1/query_range", {"query":'{namespace="apps"} |= "request_completed"',"start":str(req.start_unix*1_000_000_000),"end":str(req.end_unix*1_000_000_000),"limit":"100"})
        trace_result={"status":"not_queried","reason":"provide trace_id for direct lookup; broad trace search depends on Tempo configuration"}
        if req.trace_id:
            trace_result=await get_json(client,TEMPO_URL.rstrip("/")+f"/api/traces/{req.trace_id}")
    return {"prometheus_latency_bucket":prom,"prometheus_error_rate":prom_error,"loki_logs":loki,"tempo_trace":trace_result}

def deterministic_analysis(req, evidence):
    errors=evidence.get("prometheus_error_rate",{}); loki=evidence.get("loki_logs",{}); latency=evidence.get("prometheus_latency_bucket",{})
    errors_ok=errors.get("status")=="success"; loki_ok=not loki.get("query_error"); latency_ok=latency.get("status")=="success"
    err_result=[]
    try: err_result=errors.get("data",{}).get("result",[])
    except Exception: pass
    observed_error=False
    for series in err_result:
        samples = series.get("values", []) or ([series.get("value")] if series.get("value") else [])
        for sample in samples:
            try:
                if float(sample[1]) > 0: observed_error=True
            except (TypeError, ValueError, IndexError):
                continue
    log_count=0
    try: log_count=sum(len(s.get("values",[])) for s in loki.get("data",{}).get("result",[]))
    except Exception: pass
    if observed_error: summary="Prometheus reports a non-zero 5xx rate; investigate the matching API error logs and traces."; cause="Elevated HTTP 5xx responses are observed; the underlying cause is not confirmed by metrics alone."; confidence="medium"
    elif log_count: summary="Application request logs were returned for the incident window; correlate latency histograms and traces before confirming a cause."; cause="Request activity is observed, but the available evidence does not prove a unique root cause."; confidence="low"
    else: summary="Insufficient evidence to confirm a root cause. Verify telemetry ingestion, service labels, and incident time window."; cause="Unknown: required evidence is missing or does not show a clear failure signature."; confidence="low"
    return {"incident_id":req.incident_id,"service":req.service,"summary":summary,"impact":"Not independently measured; use request/error metrics and business telemetry to quantify impact.","window":{"start_unix":req.start_unix,"end_unix":req.end_unix},"observations":{"prometheus_query_succeeded":latency_ok and errors_ok,"loki_query_succeeded":loki_ok,"matching_log_entries":log_count,"nonzero_5xx_rate_observed":observed_error,"trace_requested":bool(req.trace_id),"trace_evidence":evidence.get("tempo_trace")},"likely_root_cause":cause,"alternative_hypotheses":["application dependency latency","resource throttling or saturation","recent release/configuration change","telemetry query or label mismatch"],"confidence":confidence,"evidence":evidence,"recommended_mitigation":["Check recent deployments and configuration changes.","Correlate p95/p99 latency with 5xx rate, pod restarts, and resource throttling.","Inspect matching logs and trace spans before taking action."],"verification_steps":["Repeat a health check and representative request.","Confirm the 5xx rate returns to baseline and latency recovers.","Confirm the alert resolves and retain the report."],"preventive_actions":["Add service-specific latency and error-rate SLOs.","Ensure logs carry request_id and trace_id.","Test rollback and recovery procedures."],"evidence_gaps":[name for name,ok in [("Prometheus latency/error queries",latency_ok and errors_ok),("Loki logs",loki_ok)] if not ok],"mode":"deterministic"}

async def summarize_with_llm(report):
    if not OPENAI_API_KEY: return report
    try:
        from openai import AsyncOpenAI
        client=AsyncOpenAI(api_key=OPENAI_API_KEY)
        response=await client.chat.completions.create(model=OPENAI_MODEL,temperature=0,messages=[{"role":"system","content":"You are an SRE investigator. Summarize only evidence present in the supplied JSON. Never invent query results or assert an unproven cause. Preserve evidence gaps, uncertainty, and recommended safe actions. Return concise JSON with summary, likely_root_cause, confidence, and recommended_mitigation."},{"role":"user","content":json.dumps(report,default=str)[:18000]}])
        report["llm_summary"]=response.choices[0].message.content; report["mode"]="telemetry-backed+llm-summary"
    except Exception as exc: report["llm_status"]="unavailable:"+type(exc).__name__
    return report

@app.get("/health/live")
def live(): return {"status":"ok"}
@app.get("/health/ready")
def ready(): return {"status":"ready","prometheus_configured":bool(PROM_URL),"loki_configured":bool(LOKI_URL),"tempo_configured":bool(TEMPO_URL)}
@app.post("/analyze")
async def analyze(req: IncidentRequest):
    evidence=await gather_evidence(req); report=deterministic_analysis(req,evidence); return await summarize_with_llm(report)
