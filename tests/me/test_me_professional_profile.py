from httpx import AsyncClient

ME_PROFESSIONAL_URL = "/api/v1/me/professional"
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


async def _register_and_login(client: AsyncClient, user: dict) -> str:
    await client.post(REGISTER_URL, json=user)
    res = await client.post(LOGIN_URL, json={"email": user["email"], "password": user["password"]})
    return res.json()["access_token"]


async def _become_professional_via_invite(client: AsyncClient, admin_token: str) -> str:
    store_res = await client.post(
        STORES_URL, json=VALID_STORE, headers={"Authorization": f"Bearer {admin_token}"}
    )
    store_id = store_res.json()["id"]
    invite_res = await client.post(
        f"{STORES_URL}/{store_id}/invites",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    accept_res = await client.post(
        f"{INVITES_URL}/{invite_res.json()['token']}/accept", json=ANON_PROF
    )
    return accept_res.json()["access_token"]


async def test_get_my_professional_profile_not_found(client: AsyncClient):
    admin_token = await _register_and_login(client, ADMIN_USER)

    response = await client.get(
        ME_PROFESSIONAL_URL,
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 404


async def test_get_my_professional_profile_unauthorized(client: AsyncClient):
    response = await client.get(ME_PROFESSIONAL_URL)
    assert response.status_code == 401


async def test_update_my_professional_profile_client_forbidden(client: AsyncClient):
    client_token = await _register_and_login(client, CLIENT_USER)

    response = await client.patch(
        ME_PROFESSIONAL_URL,
        json={"bio": "Tentativa"},
        headers={"Authorization": f"Bearer {client_token}"},
    )
    assert response.status_code == 403


async def test_update_my_professional_profile_unauthorized(client: AsyncClient):
    response = await client.patch(ME_PROFESSIONAL_URL, json={"bio": "X"})
    assert response.status_code == 401
