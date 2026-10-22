import importlib.util, pathlib, sys
from fastapi.testclient import TestClient
APP_PATH=pathlib.Path(__file__).parents[2]/"services"/"sample-api"/"app.py"
spec=importlib.util.spec_from_file_location("sample_api_app",APP_PATH); module=importlib.util.module_from_spec(spec); sys.modules[spec.name]=module; spec.loader.exec_module(module)
def test_health_endpoints():
    with TestClient(module.app) as client:
        assert client.get("/health/live").json()=={"status":"ok"}
        assert client.get("/health/ready").status_code==200
def test_work_and_metrics():
    with TestClient(module.app) as client:
        assert client.get("/api/work").json()["status"]=="ok"
        metrics=client.get("/metrics").text
        assert "http_server_requests_total" in metrics
def test_fault_endpoint_disabled_by_default(monkeypatch):
    monkeypatch.setattr(module,"FAULT_ENABLED",False)
    with TestClient(module.app) as client:
        assert client.post("/admin/fault",json={"latency_ms":100}).status_code==404
