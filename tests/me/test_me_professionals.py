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


# ---------------------------------------------------------------------------
# GET /me/professionals
# ---------------------------------------------------------------------------


async def test_list_my_professionals_empty(client: AsyncClient):
    token = await _get_token(client, ADMIN_USER)
    response = await client.get(
        ME_PROFESSIONALS_URL,
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    assert response.json() == []


async def test_list_my_professionals_returns_linked_professional(client: AsyncClient):
    token = await _get_token(client, ADMIN_USER)
    _, invite_token = await _create_store_and_invite(client, token)

    await client.post(f"{INVITES_URL}/{invite_token}/accept", json=ANON_PROF)

    response = await client.get(
        ME_PROFESSIONALS_URL,
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    body = response.json()
    assert len(body) == 1
    assert body[0]["name"] == ANON_PROF["name"]
    assert body[0]["store_name"] == VALID_STORE["name"]
    assert "id" in body[0]
    assert "store_id" in body[0]
    assert "user_id" in body[0]


async def test_list_my_professionals_only_own_stores(client: AsyncClient):
    token_a = await _get_token(client, ADMIN_USER)
    token_b = await _get_token(client, OTHER_ADMIN_USER)

    _, invite_token = await _create_store_and_invite(client, token_b)
    await client.post(f"{INVITES_URL}/{invite_token}/accept", json=ANON_PROF)

    response = await client.get(
        ME_PROFESSIONALS_URL,
        headers={"Authorization": f"Bearer {token_a}"},
    )
    assert response.status_code == 200
    assert response.json() == []


async def test_list_my_professionals_unauthorized(client: AsyncClient):
    response = await client.get(ME_PROFESSIONALS_URL)
    assert response.status_code == 401
