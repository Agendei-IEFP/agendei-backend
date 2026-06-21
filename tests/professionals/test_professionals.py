import uuid

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


async def test_list_store_professionals_empty(client: AsyncClient):
    token = await _get_token(client, ADMIN_USER)
    store_id = await _create_store(client, token)

    response = await client.get(f"{STORES_URL}/{store_id}/professionals")
    assert response.status_code == 200
    assert response.json() == []


async def test_list_store_professionals_store_not_found(client: AsyncClient):
    response = await client.get(f"{STORES_URL}/nonexistent-store-id/professionals")
    assert response.status_code == 404


async def test_update_professional_not_found(client: AsyncClient):
    token = await _get_token(client, ADMIN_USER)
    store_id = await _create_store(client, token)

    response = await client.patch(
        f"{STORES_URL}/{store_id}/professionals/nonexistent-id",
        json={"bio": "tentativa"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 404


async def test_unlink_professional_not_found(client: AsyncClient):
    token = await _get_token(client, ADMIN_USER)
    store_id = await _create_store(client, token)

    response = await client.delete(
        f"{STORES_URL}/{store_id}/professional-links/nonexistent-id",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 404


def _make_professional_payload(**overrides: object) -> dict:
    unique = uuid.uuid4().hex[:8]
    base = {
        "name": "Maria Profissional",
        "email": f"pro+{unique}@example.com",
        "password": "Senha@123",
        "phone": "11999999999",
    }
    base.update(overrides)
    return base


async def test_create_professional_success(client: AsyncClient):
    token = await _get_token(client, ADMIN_USER)
    store_id = await _create_store(client, token)
    payload = _make_professional_payload()

    response = await client.post(
        f"{STORES_URL}/{store_id}/professionals",
        json=payload,
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 201
    body = response.json()
    assert body["name"] == payload["name"]
    assert body["store_id"] == store_id
    assert body["is_active"] is True
    assert "id" in body
    assert "user_id" in body
    assert "deleted_at" not in body


async def test_create_professional_minimal_payload(client: AsyncClient):
    token = await _get_token(client, ADMIN_USER)
    store_id = await _create_store(client, token)
    payload = _make_professional_payload(phone=None)

    response = await client.post(
        f"{STORES_URL}/{store_id}/professionals",
        json=payload,
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 201
    body = response.json()
    assert body["name"] == payload["name"]
    assert body["bio"] is None
    assert body["photo_url"] is None


async def test_create_professional_not_owner(client: AsyncClient):
    admin_token = await _get_token(client, ADMIN_USER)
    other_token = await _get_token(client, OTHER_ADMIN_USER)
    store_id = await _create_store(client, admin_token)
    payload = _make_professional_payload()

    response = await client.post(
        f"{STORES_URL}/{store_id}/professionals",
        json=payload,
        headers={"Authorization": f"Bearer {other_token}"},
    )
    assert response.status_code == 403


async def test_create_professional_duplicate_email(client: AsyncClient):
    token = await _get_token(client, ADMIN_USER)
    store_id = await _create_store(client, token)
    payload = _make_professional_payload()

    first = await client.post(
        f"{STORES_URL}/{store_id}/professionals",
        json=payload,
        headers={"Authorization": f"Bearer {token}"},
    )
    assert first.status_code == 201
    response = await client.post(
        f"{STORES_URL}/{store_id}/professionals",
        json=payload,
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 409


async def test_create_professional_unauthenticated(client: AsyncClient):
    token = await _get_token(client, ADMIN_USER)
    store_id = await _create_store(client, token)
    payload = _make_professional_payload()

    response = await client.post(
        f"{STORES_URL}/{store_id}/professionals",
        json=payload,
    )
    assert response.status_code == 401


async def test_create_professional_client_role_forbidden(client: AsyncClient):
    admin_token = await _get_token(client, ADMIN_USER)
    client_token = await _get_token(client, CLIENT_USER)
    store_id = await _create_store(client, admin_token)
    payload = _make_professional_payload()

    response = await client.post(
        f"{STORES_URL}/{store_id}/professionals",
        json=payload,
        headers={"Authorization": f"Bearer {client_token}"},
    )
    assert response.status_code == 403
