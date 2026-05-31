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

BLOCK_MORNING = {"weekday": 1, "start_time": "08:00:00", "end_time": "12:00:00"}
BLOCK_AFTERNOON = {"weekday": 1, "start_time": "13:00:00", "end_time": "17:00:00"}
BLOCK_OVERLAP = {"weekday": 1, "start_time": "11:00:00", "end_time": "14:00:00"}


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
# POST /professional-stores/{id}/schedules
# ---------------------------------------------------------------------------


async def test_criar_dois_blocos_mesmo_dia_success(client: AsyncClient):
    ctx = await _setup(client)
    ps_id = ctx["professional_store_id"]
    headers = {"Authorization": f"Bearer {ctx['prof_token']}"}

    r1 = await client.post(f"{PROF_STORES_BASE}/{ps_id}/schedules", json=BLOCK_MORNING, headers=headers)
    assert r1.status_code == 201
    assert r1.json()["start_time"] == BLOCK_MORNING["start_time"]

    r2 = await client.post(f"{PROF_STORES_BASE}/{ps_id}/schedules", json=BLOCK_AFTERNOON, headers=headers)
    assert r2.status_code == 201
    assert r2.json()["start_time"] == BLOCK_AFTERNOON["start_time"]

    list_res = await client.get(f"{PROF_STORES_BASE}/{ps_id}/schedules", headers=headers)
    assert list_res.status_code == 200
    assert len(list_res.json()) == 2


async def test_criar_bloco_sobreposto_retorna_409(client: AsyncClient):
    ctx = await _setup(client)
    ps_id = ctx["professional_store_id"]
    headers = {"Authorization": f"Bearer {ctx['prof_token']}"}

    await client.post(f"{PROF_STORES_BASE}/{ps_id}/schedules", json=BLOCK_MORNING, headers=headers)

    r = await client.post(f"{PROF_STORES_BASE}/{ps_id}/schedules", json=BLOCK_OVERLAP, headers=headers)
    assert r.status_code == 409


async def test_atualizar_bloco_para_sobrepor_retorna_409(client: AsyncClient):
    ctx = await _setup(client)
    ps_id = ctx["professional_store_id"]
    headers = {"Authorization": f"Bearer {ctx['prof_token']}"}

    r1 = await client.post(f"{PROF_STORES_BASE}/{ps_id}/schedules", json=BLOCK_MORNING, headers=headers)
    r2 = await client.post(f"{PROF_STORES_BASE}/{ps_id}/schedules", json=BLOCK_AFTERNOON, headers=headers)
    schedule_id = r2.json()["id"]

    # Try to extend afternoon block back into morning block
    r = await client.patch(
        f"{PROF_STORES_BASE}/{ps_id}/schedules/{schedule_id}",
        json={"start_time": "11:00:00"},
        headers=headers,
    )
    assert r.status_code == 409
