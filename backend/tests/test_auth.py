from __future__ import annotations

import pytest
import pytest_asyncio
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_register(client: AsyncClient):
    response = await client.post("/api/v1/auth/register", json={
        "org_name": "Test Org",
        "full_name": "Jane Doe",
        "email": "jane@test.com",
        "password": "securepass123",
    })
    assert response.status_code == 201
    data = response.json()
    assert "access_token" in data
    assert data["role"] == "owner"


@pytest.mark.asyncio
async def test_register_duplicate_email(client: AsyncClient):
    payload = {
        "org_name": "Test Org",
        "full_name": "Jane Doe",
        "email": "jane@test.com",
        "password": "securepass123",
    }
    await client.post("/api/v1/auth/register", json=payload)
    response = await client.post("/api/v1/auth/register", json=payload)
    assert response.status_code == 409


@pytest.mark.asyncio
async def test_login(client: AsyncClient):
    await client.post("/api/v1/auth/register", json={
        "org_name": "Test Org",
        "full_name": "Jane Doe",
        "email": "jane@test.com",
        "password": "securepass123",
    })

    response = await client.post("/api/v1/auth/login", json={
        "email": "jane@test.com",
        "password": "securepass123",
    })
    assert response.status_code == 200
    assert "access_token" in response.json()


@pytest.mark.asyncio
async def test_login_wrong_password(client: AsyncClient):
    await client.post("/api/v1/auth/register", json={
        "org_name": "Test Org",
        "full_name": "Jane Doe",
        "email": "jane@test.com",
        "password": "securepass123",
    })

    response = await client.post("/api/v1/auth/login", json={
        "email": "jane@test.com",
        "password": "wrongpassword",
    })
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_get_me(client: AsyncClient):
    reg = await client.post("/api/v1/auth/register", json={
        "org_name": "Test Org",
        "full_name": "Jane Doe",
        "email": "jane@test.com",
        "password": "securepass123",
    })
    token = reg.json()["access_token"]

    response = await client.get("/api/v1/auth/me", headers={
        "Authorization": f"Bearer {token}",
    })
    assert response.status_code == 200
    data = response.json()
    assert data["email"] == "jane@test.com"
    assert data["full_name"] == "Jane Doe"


@pytest.mark.asyncio
async def test_get_me_unauthorized(client: AsyncClient):
    response = await client.get("/api/v1/auth/me")
    assert response.status_code == 401
