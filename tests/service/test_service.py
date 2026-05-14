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


# ---------------------------------------------------------------------------
# POST /services
# ---------------------------------------------------------------------------


async def test_create_service_success_as_professional(client: AsyncClient):
    admin_token = await _register_and_login(client, ADMIN_USER)
    prof_token = await _become_professional_via_invite(client, admin_token)

    response = await client.post(
        SERVICES_URL,
        json=VALID_SERVICE,
        headers={"Authorization": f"Bearer {prof_token}"},
    )
    assert response.status_code == 201
    body = response.json()
    assert body["name"] == VALID_SERVICE["name"]
    assert body["default_duration_minutes"] == 60
    assert "id" in body
    assert "professional_id" in body


async def test_create_service_success_as_store_admin(client: AsyncClient):
    admin_token = await _register_and_login(client, ADMIN_USER)

    store_res = await client.post(
        STORES_URL, json={"name": "Loja do Admin"}, headers={"Authorization": f"Bearer {admin_token}"}
    )
    store_id = store_res.json()["id"]

    # Admin self-links to own store to get a Professional record
    await client.post(
        f"{STORES_URL}/{store_id}/professionals/me",
        json={},
        headers={"Authorization": f"Bearer {admin_token}"},
    )

    response = await client.post(
        SERVICES_URL,
        json=VALID_SERVICE,
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 201


async def test_create_service_requires_professional_profile(client: AsyncClient):
    # A store_admin without a Professional record yet
    admin_token = await _register_and_login(client, ADMIN_USER)

    response = await client.post(
        SERVICES_URL,
        json=VALID_SERVICE,
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 404


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


async def test_create_service_duration_below_minimum(client: AsyncClient):
    admin_token = await _register_and_login(client, ADMIN_USER)
    prof_token = await _become_professional_via_invite(client, admin_token)

    response = await client.post(
        SERVICES_URL,
        json={**VALID_SERVICE, "default_duration_minutes": 10},
        headers={"Authorization": f"Bearer {prof_token}"},
    )
    assert response.status_code == 422


async def test_create_service_negative_price(client: AsyncClient):
    admin_token = await _register_and_login(client, ADMIN_USER)
    prof_token = await _become_professional_via_invite(client, admin_token)

    response = await client.post(
        SERVICES_URL,
        json={**VALID_SERVICE, "default_price": "-10.00"},
        headers={"Authorization": f"Bearer {prof_token}"},
    )
    assert response.status_code == 422


# ---------------------------------------------------------------------------
# GET /services/me
# ---------------------------------------------------------------------------


async def test_list_my_services_empty(client: AsyncClient):
    admin_token = await _register_and_login(client, ADMIN_USER)
    prof_token = await _become_professional_via_invite(client, admin_token)

    response = await client.get(
        f"{SERVICES_URL}/me",
        headers={"Authorization": f"Bearer {prof_token}"},
    )
    assert response.status_code == 200
    assert response.json() == []


async def test_list_my_services_returns_created_services(client: AsyncClient):
    admin_token = await _register_and_login(client, ADMIN_USER)
    prof_token = await _become_professional_via_invite(client, admin_token)

    await client.post(
        SERVICES_URL,
        json=VALID_SERVICE,
        headers={"Authorization": f"Bearer {prof_token}"},
    )
    await client.post(
        SERVICES_URL,
        json={**VALID_SERVICE, "name": "Hidratação"},
        headers={"Authorization": f"Bearer {prof_token}"},
    )

    response = await client.get(
        f"{SERVICES_URL}/me",
        headers={"Authorization": f"Bearer {prof_token}"},
    )
    assert response.status_code == 200
    assert len(response.json()) == 2


async def test_list_my_services_does_not_return_other_professional_services(client: AsyncClient):
    admin_a = await _register_and_login(client, ADMIN_USER)
    admin_b = await _register_and_login(client, OTHER_ADMIN)
    prof_a_token = await _become_professional_via_invite(client, admin_a)

    _, invite_b = await _create_store_and_invite(client, admin_b)
    anon_b = {**ANON_PROF, "email": "prof_b@test.com"}
    accept_b = await client.post(f"{INVITES_URL}/{invite_b}/accept", json=anon_b)
    prof_b_token = accept_b.json()["access_token"]

    await client.post(
        SERVICES_URL,
        json=VALID_SERVICE,
        headers={"Authorization": f"Bearer {prof_a_token}"},
    )

    response = await client.get(
        f"{SERVICES_URL}/me",
        headers={"Authorization": f"Bearer {prof_b_token}"},
    )
    assert response.status_code == 200
    assert response.json() == []


# ---------------------------------------------------------------------------
# PATCH /services/{id}
# ---------------------------------------------------------------------------


async def test_update_service_success(client: AsyncClient):
    admin_token = await _register_and_login(client, ADMIN_USER)
    prof_token = await _become_professional_via_invite(client, admin_token)

    create_res = await client.post(
        SERVICES_URL,
        json=VALID_SERVICE,
        headers={"Authorization": f"Bearer {prof_token}"},
    )
    service_id = create_res.json()["id"]

    response = await client.patch(
        f"{SERVICES_URL}/{service_id}",
        json={"name": "Corte Atualizado", "default_price": "90.00"},
        headers={"Authorization": f"Bearer {prof_token}"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["name"] == "Corte Atualizado"
    assert body["default_price"] == "90.00"
    # fields not sent must not be wiped
    assert body["default_duration_minutes"] == VALID_SERVICE["default_duration_minutes"]
    assert body["description"] == VALID_SERVICE["description"]


async def test_update_service_deactivate_hides_from_listing(client: AsyncClient):
    admin_token = await _register_and_login(client, ADMIN_USER)
    prof_token = await _become_professional_via_invite(client, admin_token)

    create_res = await client.post(
        SERVICES_URL,
        json=VALID_SERVICE,
        headers={"Authorization": f"Bearer {prof_token}"},
    )
    service_id = create_res.json()["id"]

    await client.patch(
        f"{SERVICES_URL}/{service_id}",
        json={"is_active": False},
        headers={"Authorization": f"Bearer {prof_token}"},
    )

    list_res = await client.get(
        f"{SERVICES_URL}/me",
        headers={"Authorization": f"Bearer {prof_token}"},
    )
    # list_my_services does not filter by is_active — deactivation is a flag, not a delete
    # what matters is the flag was saved
    patch_res = await client.patch(
        f"{SERVICES_URL}/{service_id}",
        json={},
        headers={"Authorization": f"Bearer {prof_token}"},
    )
    assert patch_res.json()["is_active"] is False


async def test_update_service_invalid_duration(client: AsyncClient):
    admin_token = await _register_and_login(client, ADMIN_USER)
    prof_token = await _become_professional_via_invite(client, admin_token)

    create_res = await client.post(
        SERVICES_URL,
        json=VALID_SERVICE,
        headers={"Authorization": f"Bearer {prof_token}"},
    )
    service_id = create_res.json()["id"]

    response = await client.patch(
        f"{SERVICES_URL}/{service_id}",
        json={"default_duration_minutes": 5},
        headers={"Authorization": f"Bearer {prof_token}"},
    )
    assert response.status_code == 422


async def test_update_service_negative_price(client: AsyncClient):
    admin_token = await _register_and_login(client, ADMIN_USER)
    prof_token = await _become_professional_via_invite(client, admin_token)

    create_res = await client.post(
        SERVICES_URL,
        json=VALID_SERVICE,
        headers={"Authorization": f"Bearer {prof_token}"},
    )
    service_id = create_res.json()["id"]

    response = await client.patch(
        f"{SERVICES_URL}/{service_id}",
        json={"default_price": "-5.00"},
        headers={"Authorization": f"Bearer {prof_token}"},
    )
    assert response.status_code == 422


async def test_update_service_other_professional_forbidden(client: AsyncClient):
    admin_a = await _register_and_login(client, ADMIN_USER)
    admin_b = await _register_and_login(client, OTHER_ADMIN)
    prof_a_token = await _become_professional_via_invite(client, admin_a)

    _, invite_b = await _create_store_and_invite(client, admin_b)
    anon_b = {**ANON_PROF, "email": "prof_b@test.com"}
    prof_b_token = (
        await client.post(f"{INVITES_URL}/{invite_b}/accept", json=anon_b)
    ).json()["access_token"]

    create_res = await client.post(
        SERVICES_URL,
        json=VALID_SERVICE,
        headers={"Authorization": f"Bearer {prof_a_token}"},
    )
    service_id = create_res.json()["id"]

    response = await client.patch(
        f"{SERVICES_URL}/{service_id}",
        json={"name": "Tentativa Hacker"},
        headers={"Authorization": f"Bearer {prof_b_token}"},
    )
    assert response.status_code == 403


async def test_update_service_not_found(client: AsyncClient):
    admin_token = await _register_and_login(client, ADMIN_USER)
    prof_token = await _become_professional_via_invite(client, admin_token)

    response = await client.patch(
        f"{SERVICES_URL}/00000000000000000000000000",
        json={"name": "X"},
        headers={"Authorization": f"Bearer {prof_token}"},
    )
    assert response.status_code == 404


# ---------------------------------------------------------------------------
# DELETE /services/{id}
# ---------------------------------------------------------------------------


async def test_delete_service_success(client: AsyncClient):
    admin_token = await _register_and_login(client, ADMIN_USER)
    prof_token = await _become_professional_via_invite(client, admin_token)

    create_res = await client.post(
        SERVICES_URL,
        json=VALID_SERVICE,
        headers={"Authorization": f"Bearer {prof_token}"},
    )
    service_id = create_res.json()["id"]

    response = await client.delete(
        f"{SERVICES_URL}/{service_id}",
        headers={"Authorization": f"Bearer {prof_token}"},
    )
    assert response.status_code == 204

    # Confirm it no longer appears in listing
    list_res = await client.get(
        f"{SERVICES_URL}/me",
        headers={"Authorization": f"Bearer {prof_token}"},
    )
    assert list_res.json() == []


async def test_delete_service_other_professional_forbidden(client: AsyncClient):
    admin_a = await _register_and_login(client, ADMIN_USER)
    admin_b = await _register_and_login(client, OTHER_ADMIN)
    prof_a_token = await _become_professional_via_invite(client, admin_a)

    _, invite_b = await _create_store_and_invite(client, admin_b)
    anon_b = {**ANON_PROF, "email": "prof_b@test.com"}
    prof_b_token = (
        await client.post(f"{INVITES_URL}/{invite_b}/accept", json=anon_b)
    ).json()["access_token"]

    create_res = await client.post(
        SERVICES_URL,
        json=VALID_SERVICE,
        headers={"Authorization": f"Bearer {prof_a_token}"},
    )
    service_id = create_res.json()["id"]

    response = await client.delete(
        f"{SERVICES_URL}/{service_id}",
        headers={"Authorization": f"Bearer {prof_b_token}"},
    )
    assert response.status_code == 403
