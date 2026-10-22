"""Instrumented assessment API. Fault injection is opt-in and token protected."""
import json, logging, os, secrets, time, uuid
from contextlib import asynccontextmanager
from typing import Optional
from fastapi import FastAPI, Header, HTTPException, Request
from fastapi.responses import Response
from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST
from opentelemetry import trace
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter

SERVICE_NAME = os.getenv("OTEL_SERVICE_NAME", "sample-api")
LOG = logging.getLogger("sample-api")
class JsonFormatter(logging.Formatter):
    def format(self, record):
        payload = {"timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(record.created)), "level": record.levelname, "service": SERVICE_NAME, "message": record.getMessage()}
        for key in ("request_id", "path", "status_code", "duration_ms", "fault_injected"):
            if hasattr(record, key): payload[key] = getattr(record, key)
        span = trace.get_current_span().get_span_context()
        if span.is_valid: payload["trace_id"] = format(span.trace_id, "032x")
        return json.dumps(payload, separators=(",", ":"))
handler = logging.StreamHandler(); handler.setFormatter(JsonFormatter()); LOG.handlers = [handler]; LOG.setLevel(os.getenv("LOG_LEVEL", "INFO")); LOG.propagate = False
REQUESTS = Counter("http_server_requests_total", "HTTP requests", ["method", "route", "status_code"])
LATENCY = Histogram("http_server_request_duration_seconds", "HTTP request duration", ["method", "route"], buckets=(.01,.025,.05,.1,.25,.5,1,2.5,5,10))
FAULTS = Counter("assessment_fault_injections_total", "Injected faults", ["type"])

def configure_tracing():
    endpoint = os.getenv("OTEL_EXPORTER_OTLP_TRACES_ENDPOINT")
    provider = TracerProvider(resource=Resource.create({"service.name": SERVICE_NAME, "deployment.environment": os.getenv("ENVIRONMENT", "local-assessment")}))
    if endpoint:
        try: provider.add_span_processor(BatchSpanProcessor(OTLPSpanExporter(endpoint=endpoint, timeout=3)))
        except Exception as exc: LOG.warning("trace_exporter_configuration_failed: %s", type(exc).__name__)
    trace.set_tracer_provider(provider)
configure_tracing()
TRACER = trace.get_tracer(SERVICE_NAME)
FAULT_ENABLED = os.getenv("FAULT_INJECTION_ENABLED", "false").lower() == "true"
FAULT_TOKEN = os.getenv("FAULT_INJECTION_TOKEN", "")
FAULT_STATE = {"latency_ms": 0, "error_rate": 0.0}

@asynccontextmanager
async def lifespan(app):
    LOG.info("service_starting")
    yield
    LOG.info("service_stopping")
app = FastAPI(title="SRE Assessment Sample API", version="1.0.0", lifespan=lifespan)

@app.middleware("http")
async def observe_request(request: Request, call_next):
    request_id = request.headers.get("x-request-id", str(uuid.uuid4()))[:128]
    started = time.perf_counter(); status = 500; route = "unmatched"
    with TRACER.start_as_current_span("http.request") as span:
        span.set_attribute("http.request.method", request.method); span.set_attribute("request.id", request_id)
        try:
            response = await call_next(request); status = response.status_code
            matched_route = request.scope.get("route")
            route = getattr(matched_route, "path", "unmatched")
            span.set_attribute("http.route", route)
            response.headers["x-request-id"] = request_id
            response.headers["x-trace-id"] = format(span.get_span_context().trace_id, "032x") if span.get_span_context().is_valid else ""
            return response
        except Exception:
            matched_route = request.scope.get("route")
            route = getattr(matched_route, "path", "unmatched")
            span.set_attribute("http.route", route)
            LOG.exception("request_failed", extra={"request_id":request_id,"path":route})
            raise
        finally:
            duration = time.perf_counter() - started
            REQUESTS.labels(request.method, route, str(status)).inc(); LATENCY.labels(request.method, route).observe(duration)
            LOG.info("request_completed", extra={"request_id":request_id,"path":route,"status_code":status,"duration_ms":round(duration*1000,2)})

@app.get("/health/live")
def live(): return {"status":"ok"}
@app.get("/health/ready")
def ready(): return {"status":"ready"}
@app.get("/api/work")
async def work():
    with TRACER.start_as_current_span("business.work") as span:
        delay = int(FAULT_STATE["latency_ms"]); error_rate = float(FAULT_STATE["error_rate"])
        span.set_attribute("fault.latency_ms", delay)
        if delay: await __import__("asyncio").sleep(min(delay, 5000)/1000)
        # Deterministic error injection is intentionally probability-based only for the isolated test.
        import random
        if error_rate > 0 and random.random() < error_rate:
            FAULTS.labels("http_500").inc(); raise HTTPException(status_code=500, detail="simulated assessment failure")
        return {"status":"ok", "operation":"work", "simulated_latency_ms":delay}

@app.get("/metrics")
def metrics(): return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)

@app.post("/admin/fault")
def set_fault(payload: dict, x_fault_token: Optional[str] = Header(default=None)):
    if not FAULT_ENABLED: raise HTTPException(status_code=404, detail="fault injection disabled")
    if not FAULT_TOKEN or not x_fault_token or not secrets.compare_digest(FAULT_TOKEN, x_fault_token): raise HTTPException(status_code=403, detail="forbidden")
    latency = payload.get("latency_ms", 0); error_rate = payload.get("error_rate", 0.0)
    if not isinstance(latency, int) or latency < 0 or latency > 5000: raise HTTPException(status_code=400, detail="latency_ms must be 0..5000")
    if not isinstance(error_rate, (int,float)) or error_rate < 0 or error_rate > 1: raise HTTPException(status_code=400, detail="error_rate must be 0..1")
    FAULT_STATE.update(latency_ms=latency, error_rate=float(error_rate))
    LOG.warning("fault_injection_state_changed", extra={"fault_injected":True})
    return {"enabled":True,"latency_ms":latency,"error_rate":float(error_rate)}
