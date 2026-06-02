# Guia da Fase 1 — Fundação

Este guia explica o que foi construído na Fase 1, por que cada peça existe e como
tudo se conecta. Escrito para quem lê este código pela primeira vez.

---

## O panorama geral

Antes de escrever qualquer funcionalidade, construímos a fundação: uma forma de
ler configurações, uma forma de ligar ao banco de dados, a definição de todas as
tabelas, e o sistema de migrações que cria essas tabelas no PostgreSQL.

Nada mais funciona sem isto. Uma rota não consegue consultar o banco se não há
ligação. O Alembic não consegue criar tabelas se não sabe que os modelos existem.
Os modelos não se registam se não houver um `Base`.

Esta é a ordem em que tudo foi construído — e a ordem importa:

```
1. .env + core/config.py      → a app conhece as suas configurações
2. db/session.py              → a app consegue ligar ao banco de dados
3. models/mixins.py           → colunas partilhadas definidas uma só vez
4. models/*.py                → todas as tabelas definidas
5. db/base.py                 → o Alembic consegue ver todas as tabelas
6. alembic/env.py             → Alembic configurado para async
7. alembic revision + upgrade → tabelas criadas no PostgreSQL
```

Estrutura de pastas dentro de `backend/`:

```
backend/
├── alembic/
│   ├── versions/            # ficheiros de migração gerados ficam aqui
│   └── env.py               # configuração do Alembic
├── alembic.ini              # ficheiro de settings do Alembic
├── app/
│   ├── core/
│   │   └── config.py        # lê o .env, expõe as configurações
│   ├── db/
│   │   ├── session.py       # engine + fábrica de sessões
│   │   └── base.py          # importa todos os modelos para o Alembic
│   └── models/
│       ├── mixins.py        # Base, ULIDMixin, TimestampMixin partilhados
│       ├── user.py
│       ├── store.py
│       ├── professional.py
│       ├── offering.py
│       ├── work_schedule.py
│       └── appointment.py
├── compose.yml              # PostgreSQL no Docker
└── .env                     # segredos — nunca versionados
```

---

## Mapa de decisões

Antes de entrar nos detalhes, aqui estão as escolhas não-óbvias desta fase e a
razão por trás de cada uma. São as perguntas mais prováveis numa revisão de código.

| Decisão | Alternativa rejeitada | Razão |
|---|---|---|
| ULID como primary key | Integer / UUID | Não enumerável + ordenável no tempo |
| Soft delete via `deleted_at` | `DELETE` físico | Auditoria, integridade referencial, RGPD |
| `anonymized_at` separado de `deleted_at` | Usar só soft delete | RGPD distingue "apagado" de "anonimizado" |
| `server_default=func.now()` nos timestamps | `default=datetime.now()` | Clock do banco é fonte de verdade única |
| `asyncpg` como driver | `psycopg2` (síncrono) | Não bloqueia o servidor em I/O concorrente |
| `expire_on_commit=False` | Valor padrão do SQLAlchemy | Lazy loading é incompatível com código async |
| `Numeric(10,2)` para dinheiro | `float` | Float não representa decimais com exatidão |
| `data_hora_fim` armazenado | Calculado na query | Evita JOIN ao `offerings` em cada verificação de slot |
| `RoleEnum(str, Enum)` | `Enum` simples | Serializa como string simples no JSON |
| `pool.NullPool` nas migrações | Pool padrão | Script pontual — não precisa de pool de ligações |
| `db/base.py` como bridge | Auto-descoberta de ficheiros | Python não importa ficheiros automaticamente |

---

## Docker + PostgreSQL

**Ficheiros:** `compose.yml`, `scripts/init-db.sql`

> **Decisão — Docker em vez de instalação local:**
> O banco corre num container — isolado, reprodutível, fácil de reiniciar.
> Toda a equipa usa a mesma versão do PostgreSQL sem configurar nada localmente.
> Um `docker compose up` é suficiente para começar a trabalhar.

O `compose.yml` define o container do banco:

```yaml
services:
  db:
    image: postgres:16-alpine
    environment:
      POSTGRES_USER: agendei
      POSTGRES_PASSWORD: agendei
      POSTGRES_DB: agendei_dev
    ports:
      - "5432:5432"
    volumes:
      - pgdata:/var/lib/postgresql/data
      - ./scripts/init-db.sql:/docker-entrypoint-initdb.d/init-db.sql
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U agendei -d agendei_dev"]
      interval: 10s
      timeout: 5s
      retries: 5
```

`POSTGRES_DB` cria um banco automaticamente. O `init-db.sql` cria o segundo
(`agendei_test`) porque o Docker só auto-cria o que está em `POSTGRES_DB`.

O `healthcheck` é importante: permite que outros serviços declarem
`depends_on: db: condition: service_healthy`, o que os faz aguardar até o
PostgreSQL estar genuinamente a aceitar ligações — não apenas iniciado.

`pgdata` é um volume nomeado — os dados persistem entre reinícios do container.
Sem ele, cada `docker compose down` apagaria o banco.

> **Decisão — Dois bancos (`agendei_dev` e `agendei_test`):**
> Os testes correm contra um banco real separado, sem poluir os dados de
> desenvolvimento. Isto é reforçado pela configuração dos testes, que usa
> `DATABASE_URL_TEST` em vez de `DATABASE_URL`.

---

## `.env` + `core/config.py` — Configuração

**Por que existe:** A app precisa de valores que mudam por ambiente — endereço do
banco, segredo JWT, etc. Colocá-los diretamente no código é um risco de segurança
(segredos ficam no git) e torna o deploy impossível (dev e produção apontam para
bancos diferentes).

A solução: guardar os valores em `.env`, nunca versionar esse ficheiro, e lê-lo
num único lugar central.

**`.env`** (ignorado pelo git):

```
DATABASE_URL=postgresql+asyncpg://agendei:agendei@localhost:5432/agendei_dev
DATABASE_URL_TEST=postgresql+asyncpg://agendei:agendei@localhost:5432/agendei_test
JWT_SECRET=change-me-before-production
JWT_ALGORITHM=HS256
JWT_EXPIRATION_MINUTES=60
```

**`.env.example`** é versionado — é um template que os colaboradores copiam e
preenchem. Sem segredos reais, apenas as chaves.

**`config.py`:**

```python
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env")

    database_url: str
    database_url_test: str
    jwt_secret: str
    jwt_algorithm: str
    jwt_expiration_minutes: int

settings = Settings()  # type: ignore[call-arg]
```

`BaseSettings` lê o ficheiro `.env` e mapeia cada chave para um campo tipado.
`DATABASE_URL` → `settings.database_url`. Case-insensitive. Se uma variável
obrigatória estiver em falta, lança um erro imediatamente no arranque — o
problema aparece de imediato em vez de surgir como um erro críptico mais tarde.

`settings` é criado uma vez no carregamento do módulo. Todos os outros ficheiros
importam-no:

```python
from app.core.config import settings

engine = create_async_engine(settings.database_url)
```

> **Decisão — `SettingsConfigDict` em vez de `class Config` interna:**
> A sintaxe com `class Config` interna é legacy do Pydantic v1. `SettingsConfigDict`
> é a forma do Pydantic v2 — funcionalmente equivalente, mas compatível com o
> futuro e com melhor suporte de IDE.

---

## `db/session.py` — Ligação ao banco de dados

**Por que existe:** Os modelos descrevem as tabelas, mas algo tem de abrir
efetivamente uma ligação ao PostgreSQL e executar as queries. É este ficheiro.

```python
from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from app.core.config import settings

engine = create_async_engine(settings.database_url, echo=True)
SessionLocal = async_sessionmaker(engine, expire_on_commit=False)

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with SessionLocal() as session:
        yield session
```

**Engine** — o pool de ligações. Criado uma vez quando a app arranca, partilhado
durante toda a sua vida. `echo=True` imprime cada query SQL no terminal — útil em
desenvolvimento, desligar em produção.

> **Decisão — `asyncpg` em vez de `psycopg2`:**
> O URL do banco usa `postgresql+asyncpg://`. O `asyncpg` é o driver PostgreSQL
> assíncrono. Sem ele, cada query ao banco bloquearia o servidor inteiro enquanto
> aguardava resposta — numa app async que trata pedidos concorrentes, isso seria
> um problema grave de performance.

**SessionLocal** — uma fábrica que cria sessões. Uma sessão é uma unidade de
trabalho: abrir, executar queries, commit ou rollback, fechar. Um pedido HTTP =
uma sessão.

> **Decisão — `expire_on_commit=False`:**
> Por defeito, o SQLAlchemy marca todos os objetos carregados como "expirados"
> após um commit, o que significa que a próxima vez que aceder aos seus atributos
> tenta recarregá-los do banco. Em código async isso causa um erro porque o
> SQLAlchemy não consegue fazer uma query lazy síncrona. Definir `False` mantém
> os objetos válidos após o commit.

**`get_db()`** — uma dependência FastAPI. O `yield` torna-a um generator:

```python
async def get_db():
    async with SessionLocal() as session:
        yield session          # ← pausa aqui, entrega a sessão à rota
    # ← retoma aqui depois da rota terminar, a sessão fecha automaticamente
```

As rotas usam-na via `Depends`:

```python
@router.get("/lojas")
async def list_lojas(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Loja))
    ...
```

O FastAPI trata de chamar `get_db`, injetar a sessão e fechá-la após a resposta.
Nunca se gere sessões manualmente nas rotas.

---

## `models/mixins.py` — Colunas partilhadas

**Por que existe:** Cada tabela precisa de um `id`, a maioria precisa de
timestamps, e todas usam soft delete. Copiar e colar essas colunas em vários
ficheiros de modelos seria repetitivo e sujeito a erros. Os mixins resolvem isso
com herança.

### `Base`

```python
from sqlalchemy.orm import DeclarativeBase

class Base(DeclarativeBase):
    pass
```

A classe-pai de que todos os modelos herdam. O SQLAlchemy usa-a para rastrear
cada tabela registada via `Base.metadata`. Deve existir exatamente **um** `Base`
em toda a app — se criar dois acidentalmente, alguns modelos ficam invisíveis para
o Alembic. Vive aqui para que cada modelo importe do mesmo lugar.

### `ULIDMixin`

```python
class ULIDMixin:
    id: Mapped[str] = mapped_column(
        String(26),
        primary_key=True,
        default=lambda: str(ULID()),
    )
```

Adiciona uma primary key `id` a qualquer modelo que herde este mixin. Gerado em
Python com a biblioteca `python-ulid`, guardado como string de 26 caracteres no
PostgreSQL.

> **Decisão — ULID em vez de UUID ou inteiro:**
>
> - **IDs inteiros** são sequenciais — `/usuarios/1`, `/usuarios/2` expõe quantos
>   utilizadores existem e torna os IDs adivinháveis. Um atacante pode enumerar
>   todos os registos com um simples ciclo.
> - **UUIDs** são aleatórios, não adivinháveis, mas sem ordenação — não se consegue
>   saber qual foi criado primeiro sem consultar `created_at`.
> - **ULIDs** são aleatórios mas ordenáveis no tempo — os primeiros 10 caracteres
>   codificam um timestamp em milissegundos, por isso ordenar por `id` dá ordem
>   cronológica. O melhor dos dois mundos.

### `TimestampMixin`

```python
class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(),
        onupdate=lambda: datetime.now(timezone.utc)
    )
    deleted_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True, default=None
    )
```

> **Decisão — `server_default=func.now()` em vez de `default=datetime.now()`:**
> Com `server_default`, é o banco a definir o timestamp, não o Python. Se usasse
> `default` em Python, o timestamp dependeria do relógio do servidor da app. Se
> houver vários servidores a correr (escalonamento horizontal) com relógios
> ligeiramente desfasados, os timestamps ficariam inconsistentes. O relógio do
> banco é uma fonte de verdade única.

**`onupdate` em `updated_at`** — o SQLAlchemy chama este lambda automaticamente
sempre que uma linha é atualizada. Nunca se define `updated_at` manualmente.

> **Decisão — Soft delete via `deleted_at` em vez de `DELETE` físico:**
> Nunca se executa `DELETE` nesta app. Quando um registo é "apagado", define-se
> `deleted_at` para o momento atual e filtra-se nas queries com
> `.where(Model.deleted_at.is_(None))`. Razões:
>
> - **Auditoria:** consegue-se ver o que foi apagado e quando
> - **Integridade referencial:** registos relacionados não se partem
> - **RGPD:** precisamos de distinguir entre "soft deleted" e "anonimizado" —
>   são duas coisas diferentes

> **Decisão — `anonymized_at` separado de `deleted_at`:**
> O RGPD impõe o "direito ao esquecimento" — o utilizador pode pedir que os seus
> dados pessoais sejam apagados. Mas não podemos eliminar a linha (integridade
> referencial). A solução é anonimizar: a linha fica, mas `name`, `email`,
> `phone` são substituídos por valores anonimizados, e `anonymized_at` regista
> quando isso aconteceu. Soft delete e anonimização são operações distintas com
> finalidades distintas.

---

## Os modelos

### Como ler um modelo

```python
class Store(Base, ULIDMixin, TimestampMixin):
    __tablename__ = "stores"                              # nome da tabela no PostgreSQL

    name: Mapped[str] = mapped_column(String(100))        # NOT NULL, máx 100 chars
    description: Mapped[Optional[str]] = mapped_column(Text)  # nullable
    owner_id: Mapped[str] = mapped_column(                # coluna foreign key
        String(26), ForeignKey("users.id")
    )

    owner: Mapped[User] = relationship("User")            # navegação, não é coluna
```

`Mapped[str]` = NOT NULL. `Mapped[Optional[str]]` = nullable. O SQLAlchemy infere
a nulabilidade do tipo Python — raramente se escreve `nullable=True/False`
explicitamente.

`ForeignKey` referencia o **nome da tabela** (`"users.id"`), não o nome da classe
Python. `relationship` é separado — não é uma coluna no banco, é uma conveniência
Python que permite fazer `store.owner` para obter o objeto `User` em vez de
apenas a string `owner_id`.

---

### `user.py` — a tabela central

Quase tudo está ligado ao `User`. Tem tanto dados de autenticação (`email`,
`password_hash`) como dados de identidade (`name`, `phone`, `role`).

**`role`** é um Enum guardado como string no PostgreSQL:

```python
class RoleEnum(str, enum.Enum):
    client = "client"
    professional = "professional"
    store_admin = "store_admin"
```

> **Decisão — `RoleEnum(str, enum.Enum)` em vez de `enum.Enum` simples:**
> Herdar de `str` faz com que os valores se serializem como strings simples em
> JSON — `"client"` em vez de `{"value": "client"}`. Sem esta herança, o
> FastAPI/Pydantic precisaria de configuração extra para serializar corretamente.

**Campos RGPD:**

- `accepted_terms_at` + `accepted_terms_version` — regista quando e que versão
  dos termos um utilizador aceitou. Requisito legal.
- `anonymized_at` — regista quando os dados pessoais foram apagados. A linha
  fica (para integridade referencial), mas `name`, `email`, `phone` são
  substituídos por valores anonimizados. Este é o "direito ao esquecimento" do
  RGPD — diferente do soft delete.

---

### `store.py` — loja

`owner_id` FK liga uma loja ao seu utilizador `store_admin`. Os campos de
contacto são maioritariamente opcionais — uma loja pode ser criada só com o nome
e completada depois.

`is_active` é um flag separado de `deleted_at`.

> **Decisão — `is_active` separado de `deleted_at`:**
> Soft delete remove permanentemente. `is_active = false` esconde da listagem
> pública mas mantém a loja gerível no painel de administração. São estados
> operacionais distintos.

---

### `professional.py` — profissional

> **Decisão — `Professional` como tabela separada de `User`:**
> Um utilizador com role `professional` tem também uma linha aqui com atributos
> extra (`bio`, `photo_url`). Estes campos não pertencem ao `User` porque nem
> todos os utilizadores são profissionais. Separar mantém o modelo limpo — `User`
> guarda identidade e autenticação, `Professional` guarda atributos específicos
> da profissão.

---

### `offering.py` — serviço

Pertence a um `Professional`, não diretamente a uma `Store`.

> **Decisão — serviços pertencem ao profissional, não à loja:**
> Profissionais diferentes na mesma loja podem oferecer serviços diferentes a
> preços diferentes. Se os serviços pertencessem à loja, seria impossível ter
> esse nível de detalhe.

> **Decisão — `Numeric(10,2)` para preço em vez de `float`:**
> Ponto flutuante não consegue representar a maioria dos números decimais com
> exatidão: `0.1 + 0.2 = 0.30000000000000004`. Um erro de faturação causado por
> isso seria embaraçoso. `Numeric` guarda o valor decimal exato.

`duration_minutes` é o que o algoritmo de slots usa para determinar quanto tempo
dura um slot e quando o próximo pode começar.

---

### `work_schedule.py` — horário de trabalho

Uma linha por dia de trabalho por profissional. Um profissional que trabalha de
segunda a sexta tem 5 linhas.

`day_of_week` é um inteiro 0–6 que corresponde ao `date.weekday()` do Python
(0 = segunda, 6 = domingo). O algoritmo de slots faz `data.weekday()` na data
pedida e procura a linha correspondente.

> **Decisão — sem `TimestampMixin` nos horários de trabalho:**
> Os horários não precisam de colunas de auditoria. Se um horário mudar,
> atualiza-se ou desativa-se a linha, e `is_active` trata da visibilidade.
> Adicionar timestamps seria ruído sem valor prático.

---

### `appointment.py` — agendamento

A tabela mais conectada. Liga `client_id` → `professional_id` → `offering_id`
com um slot de tempo.

> **Decisão — `end_datetime` armazenado em vez de calculado:**
> Quando se cria um agendamento, o serviço calcula
> `start_datetime + offering.duration_minutes` e guarda o resultado. O algoritmo
> de slots consulta agendamentos sobrepostos usando os dois campos — se fosse
> recalculado em cada query, precisaria de um JOIN ao `offerings` em cada
> verificação de disponibilidade, o que é lento.

**Fluxo de `status`:**

```
pending → confirmed → completed
    └────────────────→ cancelled
```

Só `pending` e `confirmed` bloqueiam um slot. `cancelled` e `completed`
libertam-no.

> **Decisão — `cancelled_by` como `String(26)` em vez de FK com `relationship`:**
> Só precisamos de registar o ID de quem cancelou — não precisamos de navegar de
> um agendamento para o cancelador como objeto. Um `relationship` adicionaria
> complexidade sem benefício prático.

**`reminder_sent`** evita que o job de lembretes envie duplicados. O job consulta
todos os agendamentos dentro da janela de lembrete onde `reminder_sent = false`,
envia os emails e define o flag como `true`.

> **Decisão — `foreign_keys=[client_id]` na relationship `client`:**
> `User` aparece duas vezes nesta tabela — `client_id` e `cancelled_by`
> (que também guarda um ID de utilizador). O SQLAlchemy vê dois caminhos para
> `User` e não sabe qual o `client` deve usar. O hint `foreign_keys` remove a
> ambiguidade.

---

## `db/base.py` — a ponte do Alembic

```python
from app.models.mixins import Base          # noqa: F401
from app.models.user import User            # noqa: F401
from app.models.store import Store          # noqa: F401
from app.models.professional import Professional  # noqa: F401
from app.models.offering import Offering    # noqa: F401
from app.models.work_schedule import WorkSchedule  # noqa: F401
from app.models.appointment import Appointment  # noqa: F401
```

O Alembic percorre o `Base.metadata` para encontrar tabelas. Um modelo só se
regista com o `Base` quando a sua classe é importada — o Python não
auto-descobre ficheiros.

> **Decisão — ficheiro de bridge explícito:**
> Se adicionar um novo modelo e esquecer de o colocar aqui, o Alembic gera uma
> migração sem essa tabela e só se descobre quando a tabela não existe no banco.
> O `db/base.py` é a lista explícita e autoritativa de todos os modelos.

`# noqa: F401` silencia o aviso do linter de "importado mas não usado". As
importações não estão sem uso — estão a fazer trabalho real como efeito lateral
do carregamento da classe.

**Usado por:** `alembic/env.py` apenas. Não é importado em nenhum lado em runtime.

---

## `alembic/` — Migrações

Migrações são scripts SQL versionados que evoluem o schema do banco ao longo do
tempo. Em vez de executar `CREATE TABLE` ou `ALTER TABLE` manualmente, o Alembic
gera-os e corre-os automaticamente.

### `alembic.ini`

O ficheiro de settings. Duas linhas que importam:

```ini
script_location = alembic   # onde ficam os ficheiros de migração
prepend_sys_path = .         # adiciona backend/ ao Python path para imports "from app..."
```

### `alembic/env.py`

A configuração de runtime do Alembic. O padrão é apenas síncrono — foi reescrito
para suportar async:

```python
from app.core.config import settings
from app.db.base import Base  # despoleta todas as importações dos modelos

target_metadata = Base.metadata  # Alembic lê isto para saber que tabelas existem

async def run_migrations_online() -> None:
    connectable = create_async_engine(settings.database_url, poolclass=pool.NullPool)

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)  # ponte: async → sync
```

> **Decisão — `pool.NullPool` nas migrações:**
> O Alembic é executado como um script pontual, não como um servidor. Pool de
> ligações é desnecessário para um script one-shot — cada comando abre uma
> ligação fresca e fecha-a. `NullPool` elimina a overhead de manter ligações
> abertas.

> **Decisão — `run_sync` para fazer a ponte async → sync:**
> O Alembic não é nativamente async. O padrão para usá-lo com um engine async é
> passar o código síncrono do Alembic para dentro de uma ligação async via
> `run_sync`. `do_run_migrations` é uma função síncrona normal que o Alembic
> conhece; `run_sync` executa-a dentro do contexto async.

### O fluxo de migrações

```bash
# Gera uma migração comparando os modelos com o schema atual do banco
uv run alembic revision --autogenerate -m "descrição"

# Aplica todas as migrações pendentes
uv run alembic upgrade head

# Reverte uma migração
uv run alembic downgrade -1

# Vê o estado atual das migrações
uv run alembic current
```

`--autogenerate` lê o `Base.metadata` e compara com o schema real do banco.
Gera o SQL de `CREATE TABLE` / `ALTER TABLE` automaticamente. Deve-se sempre
rever o ficheiro gerado antes de o aplicar.

---

## Como tudo se conecta

```
.env
 └── core/config.py          lê o .env, expõe configurações tipadas
      ├── db/session.py       usa DATABASE_URL → engine + get_db()
      └── alembic/env.py      usa DATABASE_URL → engine de migração

models/mixins.py              define Base, ULIDMixin, TimestampMixin
 └── todos os modelos         herdam dos mixins, definem colunas

db/base.py                    importa todos os modelos (efeito lateral: regista-os com Base)
 └── alembic/env.py           lê Base.metadata → conhece todas as tabelas → gera migrações
```

**Ciclo de vida de um pedido:**

```
Pedido HTTP chega
 └── FastAPI router encontra a rota
      └── FastAPI chama get_db() via Depends
           └── sessão abre
                └── rota chama uma função de serviço, passa a sessão
                     └── serviço executa queries usando a sessão + classes de modelo
                          └── resposta enviada → sessão fecha
```

A camada de serviços é onde vive a lógica de negócio — não na rota e não no
modelo. Rotas são finas: recebem um pedido, chamam um serviço, devolvem uma
resposta. Os serviços são testáveis de forma isolada porque recebem uma sessão
como parâmetro em vez de a criarem eles próprios.
