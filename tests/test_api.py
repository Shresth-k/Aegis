import pytest
from fastapi.testclient import TestClient
from aegis.api.main import app

client = TestClient(app)

def test_health_endpoint():
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "healthy"

    resp2 = client.get("/api/health")
    assert resp2.status_code == 200
    assert resp2.json()["status"] == "healthy"

def test_list_incidents():
    resp = client.get("/api/incidents")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    assert any(i["incident_id"] in ["INC-001", "ITOPS-001"] for i in data)

def test_chaos_endpoints():
    resp_inject = client.post("/api/chaos/inject?service=checkout-service&version=2.4.1")
    assert resp_inject.status_code == 200
    assert resp_inject.json()["status"] == "INJECTED"

    resp_reset = client.post("/api/chaos/reset?service=checkout-service")
    assert resp_reset.status_code == 200
    assert resp_reset.json()["status"] == "RESET"

def test_run_incident_and_approval_flow():
    # 1. Run incident investigation
    resp = client.post("/api/incidents/run", json={
        "incident_id": "TEST-API-001",
        "service": "checkout-service",
        "severity": "P1",
        "title": "API Test Incident",
        "description": "DB connection timeout test"
    })
    assert resp.status_code == 200
    state = resp.json()
    assert state["status"] == "PENDING_APPROVAL"
    assert state["diagnosis"]["recommended_action"] == "rollback_deployment"

    # 2. Approve remediation
    resp_approve = client.post("/api/incidents/approve", json={
        "incident_id": "TEST-API-001",
        "approved": True,
        "approved_by": "TestSRE",
        "reason": "Test verified"
    })
    assert resp_approve.status_code == 200
    approved_state = resp_approve.json()
    assert approved_state["status"] == "RESOLVED"
    assert approved_state["verification"]["status"] == "SUCCESS"

def test_frontend_spa_served():
    resp = client.get("/")
    assert resp.status_code == 200
    assert "AEGIS" in resp.text

def test_copilot_chat():
    # 1. Metrics inquiry tool dispatch
    resp_metrics = client.post("/api/chat", json={
        "incident_id": "INC-001",
        "message": "Show DB pool saturation and metrics"
    })
    assert resp_metrics.status_code == 200
    data_m = resp_metrics.json()
    assert "Live Telemetry" in data_m["reply"] or "Error Rate" in data_m["reply"]
    assert data_m["tool_call"] is not None
    assert data_m["tool_call"]["name"] == "get_metrics"

    # 2. Logs inquiry tool dispatch
    resp_logs = client.post("/api/chat", json={
        "incident_id": "INC-001",
        "message": "Show recent 5xx error logs"
    })
    assert resp_logs.status_code == 200
    data_l = resp_logs.json()
    assert data_l["tool_call"] is not None
    assert data_l["tool_call"]["name"] == "get_service_logs"

    # 3. General reasoning inquiry
    resp_gen = client.post("/api/chat", json={
        "incident_id": "INC-001",
        "message": "What is the recommended action?"
    })
    assert resp_gen.status_code == 200
    data_g = resp_gen.json()
    assert len(data_g["reply"]) > 0

    # 4. Multi-turn chat with history
    resp_history = client.post("/api/chat", json={
        "incident_id": "INC-001",
        "message": "Why is latency elevated?",
        "history": [
            {"role": "user", "text": "What is the current error rate?"},
            {"role": "assistant", "text": "Error rate is currently 38.5%."}
        ]
    })
    assert resp_history.status_code == 200
    assert len(resp_history.json()["reply"]) > 0

    # 5. Policy inquiry
    resp_pol = client.post("/api/chat", json={
        "incident_id": "INC-001",
        "message": "What policy guardrail applies?"
    })
    assert resp_pol.status_code == 200
    assert "Policy" in resp_pol.json()["reply"]

    # 6. Runbook inquiry
    resp_rb = client.post("/api/chat", json={
        "incident_id": "INC-001",
        "message": "Which runbooks are available?"
    })
    assert resp_rb.status_code == 200
    assert len(resp_rb.json()["reply"]) > 0


def test_traces_endpoint():
    resp = client.get("/api/incidents/INC-001/traces")
    assert resp.status_code == 200
    data = resp.json()
    assert "incident_id" in data
    assert "events" in data


def test_chaos_resets_incident():
    # Run incident to pending approval
    client.post("/api/incidents/run", json={"incident_id": "CHAOS-TEST", "service": "checkout-service"})
    # Inject chaos
    resp_chaos = client.post("/api/chaos/inject?service=checkout-service&version=2.4.1")
    assert resp_chaos.status_code == 200
    # Check that incident state was reset to OPEN
    resp_inc = client.get("/api/incidents/CHAOS-TEST")
    assert resp_inc.status_code == 200
    assert resp_inc.json()["status"] == "OPEN"


