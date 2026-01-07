"""Test API endpoints."""

import pytest
from fastapi.testclient import TestClient
from api import app


@pytest.fixture
def client():
    """Create test client."""
    return TestClient(app)


def test_health_check(client):
    """Test health endpoint."""
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["version"] == "2.0.0"


def test_health_check_alt(client):
    """Test /health endpoint."""
    response = client.get("/health")
    assert response.status_code == 200


def test_list_jobs_empty(client):
    """Test listing jobs when empty."""
    response = client.get("/api/v1/jobs")
    assert response.status_code == 200
    assert isinstance(response.json(), list)


def test_get_job_not_found(client):
    """Test getting non-existent job."""
    response = client.get("/api/v1/jobs/12345678-1234-1234-1234-123456789abc")
    assert response.status_code == 404


def test_invalid_job_id(client):
    """Test invalid job ID format."""
    response = client.get("/api/v1/jobs/invalid-id")
    assert response.status_code == 400


def test_create_job_no_api_key(client, monkeypatch):
    """Test job creation without API key."""
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    response = client.post(
        "/api/v1/jobs",
        json={"company_name": "Test", "target_count": 10}
    )
    assert response.status_code == 500
    assert "GEMINI_API_KEY" in response.json()["detail"]


def test_generate_validation(client):
    """Test validation on generate endpoint."""
    response = client.post(
        "/api/v1/generate",
        json={"company_name": "", "target_count": 10}
    )
    assert response.status_code == 422  # Validation error
