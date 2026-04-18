import pytest
from httpx import AsyncClient

REGISTER_URL = "/api/v1/auth/register"
LOGIN_URL = "/api/v1/auth/login"
REFRESH_URL = "/api/v1/auth/refresh"
LOGOUT_URL = "/api/v1/auth/logout"

VALID_USER = {
    "nome": "Test User",
    "email": "test@example.com",
    "senha": "password123",
    "role": "cliente",
    "accepted_terms": True,
}


# ---------------------------------------------------------------------------
# Register
# ---------------------------------------------------------------------------


async def test_register_success(client: AsyncClient):
    response = await client.post(REGISTER_URL, json=VALID_USER)
    assert response.status_code == 201
    body = response.json()
    assert body["email"] == VALID_USER["email"]
    assert body["nome"] == VALID_USER["nome"]
    assert body["role"] == VALID_USER["role"]
    assert "id" in body
    assert "senha" not in body
    assert "senha_hash" not in body


async def test_register_duplicate_email(client: AsyncClient):
    await client.post(REGISTER_URL, json=VALID_USER)
    response = await client.post(REGISTER_URL, json=VALID_USER)
    assert response.status_code == 409
    assert response.json() == {"detail": "Email já cadastrado"}


async def test_register_short_password(client: AsyncClient):
    data = {**VALID_USER, "senha": "short"}
    response = await client.post(REGISTER_URL, json=data)
    assert response.status_code == 422


async def test_register_terms_not_accepted(client: AsyncClient):
    data = {**VALID_USER, "accepted_terms": False}
    response = await client.post(REGISTER_URL, json=data)
    assert response.status_code == 422


# ---------------------------------------------------------------------------
# Login
# ---------------------------------------------------------------------------


async def test_login_success(client: AsyncClient):
    await client.post(REGISTER_URL, json=VALID_USER)
    response = await client.post(LOGIN_URL, json={
        "email": VALID_USER["email"],
        "senha": VALID_USER["senha"],
    })
    assert response.status_code == 200
    body = response.json()
    assert "access_token" in body
    assert body["token_type"] == "bearer"
    assert body["user"]["email"] == VALID_USER["email"]
    assert "refresh_token" in response.cookies


async def test_login_wrong_password(client: AsyncClient):
    await client.post(REGISTER_URL, json=VALID_USER)
    response = await client.post(LOGIN_URL, json={
        "email": VALID_USER["email"],
        "senha": "wrongpassword",
    })
    assert response.status_code == 401


async def test_login_unknown_email(client: AsyncClient):
    response = await client.post(LOGIN_URL, json={
        "email": "nobody@example.com",
        "senha": "password123",
    })
    assert response.status_code == 401


# ---------------------------------------------------------------------------
# Refresh
# ---------------------------------------------------------------------------


async def test_refresh_success(client: AsyncClient):
    await client.post(REGISTER_URL, json=VALID_USER)
    await client.post(LOGIN_URL, json={
        "email": VALID_USER["email"],
        "senha": VALID_USER["senha"],
    })
    response = await client.post(REFRESH_URL)
    assert response.status_code == 200
    body = response.json()
    assert "access_token" in body


async def test_refresh_no_cookie(client: AsyncClient):
    response = await client.post(REFRESH_URL)
    assert response.status_code == 401


# ---------------------------------------------------------------------------
# Logout
# ---------------------------------------------------------------------------


async def test_logout(client: AsyncClient):
    await client.post(REGISTER_URL, json=VALID_USER)
    await client.post(LOGIN_URL, json={
        "email": VALID_USER["email"],
        "senha": VALID_USER["senha"],
    })
    response = await client.post(LOGOUT_URL)
    assert response.status_code == 204
