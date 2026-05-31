import pytest
from httpx import AsyncClient

BASE_URL = "/api/v1/stores"
ME_URL = "/api/v1/me"
REGISTER_URL = "/api/v1/auth/register"
LOGIN_URL = "/api/v1/auth/login"

ADMIN_USER = {
    "name": "Jessé Admin",
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

VALID_STORE = {"name": "Salão do Jessézin"}


async def _get_token(client: AsyncClient, user: dict) -> str:
    await client.post(REGISTER_URL, json=user)
    response = await client.post(
        LOGIN_URL, json={"email": user["email"], "password": user["password"]}
    )
    return response.json()["access_token"]


@pytest.fixture
async def admin_token(client: AsyncClient) -> str:
    return await _get_token(client, ADMIN_USER)


@pytest.fixture
async def other_admin_token(client: AsyncClient) -> str:
    return await _get_token(client, OTHER_ADMIN_USER)


@pytest.fixture
async def client_token(client: AsyncClient) -> str:
    return await _get_token(client, CLIENT_USER)


# ---------------------------------------------------------------------------
# GET /stores
# ---------------------------------------------------------------------------


async def test_list_stores_empty(client: AsyncClient):
    response = await client.get(BASE_URL)
    assert response.status_code == 200
    assert response.json() == []


async def test_list_stores_returns_active(client: AsyncClient, admin_token: str):
    await client.post(BASE_URL, json=VALID_STORE, headers={"Authorization": f"Bearer {admin_token}"})
    response = await client.get(BASE_URL)
    assert response.status_code == 200
    assert len(response.json()) == 1


async def test_list_stores_excludes_deleted(client: AsyncClient, admin_token: str):
    created = await client.post(BASE_URL, json=VALID_STORE, headers={"Authorization": f"Bearer {admin_token}"})
    store_id = created.json()["id"]
    await client.delete(f"{BASE_URL}/{store_id}", headers={"Authorization": f"Bearer {admin_token}"})
    response = await client.get(BASE_URL)
    assert response.status_code == 200
    assert response.json() == []


# ---------------------------------------------------------------------------
# GET /me/stores
# ---------------------------------------------------------------------------


async def test_list_my_stores_success(
    client: AsyncClient, admin_token: str, other_admin_token: str
):
    await client.post(BASE_URL, json=VALID_STORE, headers={"Authorization": f"Bearer {admin_token}"})
    await client.post(BASE_URL, json={"name": "Outro Salão"}, headers={"Authorization": f"Bearer {other_admin_token}"})
    response = await client.get(f"{ME_URL}/stores", headers={"Authorization": f"Bearer {admin_token}"})
    assert response.status_code == 200
    body = response.json()
    assert len(body) == 1
    assert body[0]["name"] == VALID_STORE["name"]


async def test_list_my_stores_empty(client: AsyncClient, admin_token: str):
    response = await client.get(f"{ME_URL}/stores", headers={"Authorization": f"Bearer {admin_token}"})
    assert response.status_code == 200
    assert response.json() == []


async def test_list_my_stores_no_token(client: AsyncClient):
    response = await client.get(f"{ME_URL}/stores")
    assert response.status_code == 401


async def test_list_my_stores_wrong_role(client: AsyncClient, client_token: str):
    response = await client.get(f"{ME_URL}/stores", headers={"Authorization": f"Bearer {client_token}"})
    assert response.status_code == 403


# ---------------------------------------------------------------------------
# GET /stores/{id}
# ---------------------------------------------------------------------------


async def test_get_store_success(client: AsyncClient, admin_token: str):
    created = await client.post(BASE_URL, json=VALID_STORE, headers={"Authorization": f"Bearer {admin_token}"})
    store_id = created.json()["id"]
    response = await client.get(f"{BASE_URL}/{store_id}")
    assert response.status_code == 200
    assert response.json()["id"] == store_id


async def test_get_store_not_found(client: AsyncClient):
    response = await client.get(f"{BASE_URL}/00000000000000000000000000")
    assert response.status_code == 404


async def test_get_deleted_store_returns_404(client: AsyncClient, admin_token: str):
    created = await client.post(BASE_URL, json=VALID_STORE, headers={"Authorization": f"Bearer {admin_token}"})
    store_id = created.json()["id"]
    await client.delete(f"{BASE_URL}/{store_id}", headers={"Authorization": f"Bearer {admin_token}"})
    response = await client.get(f"{BASE_URL}/{store_id}")
    assert response.status_code == 404


# ---------------------------------------------------------------------------
# POST /stores
# ---------------------------------------------------------------------------


async def test_create_store_success(client: AsyncClient, admin_token: str):
    response = await client.post(BASE_URL, json=VALID_STORE, headers={"Authorization": f"Bearer {admin_token}"})
    assert response.status_code == 201
    body = response.json()
    assert body["name"] == VALID_STORE["name"]
    assert "id" in body
    assert "deleted_at" not in body
    assert "password_hash" not in body


async def test_create_store_no_token(client: AsyncClient):
    response = await client.post(BASE_URL, json=VALID_STORE)
    assert response.status_code == 401


async def test_create_store_wrong_role(client: AsyncClient, client_token: str):
    response = await client.post(BASE_URL, json=VALID_STORE, headers={"Authorization": f"Bearer {client_token}"})
    assert response.status_code == 403


async def test_create_store_missing_name(client: AsyncClient, admin_token: str):
    response = await client.post(BASE_URL, json={}, headers={"Authorization": f"Bearer {admin_token}"})
    assert response.status_code == 422


# ---------------------------------------------------------------------------
# PATCH /stores/{id}
# ---------------------------------------------------------------------------


async def test_update_store_success(client: AsyncClient, admin_token: str):
    created = await client.post(BASE_URL, json=VALID_STORE, headers={"Authorization": f"Bearer {admin_token}"})
    store_id = created.json()["id"]
    response = await client.patch(
        f"{BASE_URL}/{store_id}",
        json={"name": "Novo Nome", "phone": "11999999999"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["name"] == "Novo Nome"
    assert body["phone"] == "11999999999"


async def test_update_store_partial(client: AsyncClient, admin_token: str):
    created = await client.post(
        BASE_URL,
        json={**VALID_STORE, "phone": "11111111111"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    store_id = created.json()["id"]
    response = await client.patch(
        f"{BASE_URL}/{store_id}",
        json={"name": "Novo Nome"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["name"] == "Novo Nome"
    assert body["phone"] == "11111111111"


async def test_update_store_not_found(client: AsyncClient, admin_token: str):
    response = await client.patch(
        f"{BASE_URL}/00000000000000000000000000",
        json={"name": "X"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 404


async def test_update_store_wrong_owner(client: AsyncClient, admin_token: str, other_admin_token: str):
    created = await client.post(BASE_URL, json=VALID_STORE, headers={"Authorization": f"Bearer {admin_token}"})
    store_id = created.json()["id"]
    response = await client.patch(
        f"{BASE_URL}/{store_id}",
        json={"name": "Invasão"},
        headers={"Authorization": f"Bearer {other_admin_token}"},
    )
    assert response.status_code == 403


async def test_update_store_no_token(client: AsyncClient, admin_token: str):
    created = await client.post(BASE_URL, json=VALID_STORE, headers={"Authorization": f"Bearer {admin_token}"})
    store_id = created.json()["id"]
    response = await client.patch(f"{BASE_URL}/{store_id}", json={"name": "X"})
    assert response.status_code == 401


# ---------------------------------------------------------------------------
# DELETE /stores/{id}
# ---------------------------------------------------------------------------


async def test_delete_store_success(client: AsyncClient, admin_token: str):
    created = await client.post(BASE_URL, json=VALID_STORE, headers={"Authorization": f"Bearer {admin_token}"})
    store_id = created.json()["id"]
    response = await client.delete(f"{BASE_URL}/{store_id}", headers={"Authorization": f"Bearer {admin_token}"})
    assert response.status_code == 204


async def test_delete_store_then_404(client: AsyncClient, admin_token: str):
    created = await client.post(BASE_URL, json=VALID_STORE, headers={"Authorization": f"Bearer {admin_token}"})
    store_id = created.json()["id"]
    await client.delete(f"{BASE_URL}/{store_id}", headers={"Authorization": f"Bearer {admin_token}"})
    response = await client.get(f"{BASE_URL}/{store_id}")
    assert response.status_code == 404


async def test_delete_store_wrong_owner(client: AsyncClient, admin_token: str, other_admin_token: str):
    created = await client.post(BASE_URL, json=VALID_STORE, headers={"Authorization": f"Bearer {admin_token}"})
    store_id = created.json()["id"]
    response = await client.delete(f"{BASE_URL}/{store_id}", headers={"Authorization": f"Bearer {other_admin_token}"})
    assert response.status_code == 403


async def test_delete_store_no_token(client: AsyncClient, admin_token: str):
    created = await client.post(BASE_URL, json=VALID_STORE, headers={"Authorization": f"Bearer {admin_token}"})
    store_id = created.json()["id"]
    response = await client.delete(f"{BASE_URL}/{store_id}")
    assert response.status_code == 401


# ---------------------------------------------------------------------------
# GET /stores?store_type=
# ---------------------------------------------------------------------------


async def test_list_stores_filter_by_type(client: AsyncClient, admin_token: str):
    await client.post(
        BASE_URL,
        json={**VALID_STORE, "store_type": "barbershop"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    await client.post(
        BASE_URL,
        json={"name": "Salão de Cabelo", "store_type": "hair_salon"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )

    response = await client.get(f"{BASE_URL}?store_type=barbershop")
    assert response.status_code == 200
    body = response.json()
    assert len(body) == 1
    assert body[0]["store_type"] == "barbershop"


async def test_list_stores_no_filter_returns_all(client: AsyncClient, admin_token: str):
    await client.post(
        BASE_URL,
        json={**VALID_STORE, "store_type": "barbershop"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    await client.post(
        BASE_URL,
        json={"name": "Salão de Cabelo", "store_type": "hair_salon"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )

    response = await client.get(BASE_URL)
    assert response.status_code == 200
    assert len(response.json()) == 2


async def test_list_stores_filter_returns_empty_when_no_match(
    client: AsyncClient, admin_token: str
):
    await client.post(
        BASE_URL,
        json={**VALID_STORE, "store_type": "barbershop"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )

    response = await client.get(f"{BASE_URL}?store_type=nails")
    assert response.status_code == 200
    assert response.json() == []


async def test_list_stores_invalid_type_returns_422(client: AsyncClient):
    response = await client.get(f"{BASE_URL}?store_type=invalid_value")
    assert response.status_code == 422


# ---------------------------------------------------------------------------
# GET /stores/{store_id}/offerings
# ---------------------------------------------------------------------------

SERVICES_URL = "/api/v1/services"
PROF_STORES_URL = "/api/v1/professional-stores"

VALID_SERVICE = {
    "name": "Corte Masculino",
    "default_price": "50.00",
    "default_duration_minutes": 60,
}


async def _setup_store_with_offering(client: AsyncClient, admin_token: str) -> tuple[str, str]:
    """Creates a store, adds admin as professional, creates a service and an offering.
    Returns (store_id, professional_store_id).
    """
    store_resp = await client.post(
        BASE_URL,
        json=VALID_STORE,
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert store_resp.status_code == 201
    store_id = store_resp.json()["id"]

    ps_resp = await client.post(
        f"{BASE_URL}/{store_id}/professionals/me",
        json={},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert ps_resp.status_code == 201
    professional_store_id = ps_resp.json()["id"]

    service_resp = await client.post(
        SERVICES_URL,
        json=VALID_SERVICE,
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert service_resp.status_code == 201
    service_id = service_resp.json()["id"]

    offering_resp = await client.post(
        f"{PROF_STORES_URL}/{professional_store_id}/offerings",
        json={"service_id": service_id},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert offering_resp.status_code == 201

    return store_id, professional_store_id


async def test_list_store_offerings_happy_path(client: AsyncClient, admin_token: str):
    store_id, _ = await _setup_store_with_offering(client, admin_token)
    response = await client.get(f"{BASE_URL}/{store_id}/offerings")
    assert response.status_code == 200
    body = response.json()
    assert len(body) == 1
    assert body[0]["service_name"] == VALID_SERVICE["name"]
    assert body[0]["effective_price"] == VALID_SERVICE["default_price"]
    assert body[0]["effective_duration_minutes"] == VALID_SERVICE["default_duration_minutes"]


async def test_list_store_offerings_empty(client: AsyncClient, admin_token: str):
    store_resp = await client.post(
        BASE_URL,
        json=VALID_STORE,
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert store_resp.status_code == 201
    store_id = store_resp.json()["id"]

    response = await client.get(f"{BASE_URL}/{store_id}/offerings")
    assert response.status_code == 200
    assert response.json() == []


async def test_list_store_offerings_not_found(client: AsyncClient):
    response = await client.get(f"{BASE_URL}/00000000000000000000000000/offerings")
    assert response.status_code == 404


async def test_list_store_offerings_disabled_not_shown(client: AsyncClient, admin_token: str):
    store_id, professional_store_id = await _setup_store_with_offering(client, admin_token)

    # Get the offering id
    offerings_resp = await client.get(f"{PROF_STORES_URL}/{professional_store_id}/offerings")
    assert offerings_resp.status_code == 200
    offering_id = offerings_resp.json()[0]["id"]

    # Disable the offering
    patch_resp = await client.patch(
        f"{PROF_STORES_URL}/{professional_store_id}/offerings/{offering_id}",
        json={"is_enabled": False},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert patch_resp.status_code == 200

    response = await client.get(f"{BASE_URL}/{store_id}/offerings")
    assert response.status_code == 200
    assert response.json() == []
