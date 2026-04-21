import pytest
from httpx import AsyncClient

BASE_URL = "/api/v1/lojas"
REGISTER_URL = "/api/v1/auth/register"
LOGIN_URL = "/api/v1/auth/login"

ADMIN_USER = {
    "nome": "Jessé Admin",
    "email": "admin@example.com",
    "password": "password123",
    "role": "admin_loja",
    "accepted_terms": True,
}

OTHER_ADMIN_USER = {
    "nome": "Outro Admin",
    "email": "outro@example.com",
    "password": "password123",
    "role": "admin_loja",
    "accepted_terms": True,
}

CLIENT_USER = {
    "nome": "Cliente",
    "email": "cliente@example.com",
    "password": "password123",
    "role": "cliente",
    "accepted_terms": True,
}

VALID_LOJA = {"nome": "Salão do Jessézin"}


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
# GET /lojas
# ---------------------------------------------------------------------------


async def test_listar_lojas_vazia(client: AsyncClient):
    response = await client.get(BASE_URL)
    assert response.status_code == 200
    assert response.json() == []


async def test_listar_lojas_retorna_ativas(client: AsyncClient, admin_token: str):
    await client.post(BASE_URL, json=VALID_LOJA, headers={"Authorization": f"Bearer {admin_token}"})
    response = await client.get(BASE_URL)
    assert response.status_code == 200
    assert len(response.json()) == 1


async def test_listar_lojas_nao_retorna_deletadas(client: AsyncClient, admin_token: str):
    created = await client.post(BASE_URL, json=VALID_LOJA, headers={"Authorization": f"Bearer {admin_token}"})
    loja_id = created.json()["id"]
    await client.delete(f"{BASE_URL}/{loja_id}", headers={"Authorization": f"Bearer {admin_token}"})
    response = await client.get(BASE_URL)
    assert response.status_code == 200
    assert response.json() == []


# ---------------------------------------------------------------------------
# GET /lojas/{id}
# ---------------------------------------------------------------------------


async def test_get_loja_success(client: AsyncClient, admin_token: str):
    created = await client.post(BASE_URL, json=VALID_LOJA, headers={"Authorization": f"Bearer {admin_token}"})
    loja_id = created.json()["id"]
    response = await client.get(f"{BASE_URL}/{loja_id}")
    assert response.status_code == 200
    assert response.json()["id"] == loja_id


async def test_get_loja_nao_encontrada(client: AsyncClient):
    response = await client.get(f"{BASE_URL}/00000000000000000000000000")
    assert response.status_code == 404


async def test_get_loja_deletada_retorna_404(client: AsyncClient, admin_token: str):
    created = await client.post(BASE_URL, json=VALID_LOJA, headers={"Authorization": f"Bearer {admin_token}"})
    loja_id = created.json()["id"]
    await client.delete(f"{BASE_URL}/{loja_id}", headers={"Authorization": f"Bearer {admin_token}"})
    response = await client.get(f"{BASE_URL}/{loja_id}")
    assert response.status_code == 404


# ---------------------------------------------------------------------------
# POST /lojas
# ---------------------------------------------------------------------------


async def test_criar_loja_success(client: AsyncClient, admin_token: str):
    response = await client.post(BASE_URL, json=VALID_LOJA, headers={"Authorization": f"Bearer {admin_token}"})
    assert response.status_code == 201
    body = response.json()
    assert body["nome"] == VALID_LOJA["nome"]
    assert "id" in body
    assert "deleted_at" not in body
    assert "senha_hash" not in body


async def test_criar_loja_sem_token(client: AsyncClient):
    response = await client.post(BASE_URL, json=VALID_LOJA)
    assert response.status_code == 401


async def test_criar_loja_role_errada(client: AsyncClient, client_token: str):
    response = await client.post(BASE_URL, json=VALID_LOJA, headers={"Authorization": f"Bearer {client_token}"})
    assert response.status_code == 403


async def test_criar_loja_sem_nome(client: AsyncClient, admin_token: str):
    response = await client.post(BASE_URL, json={}, headers={"Authorization": f"Bearer {admin_token}"})
    assert response.status_code == 422


# ---------------------------------------------------------------------------
# PATCH /lojas/{id}
# ---------------------------------------------------------------------------


async def test_atualizar_loja_success(client: AsyncClient, admin_token: str):
    created = await client.post(BASE_URL, json=VALID_LOJA, headers={"Authorization": f"Bearer {admin_token}"})
    loja_id = created.json()["id"]
    response = await client.patch(
        f"{BASE_URL}/{loja_id}",
        json={"nome": "Novo Nome", "telefone": "11999999999"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["nome"] == "Novo Nome"
    assert body["telefone"] == "11999999999"


async def test_atualizar_loja_parcial(client: AsyncClient, admin_token: str):
    created = await client.post(
        BASE_URL,
        json={**VALID_LOJA, "telefone": "11111111111"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    loja_id = created.json()["id"]
    response = await client.patch(
        f"{BASE_URL}/{loja_id}",
        json={"nome": "Novo Nome"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["nome"] == "Novo Nome"
    assert body["telefone"] == "11111111111"


async def test_atualizar_loja_nao_encontrada(client: AsyncClient, admin_token: str):
    response = await client.patch(
        f"{BASE_URL}/00000000000000000000000000",
        json={"nome": "X"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 404


async def test_atualizar_loja_dono_errado(client: AsyncClient, admin_token: str, other_admin_token: str):
    created = await client.post(BASE_URL, json=VALID_LOJA, headers={"Authorization": f"Bearer {admin_token}"})
    loja_id = created.json()["id"]
    response = await client.patch(
        f"{BASE_URL}/{loja_id}",
        json={"nome": "Invasão"},
        headers={"Authorization": f"Bearer {other_admin_token}"},
    )
    assert response.status_code == 403


async def test_atualizar_loja_sem_token(client: AsyncClient, admin_token: str):
    created = await client.post(BASE_URL, json=VALID_LOJA, headers={"Authorization": f"Bearer {admin_token}"})
    loja_id = created.json()["id"]
    response = await client.patch(f"{BASE_URL}/{loja_id}", json={"nome": "X"})
    assert response.status_code == 401


# ---------------------------------------------------------------------------
# DELETE /lojas/{id}
# ---------------------------------------------------------------------------


async def test_deletar_loja_success(client: AsyncClient, admin_token: str):
    created = await client.post(BASE_URL, json=VALID_LOJA, headers={"Authorization": f"Bearer {admin_token}"})
    loja_id = created.json()["id"]
    response = await client.delete(f"{BASE_URL}/{loja_id}", headers={"Authorization": f"Bearer {admin_token}"})
    assert response.status_code == 204


async def test_deletar_loja_get_retorna_404(client: AsyncClient, admin_token: str):
    created = await client.post(BASE_URL, json=VALID_LOJA, headers={"Authorization": f"Bearer {admin_token}"})
    loja_id = created.json()["id"]
    await client.delete(f"{BASE_URL}/{loja_id}", headers={"Authorization": f"Bearer {admin_token}"})
    response = await client.get(f"{BASE_URL}/{loja_id}")
    assert response.status_code == 404


async def test_deletar_loja_dono_errado(client: AsyncClient, admin_token: str, other_admin_token: str):
    created = await client.post(BASE_URL, json=VALID_LOJA, headers={"Authorization": f"Bearer {admin_token}"})
    loja_id = created.json()["id"]
    response = await client.delete(f"{BASE_URL}/{loja_id}", headers={"Authorization": f"Bearer {other_admin_token}"})
    assert response.status_code == 403


async def test_deletar_loja_sem_token(client: AsyncClient, admin_token: str):
    created = await client.post(BASE_URL, json=VALID_LOJA, headers={"Authorization": f"Bearer {admin_token}"})
    loja_id = created.json()["id"]
    response = await client.delete(f"{BASE_URL}/{loja_id}")
    assert response.status_code == 401
