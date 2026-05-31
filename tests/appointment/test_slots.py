from datetime import date, timedelta

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

ANON_PROF = {
    "name": "Profissional",
    "email": "prof@test.com",
    "password": "senha123",
    "accepted_terms": True,
}

VALID_STORE = {"name": "Salão da Ana"}
VALID_SERVICE = {
    "name": "Corte",
    "default_price": "50.00",
    "default_duration_minutes": 60,
}


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

    service_res = await client.post(
        SERVICES_URL,
        json=VALID_SERVICE,
        headers={"Authorization": f"Bearer {prof_token}"},
    )
    service_id = service_res.json()["id"]

    offering_res = await client.post(
        f"{PROF_STORES_BASE}/{professional_store_id}/offerings",
        json={"service_id": service_id},
        headers={"Authorization": f"Bearer {prof_token}"},
    )
    offering_id = offering_res.json()["id"]

    return {
        "admin_token": admin_token,
        "prof_token": prof_token,
        "store_id": store_id,
        "professional_store_id": professional_store_id,
        "offering_id": offering_id,
    }


def _next_monday() -> str:
    """Returns the next Monday from today as YYYY-MM-DD (weekday=0)."""
    today = date.today()
    days_ahead = (7 - today.weekday()) % 7 or 7
    return (today + timedelta(days=days_ahead)).isoformat()


# ---------------------------------------------------------------------------
# GET /professional-stores/{id}/available-slots
# ---------------------------------------------------------------------------


async def test_slots_sem_horario_retorna_lista_vazia(client: AsyncClient):
    ctx = await _setup(client)
    ps_id = ctx["professional_store_id"]
    monday = _next_monday()

    res = await client.get(
        f"{PROF_STORES_BASE}/{ps_id}/available-slots",
        params={"offering_id": ctx["offering_id"], "date": monday},
    )
    assert res.status_code == 200
    assert res.json() == []


async def test_slots_multi_blocos_nao_atravessam_pausa(client: AsyncClient):
    """
    Two blocks on Monday: 08:00-10:00 and 13:00-14:00.
    Service duration = 60min, grid = 10min.
    Expected slots: 08:00, 08:10, ..., 09:00 (block 1) + 13:00 (block 2).
    No slot should span 10:00-13:00 pause.
    """
    ctx = await _setup(client)
    ps_id = ctx["professional_store_id"]
    headers = {"Authorization": f"Bearer {ctx['prof_token']}"}
    monday = _next_monday()

    await client.post(
        f"{PROF_STORES_BASE}/{ps_id}/schedules",
        json={"weekday": 0, "start_time": "08:00:00", "end_time": "10:00:00"},
        headers=headers,
    )
    await client.post(
        f"{PROF_STORES_BASE}/{ps_id}/schedules",
        json={"weekday": 0, "start_time": "13:00:00", "end_time": "14:00:00"},
        headers=headers,
    )

    res = await client.get(
        f"{PROF_STORES_BASE}/{ps_id}/available-slots",
        params={"offering_id": ctx["offering_id"], "date": monday},
    )
    assert res.status_code == 200
    slots = res.json()

    starts = [s["start"][11:16] for s in slots]  # extract HH:MM from ISO datetime

    # All slots must start within block 1 (08:00-09:00) or block 2 (13:00)
    for start in starts:
        in_block_1 = "08:00" <= start <= "09:00"
        in_block_2 = start == "13:00"
        assert in_block_1 or in_block_2, f"Slot {start} crosses the pause or is outside blocks"

    # Must have no slot starting in the pause (10:00-13:00)
    pause_slots = [s for s in starts if "10:00" <= s < "13:00"]
    assert pause_slots == [], f"Slots found in pause window: {pause_slots}"


async def test_slots_grid_10min(client: AsyncClient):
    """
    Block 08:00-09:00, service 30min.
    Grid = 10min → slots at 08:00, 08:10, 08:20, 08:30 (08:30+30=09:00 fits).
    NOT at 08:40 (08:40+30=09:10 > 09:00).
    """
    ctx = await _setup(client)
    ps_id = ctx["professional_store_id"]
    headers = {"Authorization": f"Bearer {ctx['prof_token']}"}
    monday = _next_monday()

    # Create a 30-min offering by using duration_override
    service_res = await client.post(
        SERVICES_URL,
        json={"name": "Sobrancelha", "default_price": "30.00", "default_duration_minutes": 30},
        headers=headers,
    )
    offering_res = await client.post(
        f"{PROF_STORES_BASE}/{ps_id}/offerings",
        json={"service_id": service_res.json()["id"]},
        headers=headers,
    )
    offering_id = offering_res.json()["id"]

    await client.post(
        f"{PROF_STORES_BASE}/{ps_id}/schedules",
        json={"weekday": 0, "start_time": "08:00:00", "end_time": "09:00:00"},
        headers=headers,
    )

    res = await client.get(
        f"{PROF_STORES_BASE}/{ps_id}/available-slots",
        params={"offering_id": offering_id, "date": monday},
    )
    assert res.status_code == 200
    starts = [s["start"][11:16] for s in res.json()]

    assert "08:00" in starts
    assert "08:10" in starts
    assert "08:20" in starts
    assert "08:30" in starts
    assert "08:40" not in starts  # 08:40 + 30min = 09:10 exceeds block end
