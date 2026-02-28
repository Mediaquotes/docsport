"""Tests for FastAPI API endpoints."""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))


@pytest.fixture
def client():
    """Create a FastAPI test client."""
    from httpx import ASGITransport, AsyncClient

    from backend.app import DocsPortApp

    app_instance = DocsPortApp()
    transport = ASGITransport(app=app_instance.app)
    return AsyncClient(transport=transport, base_url="http://test")


@pytest.mark.asyncio
async def test_health_check(client):
    response = await client.get("/api/health")
    assert response.status_code == 200

    data = response.json()
    assert data["status"] == "healthy"
    assert data["service"] == "DocsPort"
    assert data["version"] == "2.0.0"


@pytest.mark.asyncio
async def test_config_endpoint(client):
    response = await client.get("/api/config")
    assert response.status_code == 200

    data = response.json()
    assert "status" in data


@pytest.mark.asyncio
async def test_list_files(client):
    response = await client.get("/api/files")
    assert response.status_code == 200

    data = response.json()
    assert "files" in data
    assert isinstance(data["files"], list)


@pytest.mark.asyncio
async def test_get_file_not_found(client):
    response = await client.get("/api/files/nonexistent_file.py")
    assert response.status_code == 404 or response.status_code == 403


@pytest.mark.asyncio
async def test_path_traversal_blocked(client):
    response = await client.get("/api/files/../../etc/passwd")
    assert response.status_code in (403, 404)


@pytest.mark.asyncio
async def test_execute_safe_code(client):
    response = await client.post("/api/execute", json={
        "code": 'print("test")',
        "execution_type": "python",
        "timeout": 5
    })
    assert response.status_code == 200

    data = response.json()
    assert data["success"] is True
    assert "test" in data["output"]


@pytest.mark.asyncio
async def test_execute_dangerous_code_blocked(client):
    response = await client.post("/api/execute", json={
        "code": "import os",
        "execution_type": "python",
        "timeout": 5
    })
    assert response.status_code == 200

    data = response.json()
    assert data["success"] is False


@pytest.mark.asyncio
async def test_execute_timeout_validation(client):
    response = await client.post("/api/execute", json={
        "code": 'print("hi")',
        "execution_type": "python",
        "timeout": 9999
    })
    # Pydantic should reject timeout > 60
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_root_returns_html(client):
    response = await client.get("/")
    assert response.status_code == 200
    assert "DocsPort" in response.text
