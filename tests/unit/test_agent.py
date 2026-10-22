import importlib.util, pathlib, sys, time
from fastapi.testclient import TestClient
APP_PATH=pathlib.Path(__file__).parents[2]/"services"/"ai-sre-agent"/"app.py"
spec=importlib.util.spec_from_file_location("ai_agent_app",APP_PATH); module=importlib.util.module_from_spec(spec); sys.modules[spec.name]=module; spec.loader.exec_module(module)
def test_deterministic_analysis_discloses_missing_evidence():
    req=module.IncidentRequest(incident_id="test-1",service="sample-api",start_unix=100,end_unix=200)
    report=module.deterministic_analysis(req,{"prometheus_latency_bucket":{"query_error":"timeout"},"prometheus_error_rate":{"query_error":"timeout"},"loki_logs":{"query_error":"timeout"},"tempo_trace":{"status":"not_queried"}})
    assert report["confidence"]=="low"
    assert report["evidence_gaps"]
    assert "Unknown" in report["likely_root_cause"]
def test_rejects_invalid_window():
    with TestClient(module.app) as client:
        now=int(time.time())
        response=client.post("/analyze",json={"start_unix":now,"end_unix":now-1})
        assert response.status_code==400

def test_detects_5xx_from_loki_when_prometheus_results_are_empty():
    req = module.IncidentRequest(
        incident_id="test-loki-5xx",
        service="sample-api-assessment",
        start_unix=100,
        end_unix=200,
    )

    evidence = {
        "prometheus_latency_bucket": {
            "status": "success",
            "data": {"result": []},
        },
        "prometheus_error_rate": {
            "status": "success",
            "data": {"result": []},
        },
        "loki_logs": {
            "status": "success",
            "data": {
                "result": [
                    {
                        "stream": {"pod": "sample-api-assessment-test"},
                        "values": [
                            [
                                "150000000000",
                                '{"status_code":500,"path":"/api/work"}',
                            ],
                            [
                                "160000000000",
                                '{"status_code":200,"path":"/health"}',
                            ],
                        ],
                    }
                ]
            },
        },
        "tempo_trace": {"status": "not_queried"},
    }

    report = module.deterministic_analysis(req, evidence)

    assert report["observations"]["nonzero_5xx_rate_observed"] is True
    assert report["observations"]["matching_log_entries"] == 2
    assert "1 HTTP 5xx" in report["summary"]
    assert report["confidence"] == "medium"
    assert "underlying cause is not yet established" in report["likely_root_cause"]
