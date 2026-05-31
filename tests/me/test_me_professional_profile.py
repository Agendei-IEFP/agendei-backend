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


# ---------------------------------------------------------------------------
# GET /me/professional
# ---------------------------------------------------------------------------


async def test_get_my_professional_profile_success(client: AsyncClient):
    admin_token = await _register_and_login(client, ADMIN_USER)
    prof_token = await _become_professional_via_invite(client, admin_token)

    response = await client.get(
        ME_PROFESSIONAL_URL,
        headers={"Authorization": f"Bearer {prof_token}"},
    )
    assert response.status_code == 200
    body = response.json()
    assert "id" in body
    assert "user_id" in body
    assert body["bio"] is None          # newly created profile has no bio
    assert body["photo_url"] is None    # newly created profile has no photo
    assert body["is_active"] is True    # active by default
    assert "deleted_at" not in body     # internal field must not be exposed


async def test_get_my_professional_profile_not_found(client: AsyncClient):
    # store_admin that has not yet self-linked as professional
    admin_token = await _register_and_login(client, ADMIN_USER)

    response = await client.get(
        ME_PROFESSIONAL_URL,
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 404


async def test_get_my_professional_profile_unauthorized(client: AsyncClient):
    response = await client.get(ME_PROFESSIONAL_URL)
    assert response.status_code == 401


# ---------------------------------------------------------------------------
# PATCH /me/professional
# ---------------------------------------------------------------------------


async def test_update_my_professional_profile_success(client: AsyncClient):
    admin_token = await _register_and_login(client, ADMIN_USER)
    prof_token = await _become_professional_via_invite(client, admin_token)

    response = await client.patch(
        ME_PROFESSIONAL_URL,
        json={"bio": "Especialista em coloração", "photo_url": "https://example.com/photo.jpg"},
        headers={"Authorization": f"Bearer {prof_token}"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["bio"] == "Especialista em coloração"
    assert body["photo_url"] == "https://example.com/photo.jpg"


async def test_update_my_professional_profile_partial(client: AsyncClient):
    admin_token = await _register_and_login(client, ADMIN_USER)
    prof_token = await _become_professional_via_invite(client, admin_token)

    # Set bio first
    await client.patch(
        ME_PROFESSIONAL_URL,
        json={"bio": "Bio inicial"},
        headers={"Authorization": f"Bearer {prof_token}"},
    )

    # Update only photo_url — bio should remain
    response = await client.patch(
        ME_PROFESSIONAL_URL,
        json={"photo_url": "https://example.com/new.jpg"},
        headers={"Authorization": f"Bearer {prof_token}"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["bio"] == "Bio inicial"
    assert body["photo_url"] == "https://example.com/new.jpg"


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
