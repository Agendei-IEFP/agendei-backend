from httpx import AsyncClient

REGISTER_URL = "/api/v1/auth/register"
LOGIN_URL = "/api/v1/auth/login"
STORES_URL = "/api/v1/stores"
INVITES_URL = "/api/v1/invites"
SERVICES_URL = "/api/v1/services"
PROF_STORES_BASE = "/api/v1/professional-stores"

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

ANON_PROF = {
    "name": "Profissional",
    "email": "prof@test.com",
    "password": "senha123",
    "accepted_terms": True,
}

VALID_STORE = {"name": "Salão da Ana"}

VALID_SERVICE = {
    "name": "Corte Feminino",
    "default_price": "80.00",
    "default_duration_minutes": 60,
}


async def _register_and_login(client: AsyncClient, user: dict) -> str:
    await client.post(REGISTER_URL, json=user)
    res = await client.post(LOGIN_URL, json={"email": user["email"], "password": user["password"]})
    return res.json()["access_token"]


async def _setup(client: AsyncClient) -> dict:
    """
    Creates admin, store, invites prof, returns tokens and ids.
    Returns: {admin_token, prof_token, store_id, professional_store_id}
    """
    admin_token = await _register_and_login(client, ADMIN_USER)

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
    prof_token = accept_res.json()["access_token"]

    # Get professional_store_id
    ps_res = await client.get(
        "/api/v1/me/professional-stores",
        headers={"Authorization": f"Bearer {prof_token}"},
    )
    professional_store_id = ps_res.json()[0]["id"]

    return {
        "admin_token": admin_token,
        "prof_token": prof_token,
        "store_id": store_id,
        "professional_store_id": professional_store_id,
    }


async def _create_service(client: AsyncClient, token: str, data: dict | None = None) -> str:
    res = await client.post(
        SERVICES_URL,
        json=data or VALID_SERVICE,
        headers={"Authorization": f"Bearer {token}"},
    )
    return res.json()["id"]


# ---------------------------------------------------------------------------
# POST /professional-stores/{id}/offerings
# ---------------------------------------------------------------------------


async def test_create_offering_success(client: AsyncClient):
    ctx = await _setup(client)
    service_id = await _create_service(client, ctx["prof_token"])

    response = await client.post(
        f"{PROF_STORES_BASE}/{ctx['professional_store_id']}/offerings",
        json={"service_id": service_id},
        headers={"Authorization": f"Bearer {ctx['prof_token']}"},
    )
    assert response.status_code == 201
    body = response.json()
    assert body["service_id"] == service_id
    assert body["is_enabled"] is True
    assert body["price_override"] is None
    assert body["duration_override"] is None
    assert body["service"]["name"] == VALID_SERVICE["name"]


async def test_create_offering_with_overrides(client: AsyncClient):
    ctx = await _setup(client)
    service_id = await _create_service(client, ctx["prof_token"])

    response = await client.post(
        f"{PROF_STORES_BASE}/{ctx['professional_store_id']}/offerings",
        json={"service_id": service_id, "price_override": "95.00", "duration_override": 75},
        headers={"Authorization": f"Bearer {ctx['prof_token']}"},
    )
    assert response.status_code == 201
    body = response.json()
    assert body["price_override"] == "95.00"
    assert body["duration_override"] == 75
    assert body["effective_price"] == "95.00"
    assert body["effective_duration_minutes"] == 75


async def test_create_offering_effective_fields_use_service_defaults_when_no_override(client: AsyncClient):
    ctx = await _setup(client)
    service_id = await _create_service(client, ctx["prof_token"])

    response = await client.post(
        f"{PROF_STORES_BASE}/{ctx['professional_store_id']}/offerings",
        json={"service_id": service_id},
        headers={"Authorization": f"Bearer {ctx['prof_token']}"},
    )
    assert response.status_code == 201
    body = response.json()
    assert body["effective_price"] == VALID_SERVICE["default_price"]
    assert body["effective_duration_minutes"] == VALID_SERVICE["default_duration_minutes"]


async def test_create_offering_invalid_duration_override(client: AsyncClient):
    ctx = await _setup(client)
    service_id = await _create_service(client, ctx["prof_token"])

    response = await client.post(
        f"{PROF_STORES_BASE}/{ctx['professional_store_id']}/offerings",
        json={"service_id": service_id, "duration_override": 10},
        headers={"Authorization": f"Bearer {ctx['prof_token']}"},
    )
    assert response.status_code == 422


async def test_create_offering_negative_price_override(client: AsyncClient):
    ctx = await _setup(client)
    service_id = await _create_service(client, ctx["prof_token"])

    response = await client.post(
        f"{PROF_STORES_BASE}/{ctx['professional_store_id']}/offerings",
        json={"service_id": service_id, "price_override": "-5.00"},
        headers={"Authorization": f"Bearer {ctx['prof_token']}"},
    )
    assert response.status_code == 422


async def test_create_offering_store_admin_can_manage(client: AsyncClient):
    ctx = await _setup(client)
    service_id = await _create_service(client, ctx["prof_token"])

    # The store admin (not the professional) should also be able to add an offering
    response = await client.post(
        f"{PROF_STORES_BASE}/{ctx['professional_store_id']}/offerings",
        json={"service_id": service_id},
        headers={"Authorization": f"Bearer {ctx['admin_token']}"},
    )
    assert response.status_code == 201


async def test_create_offering_service_from_other_professional_fails(client: AsyncClient):
    ctx = await _setup(client)

    # Create second professional
    admin_b = await _register_and_login(client, OTHER_ADMIN)
    store_b_res = await client.post(
        STORES_URL, json={"name": "Loja B"}, headers={"Authorization": f"Bearer {admin_b}"}
    )
    store_b_id = store_b_res.json()["id"]
    invite_b = await client.post(
        f"{STORES_URL}/{store_b_id}/invites",
        headers={"Authorization": f"Bearer {admin_b}"},
    )
    anon_b = {**ANON_PROF, "email": "prof_b@test.com"}
    prof_b_token = (
        await client.post(f"{INVITES_URL}/{invite_b.json()['token']}/accept", json=anon_b)
    ).json()["access_token"]

    # service_b belongs to prof_b
    service_b_id = await _create_service(client, prof_b_token)

    # prof_a tries to add service_b to their link
    response = await client.post(
        f"{PROF_STORES_BASE}/{ctx['professional_store_id']}/offerings",
        json={"service_id": service_b_id},
        headers={"Authorization": f"Bearer {ctx['prof_token']}"},
    )
    assert response.status_code == 422


async def test_create_offering_duplicate_conflict(client: AsyncClient):
    ctx = await _setup(client)
    service_id = await _create_service(client, ctx["prof_token"])

    await client.post(
        f"{PROF_STORES_BASE}/{ctx['professional_store_id']}/offerings",
        json={"service_id": service_id},
        headers={"Authorization": f"Bearer {ctx['prof_token']}"},
    )

    response = await client.post(
        f"{PROF_STORES_BASE}/{ctx['professional_store_id']}/offerings",
        json={"service_id": service_id},
        headers={"Authorization": f"Bearer {ctx['prof_token']}"},
    )
    assert response.status_code == 409


async def test_create_offering_unauthorized(client: AsyncClient):
    ctx = await _setup(client)
    service_id = await _create_service(client, ctx["prof_token"])

    response = await client.post(
        f"{PROF_STORES_BASE}/{ctx['professional_store_id']}/offerings",
        json={"service_id": service_id},
    )
    assert response.status_code == 401


# ---------------------------------------------------------------------------
# GET /professional-stores/{id}/offerings
# ---------------------------------------------------------------------------


async def test_list_offerings_disabled_still_appears(client: AsyncClient):
    ctx = await _setup(client)
    service_id = await _create_service(client, ctx["prof_token"])

    offering_res = await client.post(
        f"{PROF_STORES_BASE}/{ctx['professional_store_id']}/offerings",
        json={"service_id": service_id},
        headers={"Authorization": f"Bearer {ctx['prof_token']}"},
    )
    offering_id = offering_res.json()["id"]

    # Disable the offering
    await client.patch(
        f"{PROF_STORES_BASE}/{ctx['professional_store_id']}/offerings/{offering_id}",
        json={"is_enabled": False},
        headers={"Authorization": f"Bearer {ctx['prof_token']}"},
    )

    response = await client.get(
        f"{PROF_STORES_BASE}/{ctx['professional_store_id']}/offerings"
    )
    assert response.status_code == 200
    body = response.json()
    assert len(body) == 1
    assert body[0]["id"] == offering_id
    assert body[0]["is_enabled"] is False


async def test_toggle_off_then_on_no_conflict(client: AsyncClient):
    ctx = await _setup(client)
    service_id = await _create_service(client, ctx["prof_token"])

    offering_res = await client.post(
        f"{PROF_STORES_BASE}/{ctx['professional_store_id']}/offerings",
        json={"service_id": service_id},
        headers={"Authorization": f"Bearer {ctx['prof_token']}"},
    )
    offering_id = offering_res.json()["id"]

    # Disable
    await client.patch(
        f"{PROF_STORES_BASE}/{ctx['professional_store_id']}/offerings/{offering_id}",
        json={"is_enabled": False},
        headers={"Authorization": f"Bearer {ctx['prof_token']}"},
    )

    # Re-enable — should succeed with 200, not 409
    response = await client.patch(
        f"{PROF_STORES_BASE}/{ctx['professional_store_id']}/offerings/{offering_id}",
        json={"is_enabled": True},
        headers={"Authorization": f"Bearer {ctx['prof_token']}"},
    )
    assert response.status_code == 200
    assert response.json()["is_enabled"] is True


async def test_list_offerings_includes_service_data(client: AsyncClient):
    ctx = await _setup(client)
    service_id = await _create_service(client, ctx["prof_token"])

    await client.post(
        f"{PROF_STORES_BASE}/{ctx['professional_store_id']}/offerings",
        json={"service_id": service_id},
        headers={"Authorization": f"Bearer {ctx['prof_token']}"},
    )

    response = await client.get(
        f"{PROF_STORES_BASE}/{ctx['professional_store_id']}/offerings"
    )
    assert response.status_code == 200
    body = response.json()
    assert len(body) == 1
    assert body[0]["service"]["name"] == VALID_SERVICE["name"]
    assert body[0]["service"]["default_price"] == "80.00"


# ---------------------------------------------------------------------------
# PATCH /professional-stores/{id}/offerings/{offering_id}
# ---------------------------------------------------------------------------


async def test_update_offering_overrides(client: AsyncClient):
    ctx = await _setup(client)
    service_id = await _create_service(client, ctx["prof_token"])

    offering_res = await client.post(
        f"{PROF_STORES_BASE}/{ctx['professional_store_id']}/offerings",
        json={"service_id": service_id},
        headers={"Authorization": f"Bearer {ctx['prof_token']}"},
    )
    offering_id = offering_res.json()["id"]

    response = await client.patch(
        f"{PROF_STORES_BASE}/{ctx['professional_store_id']}/offerings/{offering_id}",
        json={"price_override": "100.00", "duration_override": 90},
        headers={"Authorization": f"Bearer {ctx['prof_token']}"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["price_override"] == "100.00"
    assert body["duration_override"] == 90
    assert body["effective_price"] == "100.00"
    assert body["effective_duration_minutes"] == 90


async def test_update_offering_clear_override_falls_back_to_service_default(client: AsyncClient):
    ctx = await _setup(client)
    service_id = await _create_service(client, ctx["prof_token"])

    offering_res = await client.post(
        f"{PROF_STORES_BASE}/{ctx['professional_store_id']}/offerings",
        json={"service_id": service_id, "price_override": "100.00"},
        headers={"Authorization": f"Bearer {ctx['prof_token']}"},
    )
    offering_id = offering_res.json()["id"]

    # Send explicit null to clear the override
    response = await client.patch(
        f"{PROF_STORES_BASE}/{ctx['professional_store_id']}/offerings/{offering_id}",
        json={"price_override": None},
        headers={"Authorization": f"Bearer {ctx['prof_token']}"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["price_override"] is None
    assert body["effective_price"] == VALID_SERVICE["default_price"]


async def test_update_offering_invalid_duration_override(client: AsyncClient):
    ctx = await _setup(client)
    service_id = await _create_service(client, ctx["prof_token"])

    offering_res = await client.post(
        f"{PROF_STORES_BASE}/{ctx['professional_store_id']}/offerings",
        json={"service_id": service_id},
        headers={"Authorization": f"Bearer {ctx['prof_token']}"},
    )
    offering_id = offering_res.json()["id"]

    response = await client.patch(
        f"{PROF_STORES_BASE}/{ctx['professional_store_id']}/offerings/{offering_id}",
        json={"duration_override": 5},
        headers={"Authorization": f"Bearer {ctx['prof_token']}"},
    )
    assert response.status_code == 422


async def test_update_offering_inactive_service_hides_from_listing(client: AsyncClient):
    ctx = await _setup(client)
    service_id = await _create_service(client, ctx["prof_token"])

    await client.post(
        f"{PROF_STORES_BASE}/{ctx['professional_store_id']}/offerings",
        json={"service_id": service_id},
        headers={"Authorization": f"Bearer {ctx['prof_token']}"},
    )

    # Deactivate the canonical service
    await client.patch(
        f"/api/v1/services/{service_id}",
        json={"is_active": False},
        headers={"Authorization": f"Bearer {ctx['prof_token']}"},
    )

    list_res = await client.get(
        f"{PROF_STORES_BASE}/{ctx['professional_store_id']}/offerings"
    )
    assert list_res.json() == []


async def test_update_offering_foreign_professional_forbidden(client: AsyncClient):
    ctx = await _setup(client)
    service_id = await _create_service(client, ctx["prof_token"])

    offering_res = await client.post(
        f"{PROF_STORES_BASE}/{ctx['professional_store_id']}/offerings",
        json={"service_id": service_id},
        headers={"Authorization": f"Bearer {ctx['prof_token']}"},
    )
    offering_id = offering_res.json()["id"]

    # Another professional
    admin_b = await _register_and_login(client, OTHER_ADMIN)
    store_b_res = await client.post(
        STORES_URL, json={"name": "Loja B"}, headers={"Authorization": f"Bearer {admin_b}"}
    )
    invite_b = await client.post(
        f"{STORES_URL}/{store_b_res.json()['id']}/invites",
        headers={"Authorization": f"Bearer {admin_b}"},
    )
    anon_b = {**ANON_PROF, "email": "prof_b@test.com"}
    prof_b_token = (
        await client.post(f"{INVITES_URL}/{invite_b.json()['token']}/accept", json=anon_b)
    ).json()["access_token"]

    response = await client.patch(
        f"{PROF_STORES_BASE}/{ctx['professional_store_id']}/offerings/{offering_id}",
        json={"price_override": "50.00"},
        headers={"Authorization": f"Bearer {prof_b_token}"},
    )
    assert response.status_code == 403


# ---------------------------------------------------------------------------
# DELETE /professional-stores/{id}/offerings/{offering_id}
# ---------------------------------------------------------------------------


async def test_delete_offering_success(client: AsyncClient):
    ctx = await _setup(client)
    service_id = await _create_service(client, ctx["prof_token"])

    offering_res = await client.post(
        f"{PROF_STORES_BASE}/{ctx['professional_store_id']}/offerings",
        json={"service_id": service_id},
        headers={"Authorization": f"Bearer {ctx['prof_token']}"},
    )
    offering_id = offering_res.json()["id"]

    response = await client.delete(
        f"{PROF_STORES_BASE}/{ctx['professional_store_id']}/offerings/{offering_id}",
        headers={"Authorization": f"Bearer {ctx['prof_token']}"},
    )
    assert response.status_code == 204

    list_res = await client.get(
        f"{PROF_STORES_BASE}/{ctx['professional_store_id']}/offerings"
    )
    assert list_res.json() == []


async def test_delete_service_cascades_to_offerings(client: AsyncClient):
    ctx = await _setup(client)
    service_id = await _create_service(client, ctx["prof_token"])

    await client.post(
        f"{PROF_STORES_BASE}/{ctx['professional_store_id']}/offerings",
        json={"service_id": service_id},
        headers={"Authorization": f"Bearer {ctx['prof_token']}"},
    )

    # Delete the canonical service
    await client.delete(
        f"{SERVICES_URL}/{service_id}",
        headers={"Authorization": f"Bearer {ctx['prof_token']}"},
    )

    # Offering should no longer appear (service is inactive/deleted)
    list_res = await client.get(
        f"{PROF_STORES_BASE}/{ctx['professional_store_id']}/offerings"
    )
    assert list_res.json() == []
