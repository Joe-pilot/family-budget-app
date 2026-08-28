import os

os.environ["DATABASE_URL"] = "sqlite:////tmp/family-budget-security-tests.db"
os.environ["API_KEY"] = "test-api-key-with-sufficient-entropy"
os.environ["CORS_ALLOWED_ORIGINS"] = "https://budget.example"

from fastapi.testclient import TestClient

from app.main import app


AUTH = {"X-API-Key": os.environ["API_KEY"]}


def test_health_is_public_and_has_security_headers():
    with TestClient(app) as client:
        response = client.get("/api/health")
    assert response.status_code == 200
    assert response.headers["cache-control"] == "no-store"
    assert response.headers["x-content-type-options"] == "nosniff"
    assert response.headers["x-frame-options"] == "DENY"
    assert response.headers["referrer-policy"] == "no-referrer"


def test_financial_data_requires_authentication():
    with TestClient(app) as client:
        missing = client.get("/api/transactions")
        invalid = client.get("/api/transactions", headers={"X-API-Key": "wrong"})
        valid = client.get("/api/transactions", headers=AUTH)
    assert missing.status_code == 401
    assert invalid.status_code == 401
    assert valid.status_code == 200


def test_cors_only_allows_configured_origin():
    preflight_headers = {
        "Access-Control-Request-Method": "GET",
        "Access-Control-Request-Headers": "X-API-Key",
    }
    with TestClient(app) as client:
        allowed = client.options(
            "/api/transactions",
            headers={"Origin": "https://budget.example", **preflight_headers},
        )
        denied = client.options(
            "/api/transactions",
            headers={"Origin": "https://attacker.example", **preflight_headers},
        )
    assert allowed.status_code == 200
    assert allowed.headers["access-control-allow-origin"] == "https://budget.example"
    assert denied.status_code == 400
    assert "access-control-allow-origin" not in denied.headers


def test_oversized_request_is_rejected_before_parsing():
    with TestClient(app) as client:
        response = client.post(
            "/api/agent/log",
            headers={**AUTH, "Content-Length": "20000"},
            content=b"{}",
        )
    assert response.status_code == 413


def test_transaction_rejects_unknown_fields_and_categories():
    payload = {
        "date": "2026-01-01",
        "type": "Expense",
        "category": "Not a category",
        "subcategory": "Other",
        "amount": 10,
        "unexpected": "value",
    }
    with TestClient(app) as client:
        extra_field = client.post("/api/transactions", headers=AUTH, json=payload)
        payload.pop("unexpected")
        invalid_category = client.post("/api/transactions", headers=AUTH, json=payload)
    assert extra_field.status_code == 422
    assert invalid_category.status_code == 422


def test_query_ranges_are_bounded():
    with TestClient(app) as client:
        bad_month = client.get("/api/transactions?month=13", headers=AUTH)
        excessive_limit = client.get("/api/transactions?limit=501", headers=AUTH)
    assert bad_month.status_code == 422
    assert excessive_limit.status_code == 422
