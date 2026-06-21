from httpx import AsyncClient

SERVICES_URL = "/api/v1/services"
REGISTER_URL = "/api/v1/auth/register"
LOGIN_URL = "/api/v1/auth/login"
STORES_URL = "/api/v1/stores"
INVITES_URL = "/api/v1/invites"

ADMIN_USER = {
    "name": "Admin Owner",
    "email": "admin@test.com",
    "password": "password123",
    "role": "store_admin",
    "accepted_terms": True,
}

OTHER_ADMIN = {
    "name": "Outro Admin",
    "email": "other@test.com",
    "password": "password123",
    "role": "store_admin",
    "accepted_terms": True,
}

CLIENT_USER = {
    "name": "Cliente",
    "email": "client@test.com",
    "password": "password123",
    "role": "client",
    "accepted_terms": True,
}

ANON_PROF = {
    "name": "Profissional Externo",
    "email": "prof@test.com",
    "password": "senha123",
    "accepted_terms": True,
}

VALID_STORE = {"name": "Salão da Ana"}

VALID_SERVICE = {
    "name": "Corte Feminino",
    "description": "Corte com lavagem",
    "default_price": "80.00",
    "default_duration_minutes": 60,
}


async def _register_and_login(client: AsyncClient, user: dict) -> str:
    await client.post(REGISTER_URL, json=user)
    res = await client.post(LOGIN_URL, json={"email": user["email"], "password": user["password"]})
    return res.json()["access_token"]


async def _create_store_and_invite(client: AsyncClient, token: str) -> tuple[str, str]:
    store_res = await client.post(
        STORES_URL, json=VALID_STORE, headers={"Authorization": f"Bearer {token}"}
    )
    store_id = store_res.json()["id"]
    invite_res = await client.post(
        f"{STORES_URL}/{store_id}/invites",
        headers={"Authorization": f"Bearer {token}"},
    )
    return store_id, invite_res.json()["token"]


async def _become_professional_via_invite(client: AsyncClient, admin_token: str) -> str:
    """Creates a store, invites anon prof, returns prof token."""
    _, invite_token = await _create_store_and_invite(client, admin_token)
    accept_res = await client.post(
        f"{INVITES_URL}/{invite_token}/accept", json=ANON_PROF
    )
    return accept_res.json()["access_token"]


async def test_create_service_unauthorized(client: AsyncClient):
    response = await client.post(SERVICES_URL, json=VALID_SERVICE)
    assert response.status_code == 401


async def test_create_service_client_forbidden(client: AsyncClient):
    client_token = await _register_and_login(client, CLIENT_USER)

    response = await client.post(
        SERVICES_URL,
        json=VALID_SERVICE,
        headers={"Authorization": f"Bearer {client_token}"},
    )
    assert response.status_code == 403
