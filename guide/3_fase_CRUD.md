# Guia da Fase 3 — CRUD e Algoritmo de Slots

Este guia explica o que foi construído na Fase 3, por que cada decisão foi tomada, e como tudo se conecta. Escrito para quem lê o código pela primeira vez.

---

## O que a Fase 3 entrega

As Fases 1 e 2 criaram a fundação (banco de dados) e a autenticação (quem és tu). A Fase 3 constrói o núcleo do produto:

- CRUD de **Lojas** — criar, listar, atualizar, deletar
- CRUD de **Profissionais** — associar profissionais a lojas
- CRUD de **Serviços** — o que cada profissional oferece
- CRUD de **Horários de trabalho** — quando cada profissional trabalha
- CRUD de **Agendamentos** — os clientes marcam consultas
- **Algoritmo de slots** — calcula os horários livres para um dia

```
backend/
└── app/
    ├── schemas/
    │   ├── loja.py
    │   ├── profissional.py
    │   ├── servico.py
    │   ├── horario_trabalho.py
    │   └── agendamento.py          ← inclui SlotDisponivel
    ├── services/
    │   ├── loja_service.py
    │   ├── profissional_service.py
    │   ├── servico_service.py
    │   ├── horario_service.py
    │   └── agendamento_service.py  ← contém o algoritmo de slots
    ├── routers/
    │   ├── lojas.py
    │   ├── profissionais.py
    │   ├── servicos_horarios.py    ← dois routers num só ficheiro
    │   └── agendamentos.py
    └── main.py                     ← registra todos os routers
```

---

## 1. Schemas — o contrato de dados

Cada recurso tem três schemas:

| Schema | Para que serve |
|--------|---------------|
| `XxxCreate` | Valida o body do POST |
| `XxxUpdate` | Valida o body do PATCH (tudo opcional) |
| `XxxPublic` | O que o frontend recebe na resposta |

**Por que separar Create de Update?**

No `Create`, campos obrigatórios (como `nome`) são `str`. No `Update`, os mesmos campos são `Optional[str] = None` — só atualizas o que enviares. Se usasses o mesmo schema para os dois, o PATCH seria obrigado a enviar todos os campos, o que é mau UX.

**Por que ter um `XxxPublic` separado do modelo SQLAlchemy?**

O modelo tem colunas internas que nunca devem sair na API: `deleted_at`, `senha_hash`, etc. O `XxxPublic` é uma whitelist explícita. O `response_model` no router usa-o como filtro — mesmo que o service retorne o objeto completo, só os campos declarados saem para o cliente.

### Validadores nos schemas

```python
# schemas/horario_trabalho.py
@model_validator(mode="after")
def horario_consistente(self) -> "HorarioTrabalhoCreate":
    if self.hora_fim <= self.hora_inicio:
        raise ValueError("hora_fim deve ser depois de hora_inicio")
    return self
```

`model_validator(mode="after")` corre depois de todos os campos serem validados individualmente — por isso consegues comparar `hora_fim` com `hora_inicio` (ambos já são objetos `time`). Se usasses `field_validator`, só terias acesso a um campo de cada vez.

Quando um validador levanta `ValueError`, o FastAPI converte automaticamente numa resposta `422 Unprocessable Entity` com mensagem descritiva.

---

## 2. A camada de services — onde vive a lógica

Todos os services recebem `db: AsyncSession` como parâmetro normal, não via `Depends()`. Isto tem uma consequência importante: **podes testar a lógica de negócio sem arrancar o FastAPI** — basta passares uma sessão de teste diretamente.

### Padrão PATCH com `exclude_unset=True`

```python
# services/loja_service.py
campos = data.model_dump(exclude_unset=True)
for campo, valor in campos.items():
    setattr(loja, campo, valor)
```

`exclude_unset=True` devolve apenas os campos que o cliente enviou. Se o cliente mandou `{"nome": "Novo Nome"}`, `campos` é `{"nome": "Novo Nome"}` — não inclui `descricao`, `telefone`, etc. Sem isso, o PATCH sobrescreveria todos os campos com `None`.

### Soft delete consistente

```python
loja.deleted_at = datetime.now(timezone.utc)
await db.commit()
```

Nunca corremos `DELETE` na base de dados. Todos os `SELECT` filtram com `.where(Modelo.deleted_at.is_(None))`. Um registo "deletado" ainda existe — só está invisível para as queries normais. Isto preserva o histórico de agendamentos e cumpre o GDPR.

### Verificação de posse

A maior parte das operações de escrita verifica se o utilizador autenticado é o dono do recurso:

```python
if loja.owner_id != usuario.id:
    raise HTTPException(status_code=403, detail="Apenas o dono da loja pode editá-la")
```

Esta verificação acontece no **service**, não no router. O router apenas trata de HTTP — recebe o request, chama o service, devolve a resposta. A lógica de autorização fina fica no service porque é aí que o contexto existe.

---

## 3. O algoritmo de slots disponíveis

Este é o algoritmo mais importante da aplicação. Encontra-se em `agendamento_service.py`.

### O problema

Dado um profissional, um serviço e uma data, quais são os horários em que o cliente pode marcar?

### A solução em 3 passos

```python
async def listar_slots_disponiveis(db, profissional_id, servico_id, data_consulta):

    # Passo 1: o profissional trabalha neste dia da semana?
    dia_semana = data_consulta.weekday()  # 0=segunda, 6=domingo
    horario = ...busca HorarioTrabalho para este dia...
    if horario is None:
        return []  # não trabalha — lista vazia

    # Passo 2: quais agendamentos já existem neste dia?
    agendamentos_ocupados = ...busca pendentes e confirmados...

    # Passo 3: gera slots e filtra os que colidem
    cursor = hora_inicio do expediente
    while cursor + duracao_servico <= hora_fim do expediente:
        if slot não colide com nenhum agendamento:
            adiciona à lista
        cursor = cursor + duracao_servico
```

### Por que `data_hora_fim` é guardada no agendamento?

É tentador calcular `fim = inicio + duracao_servico` na hora da query. Mas isso exigiria um JOIN com a tabela `servicos` em cada verificação de colisão. Com muitos agendamentos, a query ficaria lenta.

Ao guardar `data_hora_fim` diretamente no `agendamento`, a query de colisão é simples:

```python
Agendamento.data_hora_inicio < data_hora_fim,
Agendamento.data_hora_fim > data_hora_inicio,
```

Dois campos indexáveis, sem JOINs.

### A lógica de colisão de intervalos

Dois intervalos `[A, B]` e `[C, D]` **colidem** se:
```
A < D  E  B > C
```

O equivalente em código:

```python
def _slot_colide(inicio, fim, agendamentos):
    for ag in agendamentos:
        if inicio < ag.data_hora_fim and fim > ag.data_hora_inicio:
            return True
    return False
```

Visualmente:
```
Agendamento existente:  |-------|
Slot proposto A:    |---|            → não colide (fim A <= início existente)
Slot proposto B:            |---|   → não colide (início B >= fim existente)
Slot proposto C:       |-----|      → COLIDE
Slot proposto D:    |-----------|   → COLIDE
```

### Proteção contra race condition

O endpoint `GET /slots` pode ser consultado por múltiplos clientes ao mesmo tempo. Entre o momento em que o cliente vê os slots disponíveis e o momento em que confirma o agendamento, outro cliente pode ter ocupado o mesmo horário.

Por isso, no `POST /agendamentos`, fazemos uma **segunda verificação de conflito**:

```python
conflito = await db.execute(
    select(Agendamento).where(
        Agendamento.profissional_id == data.profissional_id,
        Agendamento.status.in_([StatusEnum.pendente, StatusEnum.confirmado]),
        Agendamento.data_hora_inicio < data_hora_fim,
        Agendamento.data_hora_fim > data_hora_inicio,
    )
)
if conflito.scalar_one_or_none() is not None:
    raise HTTPException(status_code=409, detail="Este horário não está mais disponível")
```

O `GET /slots` é para UX (mostrar opções). O `POST /agendamentos` é a verificação real. Esta é a diferença entre "optimistic UI" e "server-side truth".

---

## 4. As transições de status

Um agendamento passa por estados bem definidos:

```
pendente → confirmado → concluido
    └──────────────────→ cancelado
```

O código usa uma tabela de transições válidas:

```python
TRANSICOES_VALIDAS = {
    StatusEnum.pendente:   [StatusEnum.confirmado, StatusEnum.cancelado],
    StatusEnum.confirmado: [StatusEnum.concluido,  StatusEnum.cancelado],
    StatusEnum.concluido:  [],
    StatusEnum.cancelado:  [],
}
```

Se alguém tentar mover de `concluido` para `cancelado`, recebe `422`. Se tentar mover de `cancelado` para `confirmado`, recebe `422`. Os estados `concluido` e `cancelado` são **terminais** — não há retorno.

Quando o status muda para `cancelado`, registamos quem cancelou:
```python
if data.status == StatusEnum.cancelado:
    ag.cancelado_por = usuario.id
```

Isto é importante para auditoria: o admin pode ver se foi o cliente ou o profissional a cancelar.

---

## 5. A estrutura de URLs

As URLs seguem REST aninhado onde faz sentido:

```
# Recursos que dependem de outro recurso
POST   /api/v1/lojas/{loja_id}/profissionais
GET    /api/v1/lojas/{loja_id}/profissionais
GET    /api/v1/profissionais/{id}/servicos
POST   /api/v1/profissionais/{id}/horarios

# Recursos independentes com query params para filtrar
GET    /api/v1/agendamentos/slots?profissional_id=...&servico_id=...&data=...
POST   /api/v1/agendamentos
GET    /api/v1/agendamentos/meus
PATCH  /api/v1/agendamentos/{id}/status
```

**Por que `/meus` antes de `/{id}`?**

O FastAPI interpreta rotas por ordem de declaração. Se `/{id}` viesse primeiro, um pedido para `/meus` seria interpretado como `id="meus"` e daria 404. Ao declarar `/meus` primeiro, o FastAPI faz match correto.

---

## 6. Rotas públicas vs. protegidas

| Rota | Autenticação necessária? |
|------|--------------------------|
| `GET /lojas` | Não |
| `GET /lojas/{id}` | Não |
| `POST /lojas` | Sim — `admin_loja` |
| `GET /profissionais/{id}/servicos` | Não |
| `GET /agendamentos/slots` | Não |
| `POST /agendamentos` | Sim — qualquer utilizador |
| `GET /agendamentos/meus` | Sim — qualquer utilizador |
| `PATCH /agendamentos/{id}/status` | Sim — cliente, profissional ou admin |

Rotas de leitura pública fazem sentido para o produto: um cliente deve poder ver lojas e horários disponíveis sem ter de criar conta primeiro.

---

## 7. Como registar os routers no `main.py`

```python
PREFIX = "/api/v1"

app.include_router(lojas_router,         prefix=PREFIX)
app.include_router(profissionais_router, prefix=PREFIX)
app.include_router(servicos_router,      prefix=PREFIX)
app.include_router(horarios_router,      prefix=PREFIX)
app.include_router(agendamentos_router,  prefix=PREFIX)
```

Cada router define o seu próprio `prefix` (ex: `prefix="/lojas"`). O `include_router` adiciona `/api/v1` por cima. O resultado final é `/api/v1/lojas`, `/api/v1/agendamentos`, etc.

`servicos_router` e `horarios_router` estão no mesmo ficheiro (`servicos_horarios.py`) porque são recursos pequenos com a mesma estrutura. Não há regra contra ter dois routers por ficheiro.

---

## Como testar manualmente

Com o servidor a correr (`uv run fastapi dev app/main.py`), abre o Swagger em `http://localhost:8000/docs`.

**Fluxo típico:**

```
1. POST /auth/register    → cria um admin_loja
2. POST /auth/login       → obtém o access_token
3. POST /lojas            → cria uma loja (com o token)
4. POST /auth/register    → cria um utilizador com role=profissional
5. POST /lojas/{id}/profissionais → associa o profissional à loja
6. POST /profissionais/{id}/servicos → cria um serviço (ex: "Corte de cabelo", 30 min)
7. POST /profissionais/{id}/horarios → define horário (ex: segunda, 09:00–18:00)
8. GET  /agendamentos/slots?...&data=2025-08-18 → vê os slots disponíveis
9. POST /auth/register    → cria um utilizador com role=cliente
10. POST /auth/login      → faz login como cliente
11. POST /agendamentos    → marca um agendamento num dos slots
12. PATCH /agendamentos/{id}/status → confirma o agendamento
```

---

## O que vem na Fase 4

A Fase 3 construiu o núcleo do produto. A Fase 4 pode adicionar:

- **Lembretes por email** — job que corre a cada X minutos e envia emails para agendamentos confirmados com `lembrete_enviado=false`
- **Testes** — pytest com base de dados de teste isolada (`DATABASE_URL_TEST`)
- **Paginação** — para listas longas de agendamentos
- **Filtros** — listar agendamentos por data, por status
- **Anonimização GDPR** — endpoint para apagar dados pessoais de um utilizador