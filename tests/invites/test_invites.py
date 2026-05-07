from datetime import datetime, timedelta, timezone

from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.professional_invite import ProfessionalInvite

STORES_URL = "/api/v1/stores"
INVITES_URL = "/api/v1/invites"
REGISTER_URL = "/api/v1/auth/register"
LOGIN_URL = "/api/v1/auth/login"

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
    "name": "Cliente Comum",
    "email": "cliente@example.com",
    "password": "password123",
    "role": "client",
    "accepted_terms": True,
}

PROFESSIONAL_USER = {
    "name": "Profissional Existente",
    "email": "prof@example.com",
    "password": "password123",
    "role": "store_admin",
    "accepted_terms": True,
}

VALID_STORE = {"name": "Salão da Ana"}

ANON_ACCEPT_BODY = {
    "name": "Nova Profissional",
    "email": "nova@example.com",
    "password": "senha123",
    "accepted_terms": True,
}


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


async def _create_invite(client: AsyncClient, token: str, store_id: str) -> str:
    response = await client.post(
        f"{STORES_URL}/{store_id}/invites",
        headers={"Authorization": f"Bearer {token}"},
    )
    return response.json()["token"]


# ---------------------------------------------------------------------------
# POST /stores/{store_id}/invites — create invite
# ---------------------------------------------------------------------------


async def test_create_invite_success(client: AsyncClient):
    token = await _get_token(client, ADMIN_USER)
    store_id = await _create_store(client, token)

    response = await client.post(
        f"{STORES_URL}/{store_id}/invites",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 201
    body = response.json()
    assert "token" in body
    assert "url" in body
    assert "expires_at" in body
    assert body["token"] in body["url"]


async def test_create_invite_not_owner(client: AsyncClient):
    admin_token = await _get_token(client, ADMIN_USER)
    other_token = await _get_token(client, OTHER_ADMIN_USER)
    store_id = await _create_store(client, admin_token)

    response = await client.post(
        f"{STORES_URL}/{store_id}/invites",
        headers={"Authorization": f"Bearer {other_token}"},
    )
    assert response.status_code == 403


async def test_create_invite_unauthenticated(client: AsyncClient):
    token = await _get_token(client, ADMIN_USER)
    store_id = await _create_store(client, token)

    response = await client.post(f"{STORES_URL}/{store_id}/invites")
    assert response.status_code == 401


async def test_create_invite_multiple_parallel(client: AsyncClient):
    token = await _get_token(client, ADMIN_USER)
    store_id = await _create_store(client, token)

    # Admin can generate multiple invites simultaneously
    token1 = await _create_invite(client, token, store_id)
    token2 = await _create_invite(client, token, store_id)
    assert token1 != token2


# ---------------------------------------------------------------------------
# GET /invites/{token} — get invite info
# ---------------------------------------------------------------------------


async def test_get_invite_success(client: AsyncClient):
    token = await _get_token(client, ADMIN_USER)
    store_id = await _create_store(client, token)
    invite_token = await _create_invite(client, token, store_id)

    response = await client.get(f"{INVITES_URL}/{invite_token}")
    assert response.status_code == 200
    body = response.json()
    assert body["store_id"] == store_id
    assert body["store_name"] == VALID_STORE["name"]
    assert "expires_at" in body


async def test_get_invite_not_found(client: AsyncClient):
    response = await client.get(f"{INVITES_URL}/invalid-token")
    assert response.status_code == 404


async def test_get_invite_expired(client: AsyncClient, db_session: AsyncSession):
    token = await _get_token(client, ADMIN_USER)
    store_id = await _create_store(client, token)
    invite_token = await _create_invite(client, token, store_id)

    # Manually expire the invite
    result = await db_session.execute(
        select(ProfessionalInvite).where(
            ProfessionalInvite.token == invite_token
        )
    )
    invite = result.scalar_one()
    invite.expires_at = datetime.now(timezone.utc) - timedelta(hours=1)
    await db_session.flush()

    response = await client.get(f"{INVITES_URL}/{invite_token}")
    assert response.status_code == 410


async def test_get_invite_already_used(client: AsyncClient, db_session: AsyncSession):
    token = await _get_token(client, ADMIN_USER)
    store_id = await _create_store(client, token)
    invite_token = await _create_invite(client, token, store_id)

    result = await db_session.execute(
        select(ProfessionalInvite).where(
            ProfessionalInvite.token == invite_token
        )
    )
    invite = result.scalar_one()
    invite.used_at = datetime.now(timezone.utc)
    await db_session.flush()

    response = await client.get(f"{INVITES_URL}/{invite_token}")
    assert response.status_code == 409


# ---------------------------------------------------------------------------
# POST /invites/{token}/accept — anonymous user creates new account
# ---------------------------------------------------------------------------


async def test_accept_invite_anonymous_success(client: AsyncClient):
    token = await _get_token(client, ADMIN_USER)
    store_id = await _create_store(client, token)
    invite_token = await _create_invite(client, token, store_id)

    response = await client.post(
        f"{INVITES_URL}/{invite_token}/accept",
        json=ANON_ACCEPT_BODY,
    )
    assert response.status_code == 200
    body = response.json()
    assert body["access_token"] is not None
    assert body["refresh_token"] is not None
    assert body["professional_store"]["store_id"] == store_id


async def test_accept_invite_anonymous_missing_fields(client: AsyncClient):
    token = await _get_token(client, ADMIN_USER)
    store_id = await _create_store(client, token)
    invite_token = await _create_invite(client, token, store_id)

    response = await client.post(
        f"{INVITES_URL}/{invite_token}/accept",
        json={},
    )
    assert response.status_code == 422


async def test_accept_invite_anonymous_terms_not_accepted(client: AsyncClient):
    token = await _get_token(client, ADMIN_USER)
    store_id = await _create_store(client, token)
    invite_token = await _create_invite(client, token, store_id)

    body = {**ANON_ACCEPT_BODY, "accepted_terms": False}
    response = await client.post(f"{INVITES_URL}/{invite_token}/accept", json=body)
    assert response.status_code == 422


async def test_accept_invite_anonymous_duplicate_email(client: AsyncClient):
    admin_token = await _get_token(client, ADMIN_USER)
    store_id = await _create_store(client, admin_token)

    # First invite
    invite_token1 = await _create_invite(client, admin_token, store_id)
    await client.post(f"{INVITES_URL}/{invite_token1}/accept", json=ANON_ACCEPT_BODY)

    # Second invite with same email
    invite_token2 = await _create_invite(client, admin_token, store_id)
    response = await client.post(
        f"{INVITES_URL}/{invite_token2}/accept",
        json=ANON_ACCEPT_BODY,
    )
    assert response.status_code == 409


# ---------------------------------------------------------------------------
# POST /invites/{token}/accept — client upgrades to professional
# ---------------------------------------------------------------------------


async def test_accept_invite_client_success(client: AsyncClient):
    admin_token = await _get_token(client, ADMIN_USER)
    client_token = await _get_token(client, CLIENT_USER)
    store_id = await _create_store(client, admin_token)
    invite_token = await _create_invite(client, admin_token, store_id)

    response = await client.post(
        f"{INVITES_URL}/{invite_token}/accept",
        json={},
        headers={"Authorization": f"Bearer {client_token}"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["access_token"] is None
    assert body["professional_store"]["store_id"] == store_id


# ---------------------------------------------------------------------------
# POST /invites/{token}/accept — professional adds another store
# ---------------------------------------------------------------------------


async def test_accept_invite_professional_success(client: AsyncClient):
    # Setup: admin creates two stores, prof accepts invite to first
    admin_token = await _get_token(client, ADMIN_USER)
    prof_token = await _get_token(client, PROFESSIONAL_USER)
    store1_id = await _create_store(client, admin_token)
    store2_id = await _create_store(client, prof_token)

    # Link prof_user to store1 via invite
    invite1 = await _create_invite(client, admin_token, store1_id)
    await client.post(
        f"{INVITES_URL}/{invite1}/accept",
        json={},
        headers={"Authorization": f"Bearer {prof_token}"},
    )

    # Now accept an invite for store2 (their own store)
    invite2 = await _create_invite(client, prof_token, store2_id)
    response = await client.post(
        f"{INVITES_URL}/{invite2}/accept",
        json={},
        headers={"Authorization": f"Bearer {prof_token}"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["professional_store"]["store_id"] == store2_id


# ---------------------------------------------------------------------------
# POST /invites/{token}/accept — invite already used / expired
# ---------------------------------------------------------------------------


async def test_accept_invite_already_used(client: AsyncClient):
    admin_token = await _get_token(client, ADMIN_USER)
    store_id = await _create_store(client, admin_token)
    invite_token = await _create_invite(client, admin_token, store_id)

    # First accept
    await client.post(f"{INVITES_URL}/{invite_token}/accept", json=ANON_ACCEPT_BODY)

    # Second accept with different email — invite is consumed
    second_body = {**ANON_ACCEPT_BODY, "email": "second@example.com"}
    response = await client.post(
        f"{INVITES_URL}/{invite_token}/accept", json=second_body
    )
    assert response.status_code == 409


async def test_accept_invite_expired(client: AsyncClient, db_session: AsyncSession):
    admin_token = await _get_token(client, ADMIN_USER)
    store_id = await _create_store(client, admin_token)
    invite_token = await _create_invite(client, admin_token, store_id)

    result = await db_session.execute(
        select(ProfessionalInvite).where(
            ProfessionalInvite.token == invite_token
        )
    )
    invite = result.scalar_one()
    invite.expires_at = datetime.now(timezone.utc) - timedelta(hours=1)
    await db_session.flush()

    response = await client.post(
        f"{INVITES_URL}/{invite_token}/accept", json=ANON_ACCEPT_BODY
    )
    assert response.status_code == 410


async def test_accept_invite_not_found(client: AsyncClient):
    response = await client.post(
        f"{INVITES_URL}/invalid-token/accept", json=ANON_ACCEPT_BODY
    )
    assert response.status_code == 404


async def test_accept_invite_duplicate_professional_store(client: AsyncClient):
    admin_token = await _get_token(client, ADMIN_USER)
    client_token = await _get_token(client, CLIENT_USER)
    store_id = await _create_store(client, admin_token)

    invite1 = await _create_invite(client, admin_token, store_id)
    await client.post(
        f"{INVITES_URL}/{invite1}/accept",
        json={},
        headers={"Authorization": f"Bearer {client_token}"},
    )

    invite2 = await _create_invite(client, admin_token, store_id)
    response = await client.post(
        f"{INVITES_URL}/{invite2}/accept",
        json={},
        headers={"Authorization": f"Bearer {client_token}"},
    )
    assert response.status_code == 409
