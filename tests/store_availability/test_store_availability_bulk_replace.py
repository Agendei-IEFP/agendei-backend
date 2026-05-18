from httpx import AsyncClient

REGISTER_URL = "/api/v1/auth/register"
LOGIN_URL = "/api/v1/auth/login"
STORES_URL = "/api/v1/stores"
INVITES_URL = "/api/v1/invites"
PROF_STORES_BASE = "/api/v1/professional-stores"

ADMIN_USER = {
    "name": "Admin Owner",
    "email": "admin@test.com",
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

ADMIN_USER_2 = {
    "name": "Admin 2",
    "email": "admin2@test.com",
    "password": "password123",
    "role": "store_admin",
    "accepted_terms": True,
}

ANON_PROF_2 = {
    "name": "Prof 2",
    "email": "prof2@test.com",
    "password": "senha123",
    "accepted_terms": True,
}

VALID_STORE = {"name": "Salão da Ana"}

THREE_BLOCKS = [
    {"weekday": 0, "start_time": "09:00:00", "end_time": "12:00:00"},
    {"weekday": 0, "start_time": "13:00:00", "end_time": "18:00:00"},
    {"weekday": 1, "start_time": "09:00:00", "end_time": "17:00:00"},
]

TWO_BLOCKS = [
    {"weekday": 0, "start_time": "09:00:00", "end_time": "12:00:00"},
    {"weekday": 2, "start_time": "10:00:00", "end_time": "16:00:00"},
]

OVERLAPPING_PAYLOAD = [
    {"weekday": 0, "start_time": "09:00:00", "end_time": "13:00:00"},
    {"weekday": 0, "start_time": "12:00:00", "end_time": "17:00:00"},
]


async def _register_and_login(client: AsyncClient, user: dict) -> str:
    await client.post(REGISTER_URL, json=user)
    res = await client.post(LOGIN_URL, json={"email": user["email"], "password": user["password"]})
    return res.json()["access_token"]


async def _setup(client: AsyncClient) -> dict:
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


# ---------------------------------------------------------------------------
# PUT /professional-stores/{id}/availability
# ---------------------------------------------------------------------------


async def test_bulk_replace_availability_empty_to_three_blocks(client: AsyncClient):
    ctx = await _setup(client)
    ps_id = ctx["professional_store_id"]
    headers = {"Authorization": f"Bearer {ctx['prof_token']}"}

    res = await client.put(
        f"{PROF_STORES_BASE}/{ps_id}/availability",
        json={"blocks": THREE_BLOCKS},
        headers=headers,
    )
    assert res.status_code == 200
    assert len(res.json()) == 3

    list_res = await client.get(f"{PROF_STORES_BASE}/{ps_id}/availability")
    assert len(list_res.json()) == 3


async def test_bulk_replace_availability_removes_old_blocks(client: AsyncClient):
    ctx = await _setup(client)
    ps_id = ctx["professional_store_id"]
    headers = {"Authorization": f"Bearer {ctx['prof_token']}"}

    await client.put(
        f"{PROF_STORES_BASE}/{ps_id}/availability",
        json={"blocks": THREE_BLOCKS},
        headers=headers,
    )

    res = await client.put(
        f"{PROF_STORES_BASE}/{ps_id}/availability",
        json={"blocks": TWO_BLOCKS},
        headers=headers,
    )
    assert res.status_code == 200

    list_res = await client.get(f"{PROF_STORES_BASE}/{ps_id}/availability")
    assert len(list_res.json()) == 2


async def test_bulk_replace_availability_empty_blocks_clears_all(client: AsyncClient):
    ctx = await _setup(client)
    ps_id = ctx["professional_store_id"]
    headers = {"Authorization": f"Bearer {ctx['prof_token']}"}

    await client.put(
        f"{PROF_STORES_BASE}/{ps_id}/availability",
        json={"blocks": THREE_BLOCKS},
        headers=headers,
    )

    res = await client.put(
        f"{PROF_STORES_BASE}/{ps_id}/availability",
        json={"blocks": []},
        headers=headers,
    )
    assert res.status_code == 200
    assert res.json() == []

    list_res = await client.get(f"{PROF_STORES_BASE}/{ps_id}/availability")
    assert list_res.json() == []


async def test_bulk_replace_availability_overlapping_payload_rejected(client: AsyncClient):
    ctx = await _setup(client)
    ps_id = ctx["professional_store_id"]
    headers = {"Authorization": f"Bearer {ctx['prof_token']}"}

    res = await client.put(
        f"{PROF_STORES_BASE}/{ps_id}/availability",
        json={"blocks": OVERLAPPING_PAYLOAD},
        headers=headers,
    )
    assert res.status_code == 409

    list_res = await client.get(f"{PROF_STORES_BASE}/{ps_id}/availability")
    assert list_res.json() == []


async def test_bulk_replace_availability_unauthenticated(client: AsyncClient):
    ctx = await _setup(client)
    ps_id = ctx["professional_store_id"]

    res = await client.put(
        f"{PROF_STORES_BASE}/{ps_id}/availability",
        json={"blocks": THREE_BLOCKS},
    )
    assert res.status_code == 401


async def test_bulk_replace_availability_wrong_owner_forbidden(client: AsyncClient):
    ctx = await _setup(client)
    ps_id = ctx["professional_store_id"]

    admin2_token = await _register_and_login(client, ADMIN_USER_2)
    store2_res = await client.post(
        STORES_URL, json={"name": "Outro Salão"}, headers={"Authorization": f"Bearer {admin2_token}"}
    )
    store2_id = store2_res.json()["id"]
    invite2_res = await client.post(
        f"{STORES_URL}/{store2_id}/invites",
        headers={"Authorization": f"Bearer {admin2_token}"},
    )
    accept2_res = await client.post(
        f"{INVITES_URL}/{invite2_res.json()['token']}/accept", json=ANON_PROF_2
    )
    prof2_token = accept2_res.json()["access_token"]

    res = await client.put(
        f"{PROF_STORES_BASE}/{ps_id}/availability",
        json={"blocks": THREE_BLOCKS},
        headers={"Authorization": f"Bearer {prof2_token}"},
    )
    assert res.status_code == 403
