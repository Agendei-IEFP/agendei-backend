from httpx import AsyncClient

STORES_URL = "/api/v1/stores"
REGISTER_URL = "/api/v1/auth/register"
LOGIN_URL = "/api/v1/auth/login"
ME_URL = "/api/v1/me"

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

CLIENT_USER = {
    "name": "Cliente",
    "email": "cliente@example.com",
    "password": "password123",
    "role": "client",
    "accepted_terms": True,
}

VALID_STORE = {"name": "Salão da Ana"}


async def _get_token(client: AsyncClient, user: dict) -> str:
    await client.post(REGISTER_URL, json=user)
    response = await client.post(
        LOGIN_URL, json={"email": user["email"], "password": user["password"]}
    )
    return response.json()["access_token"]


async def _create_store(client: AsyncClient, token: str) -> str:
    response = await client.post(
        STORES_URL,
        json=VALID_STORE,
        headers={"Authorization": f"Bearer {token}"},
    )
    return response.json()["id"]


async def _link_admin_as_professional(client: AsyncClient, token: str, store_id: str) -> dict:
    response = await client.post(
        f"{STORES_URL}/{store_id}/professionals/me",
        json={},
        headers={"Authorization": f"Bearer {token}"},
    )
    return response.json()


# ---------------------------------------------------------------------------
# POST /stores/{store_id}/professionals/me — admin registers as professional
# ---------------------------------------------------------------------------


async def test_add_admin_as_professional_success(client: AsyncClient):
    token = await _get_token(client, ADMIN_USER)
    store_id = await _create_store(client, token)

    response = await client.post(
        f"{STORES_URL}/{store_id}/professionals/me",
        json={"bio": "Especialista em cortes", "photo_url": None},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 201
    body = response.json()
    assert "id" in body
    assert body["store_id"] == store_id
    assert "professional_id" in body
    assert body["is_active"] is True
    assert "deleted_at" not in body


async def test_add_admin_as_professional_empty_payload(client: AsyncClient):
    token = await _get_token(client, ADMIN_USER)
    store_id = await _create_store(client, token)

    response = await client.post(
        f"{STORES_URL}/{store_id}/professionals/me",
        json={},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 201


async def test_add_admin_as_professional_not_owner(client: AsyncClient):
    admin_token = await _get_token(client, ADMIN_USER)
    other_token = await _get_token(client, OTHER_ADMIN_USER)
    store_id = await _create_store(client, admin_token)

    response = await client.post(
        f"{STORES_URL}/{store_id}/professionals/me",
        json={},
        headers={"Authorization": f"Bearer {other_token}"},
    )
    assert response.status_code == 403


async def test_add_admin_as_professional_duplicate(client: AsyncClient):
    token = await _get_token(client, ADMIN_USER)
    store_id = await _create_store(client, token)

    await client.post(
        f"{STORES_URL}/{store_id}/professionals/me",
        json={},
        headers={"Authorization": f"Bearer {token}"},
    )
    response = await client.post(
        f"{STORES_URL}/{store_id}/professionals/me",
        json={},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 409


async def test_add_admin_as_professional_unauthenticated(client: AsyncClient):
    token = await _get_token(client, ADMIN_USER)
    store_id = await _create_store(client, token)

    response = await client.post(
        f"{STORES_URL}/{store_id}/professionals/me",
        json={},
    )
    assert response.status_code == 401


async def test_add_admin_as_professional_client_role(client: AsyncClient):
    admin_token = await _get_token(client, ADMIN_USER)
    client_token = await _get_token(client, CLIENT_USER)
    store_id = await _create_store(client, admin_token)

    response = await client.post(
        f"{STORES_URL}/{store_id}/professionals/me",
        json={},
        headers={"Authorization": f"Bearer {client_token}"},
    )
    assert response.status_code == 403


# ---------------------------------------------------------------------------
# GET /stores/{store_id}/professionals — list professionals
# ---------------------------------------------------------------------------


async def test_list_store_professionals_empty(client: AsyncClient):
    token = await _get_token(client, ADMIN_USER)
    store_id = await _create_store(client, token)

    response = await client.get(f"{STORES_URL}/{store_id}/professionals")
    assert response.status_code == 200
    assert response.json() == []


async def test_list_store_professionals_with_one(client: AsyncClient):
    token = await _get_token(client, ADMIN_USER)
    store_id = await _create_store(client, token)
    await _link_admin_as_professional(client, token, store_id)

    response = await client.get(f"{STORES_URL}/{store_id}/professionals")
    assert response.status_code == 200
    body = response.json()
    assert len(body) == 1
    assert "id" in body[0]
    assert "user_id" in body[0]
    assert "deleted_at" not in body[0]


async def test_list_store_professionals_store_not_found(client: AsyncClient):
    response = await client.get(f"{STORES_URL}/nonexistent-store-id/professionals")
    assert response.status_code == 404


# ---------------------------------------------------------------------------
# PATCH /stores/{store_id}/professionals/{professional_id} — update profile
# ---------------------------------------------------------------------------


async def test_update_professional_success(client: AsyncClient):
    token = await _get_token(client, ADMIN_USER)
    store_id = await _create_store(client, token)
    link = await _link_admin_as_professional(client, token, store_id)
    professional_id = link["professional_id"]

    response = await client.patch(
        f"{STORES_URL}/{store_id}/professionals/{professional_id}",
        json={"bio": "Nova bio", "is_active": False},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["bio"] == "Nova bio"
    assert body["is_active"] is False


async def test_update_professional_not_owner(client: AsyncClient):
    admin_token = await _get_token(client, ADMIN_USER)
    other_token = await _get_token(client, OTHER_ADMIN_USER)
    store_id = await _create_store(client, admin_token)
    link = await _link_admin_as_professional(client, admin_token, store_id)
    professional_id = link["professional_id"]

    response = await client.patch(
        f"{STORES_URL}/{store_id}/professionals/{professional_id}",
        json={"bio": "tentativa"},
        headers={"Authorization": f"Bearer {other_token}"},
    )
    assert response.status_code == 403


async def test_update_professional_unauthenticated(client: AsyncClient):
    token = await _get_token(client, ADMIN_USER)
    store_id = await _create_store(client, token)
    link = await _link_admin_as_professional(client, token, store_id)
    professional_id = link["professional_id"]

    response = await client.patch(
        f"{STORES_URL}/{store_id}/professionals/{professional_id}",
        json={"bio": "tentativa"},
    )
    assert response.status_code == 401


async def test_update_professional_not_found(client: AsyncClient):
    token = await _get_token(client, ADMIN_USER)
    store_id = await _create_store(client, token)

    response = await client.patch(
        f"{STORES_URL}/{store_id}/professionals/nonexistent-id",
        json={"bio": "tentativa"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 404


# ---------------------------------------------------------------------------
# DELETE /stores/{store_id}/professional-links/{professional_store_id}
# ---------------------------------------------------------------------------


async def test_unlink_professional_success(client: AsyncClient):
    token = await _get_token(client, ADMIN_USER)
    store_id = await _create_store(client, token)
    link = await _link_admin_as_professional(client, token, store_id)
    link_id = link["id"]

    response = await client.delete(
        f"{STORES_URL}/{store_id}/professional-links/{link_id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 204

    # Professional should no longer appear in the list
    list_response = await client.get(f"{STORES_URL}/{store_id}/professionals")
    assert list_response.json() == []


async def test_unlink_professional_not_owner(client: AsyncClient):
    admin_token = await _get_token(client, ADMIN_USER)
    other_token = await _get_token(client, OTHER_ADMIN_USER)
    store_id = await _create_store(client, admin_token)
    link = await _link_admin_as_professional(client, admin_token, store_id)
    link_id = link["id"]

    response = await client.delete(
        f"{STORES_URL}/{store_id}/professional-links/{link_id}",
        headers={"Authorization": f"Bearer {other_token}"},
    )
    assert response.status_code == 403


async def test_unlink_professional_unauthenticated(client: AsyncClient):
    token = await _get_token(client, ADMIN_USER)
    store_id = await _create_store(client, token)
    link = await _link_admin_as_professional(client, token, store_id)
    link_id = link["id"]

    response = await client.delete(
        f"{STORES_URL}/{store_id}/professional-links/{link_id}",
    )
    assert response.status_code == 401


async def test_unlink_professional_not_found(client: AsyncClient):
    token = await _get_token(client, ADMIN_USER)
    store_id = await _create_store(client, token)

    response = await client.delete(
        f"{STORES_URL}/{store_id}/professional-links/nonexistent-id",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 404


# ---------------------------------------------------------------------------
# GET /me/professional-stores — list own professional store links
# ---------------------------------------------------------------------------


async def test_list_my_professional_stores_empty(client: AsyncClient):
    token = await _get_token(client, ADMIN_USER)

    response = await client.get(
        f"{ME_URL}/professional-stores",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    assert response.json() == []


async def test_list_my_professional_stores_with_link(client: AsyncClient):
    token = await _get_token(client, ADMIN_USER)
    store_id = await _create_store(client, token)
    await _link_admin_as_professional(client, token, store_id)

    response = await client.get(
        f"{ME_URL}/professional-stores",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    body = response.json()
    assert len(body) == 1
    assert body[0]["store_id"] == store_id


async def test_list_my_professional_stores_unauthenticated(client: AsyncClient):
    response = await client.get(f"{ME_URL}/professional-stores")
    assert response.status_code == 401
