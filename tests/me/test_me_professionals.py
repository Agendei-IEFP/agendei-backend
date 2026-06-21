from httpx import AsyncClient

ME_PROFESSIONALS_URL = "/api/v1/me/professionals"
STORES_URL = "/api/v1/stores"
INVITES_URL = "/api/v1/invites"
REGISTER_URL = "/api/v1/auth/register"
LOGIN_URL = "/api/v1/auth/login"

ADMIN_USER = {
    "name": "Admin Dono",
    "email": "admin@example.com",
    "password": "password123",
    "role": "store_admin",
    "accepted_terms": True,
}

OTHER_ADMIN_USER = {
    "name": "Outro Admin",
    "email": "outro@example.com",
    "password": "password123",
    "role": "store_admin",
    "accepted_terms": True,
}

ANON_PROF = {
    "name": "Nova Profissional",
    "email": "prof@example.com",
    "password": "senha123",
    "accepted_terms": True,
}

VALID_STORE = {"name": "Salão da Ana"}


async def _get_token(client: AsyncClient, user: dict) -> str:
    await client.post(REGISTER_URL, json=user)
    res = await client.post(LOGIN_URL, json={"email": user["email"], "password": user["password"]})
    return res.json()["access_token"]


async def _create_store_and_invite(client: AsyncClient, token: str) -> tuple[str, str]:
    store_res = await client.post(
        STORES_URL,
        json=VALID_STORE,
        headers={"Authorization": f"Bearer {token}"},
    )
    store_id = store_res.json()["id"]
    invite_res = await client.post(
        f"{STORES_URL}/{store_id}/invites",
        headers={"Authorization": f"Bearer {token}"},
    )
    invite_token = invite_res.json()["token"]
    return store_id, invite_token


async def test_list_my_professionals_empty(client: AsyncClient):
    token = await _get_token(client, ADMIN_USER)
    response = await client.get(
        ME_PROFESSIONALS_URL,
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    assert response.json() == []


async def test_list_my_professionals_unauthorized(client: AsyncClient):
    response = await client.get(ME_PROFESSIONALS_URL)
    assert response.status_code == 401
