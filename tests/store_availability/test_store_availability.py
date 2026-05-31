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

VALID_STORE = {"name": "Salão da Ana"}

BASE_SCHEDULE = {"weekday": 1, "start_time": "08:00:00", "end_time": "12:00:00"}
OVERRIDE_BLOCK = {"weekday": 1, "start_time": "09:00:00", "end_time": "11:00:00"}
OVERLAP_BLOCK = {"weekday": 1, "start_time": "10:00:00", "end_time": "13:00:00"}


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
# POST /professional-stores/{id}/availability
# ---------------------------------------------------------------------------


async def test_create_override_success(client: AsyncClient):
    ctx = await _setup(client)
    ps_id = ctx["professional_store_id"]
    headers = {"Authorization": f"Bearer {ctx['prof_token']}"}

    res = await client.post(
        f"{PROF_STORES_BASE}/{ps_id}/availability", json=OVERRIDE_BLOCK, headers=headers
    )
    assert res.status_code == 201
    body = res.json()
    assert body["weekday"] == OVERRIDE_BLOCK["weekday"]
    assert body["start_time"] == OVERRIDE_BLOCK["start_time"]
    assert body["end_time"] == OVERRIDE_BLOCK["end_time"]
    assert body["is_active"] is True
    assert body["professional_store_id"] == ps_id


async def test_create_override_overlap_rejected(client: AsyncClient):
    ctx = await _setup(client)
    ps_id = ctx["professional_store_id"]
    headers = {"Authorization": f"Bearer {ctx['prof_token']}"}

    await client.post(
        f"{PROF_STORES_BASE}/{ps_id}/availability", json=OVERRIDE_BLOCK, headers=headers
    )
    res = await client.post(
        f"{PROF_STORES_BASE}/{ps_id}/availability", json=OVERLAP_BLOCK, headers=headers
    )
    assert res.status_code == 409


async def test_override_does_not_affect_base_schedule(client: AsyncClient):
    """Creating an override must not modify WorkSchedule records."""
    ctx = await _setup(client)
    ps_id = ctx["professional_store_id"]
    headers = {"Authorization": f"Bearer {ctx['prof_token']}"}

    # Create a base schedule block
    await client.post(
        f"{PROF_STORES_BASE}/{ps_id}/schedules", json=BASE_SCHEDULE, headers=headers
    )

    # Create an override on the same day
    await client.post(
        f"{PROF_STORES_BASE}/{ps_id}/availability", json=OVERRIDE_BLOCK, headers=headers
    )

    # Base schedule must still be intact
    schedules_res = await client.get(f"{PROF_STORES_BASE}/{ps_id}/schedules")
    schedules = schedules_res.json()
    assert len(schedules) == 1
    assert schedules[0]["start_time"] == BASE_SCHEDULE["start_time"]
    assert schedules[0]["end_time"] == BASE_SCHEDULE["end_time"]


async def test_list_store_availability(client: AsyncClient):
    ctx = await _setup(client)
    ps_id = ctx["professional_store_id"]
    headers = {"Authorization": f"Bearer {ctx['prof_token']}"}

    await client.post(
        f"{PROF_STORES_BASE}/{ps_id}/availability", json=OVERRIDE_BLOCK, headers=headers
    )

    res = await client.get(f"{PROF_STORES_BASE}/{ps_id}/availability")
    assert res.status_code == 200
    assert len(res.json()) == 1


async def test_delete_override_restores_base_fallback(client: AsyncClient):
    """After deleting override, the list returns empty (base used as fallback at slot level)."""
    ctx = await _setup(client)
    ps_id = ctx["professional_store_id"]
    headers = {"Authorization": f"Bearer {ctx['prof_token']}"}

    create_res = await client.post(
        f"{PROF_STORES_BASE}/{ps_id}/availability", json=OVERRIDE_BLOCK, headers=headers
    )
    availability_id = create_res.json()["id"]

    del_res = await client.delete(
        f"{PROF_STORES_BASE}/{ps_id}/availability/{availability_id}", headers=headers
    )
    assert del_res.status_code == 204

    list_res = await client.get(f"{PROF_STORES_BASE}/{ps_id}/availability")
    assert list_res.json() == []
