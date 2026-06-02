# Guia da Fase 2 — Autenticação

Este guia explica o que foi construído na Fase 2, por que cada decisão foi tomada
e como tudo se conecta. Escrito para quem lê este código pela primeira vez.

---

## O problema que esta fase resolve

Após a Fase 1, o banco existia mas qualquer pessoa podia chamar qualquer endpoint
e fazer qualquer coisa. Não havia conceito de "quem está a fazer este pedido" ou
"esta pessoa tem permissão para fazer isto".

Autenticação responde: **quem és tu?**
Autorização responde: **o que podes fazer?**

A Fase 2 constrói as duas.

---

## O panorama geral — como a autenticação funciona

O sistema usa dois tokens:

**Access token** — um JWT de curta duração (15 minutos). O frontend guarda-o em
memória (uma variável JavaScript). É enviado no header `Authorization` em cada
pedido à API.

**Refresh token** — um JWT de longa duração (7 dias). Guardado num cookie
`httpOnly`, o que significa que o JavaScript não o consegue ler — só o browser o
envia automaticamente. É usado apenas para obter um novo access token quando o
anterior expira.

Pensa nisto como um sistema de segurança de um edifício:
- O **access token** é o teu crachá diário de visitante — válido por algumas
  horas, dá acesso à maioria das portas.
- O **refresh token** é a chave-mestra que guardas num cofre — só a usas para
  obter um novo crachá, nunca para abrir portas diretamente.

---

## Mapa de decisões

| Decisão | Alternativa rejeitada | Razão |
|---|---|---|
| Dois tokens (access + refresh) | Um único token de longa duração | Token roubado expira em 15min; refresh é protegido por cookie httpOnly |
| Refresh token em cookie `httpOnly` | localStorage / sessionStorage | JavaScript não consegue ler cookies httpOnly — protege contra XSS |
| `samesite="strict"` no cookie | `samesite="lax"` ou sem flag | Impede CSRF — um site malicioso não consegue acionar `/refresh` silenciosamente |
| `path` do cookie = `/api/v1/auth/refresh` | `path="/"` | O token só viaja quando é necessário — reduz a superfície de ataque |
| `bcrypt` diretamente | `passlib` | `passlib` quebrou com bcrypt >= 4.x por remover `__about__` |
| Mesma mensagem de erro para email/password errados | Mensagens distintas | Impede enumeração — um atacante não consegue saber se o email existe |
| 409 para email duplicado | 400 | 409 "Conflict" é semanticamente correto — o pedido é válido mas conflitua com estado existente |
| Buscar o utilizador no banco em cada pedido | Confiar apenas no JWT | Token válido não garante que a conta ainda existe ou não foi apagada |
| `require_role` retorna uma função (closure) | Função direta com role hardcoded | Os roles são parâmetros — a closure "lembra" os roles com que foi criada |
| 401 vs 403 distintos | Usar sempre 401 | 401 = não identificado; 403 = identificado mas sem permissão |

---

## Mapa de ficheiros

```
backend/
└── app/
    ├── core/
    │   ├── config.py          → lê .env para Python (inclui settings de JWT)
    │   ├── security.py        → hash de passwords, criação/descodificação de JWTs
    │   └── dependencies.py    → get_current_user, require_role
    ├── schemas/
    │   ├── user.py            → como um utilizador aparece nas respostas da API
    │   └── auth.py            → shapes de pedido/resposta para os endpoints de auth
    ├── services/
    │   └── auth_service.py    → lógica de negócio (register, login, refresh)
    ├── routers/
    │   └── auth.py            → os endpoints HTTP
    └── main.py                → ponto de entrada, regista tudo
```

---

## 1. Variáveis de ambiente — `.env`

```
JWT_SECRET=7625d894fc30f...         # chave secreta para assinar os tokens
JWT_ALGORITHM=HS256                 # algoritmo de assinatura
JWT_EXPIRATION_MINUTES=15           # access token dura 15 minutos
REFRESH_TOKEN_EXPIRE_DAYS=7         # refresh token dura 7 dias
ALLOWED_ORIGINS=["http://localhost:5173"]   # frontends autorizados a chamar a API
CURRENT_TERMS_VERSION=1.0           # versão dos termos que os utilizadores aceitam
```

> **Decisão — `JWT_SECRET` como variável de ambiente:**
> JWTs não são encriptados — qualquer pessoa pode descodificá-los e ler o
> conteúdo. Mas são *assinados*. A assinatura prova que o token foi criado pelo
> teu servidor e não foi adulterado. O segredo é o que torna a assinatura
> confiável. Se vazar, atacantes conseguem forjar tokens válidos.

> **Decisão — `ALLOWED_ORIGINS` explícito em vez de `"*"`:**
> CORS é um mecanismo de segurança do browser. Quando o frontend em
> `localhost:5173` chama a API em `localhost:8000`, o browser verifica primeiro
> se a API aceita falar com esse frontend. Usar `"*"` (qualquer origem) com
> cookies é rejeitado pelos browsers — tens de ser explícito.

---

## 2. Hash de passwords e JWTs — `app/core/security.py`

```python
import bcrypt
from jose import jwt

def hash_password(plain: str) -> str:
    return bcrypt.hashpw(plain.encode(), bcrypt.gensalt()).decode()

def verify_password(plain: str, hashed: str) -> bool:
    return bcrypt.checkpw(plain.encode(), hashed.encode())
```

> **Decisão — nunca guardar passwords em texto simples:**
> Se o banco vazar, os atacantes obtêm a password de cada utilizador — e como as
> pessoas reutilizam passwords, passam a controlar as contas desses utilizadores
> em todo o lado. O hash transforma `"senha123"` em algo como `"$2b$12$ZAwiv9..."`
> que não pode ser invertido. A única forma de verificar uma password é fazer o
> hash novamente e comparar.

> **Decisão — `bcrypt` diretamente em vez de `passlib`:**
> O `passlib` é uma biblioteca popular que envolve o bcrypt, mas quebrou com
> versões bcrypt >= 4.x (procurava um atributo `__about__` que foi removido).
> Usar `bcrypt` diretamente evita esta fragilidade.

> **Decisão — bcrypt é intencionalmente lento (~100ms por hash):**
> Isso parece mau, mas significa que um atacante a tentar quebrar um hash
> vazado tem de esperar 100ms por tentativa em vez de nanosegundos. Quebrar um
> milhão de hashes passa de segundos para anos.

```python
def create_access_token(data: dict) -> str:
    payload = data.copy()
    payload["exp"] = datetime.now(timezone.utc) + timedelta(minutes=settings.jwt_expiration_minutes)
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)

def create_refresh_token(data: dict) -> str:
    payload = data.copy()
    payload["exp"] = datetime.now(timezone.utc) + timedelta(days=settings.refresh_token_expire_days)
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)

def decode_token(token: str) -> dict:
    return jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
```

O que está dentro de um JWT:

```json
{
  "sub": "01KP7XSEVGPGPK4HV69P7TENZG",
  "role": "client",
  "exp": 1776236012
}
```

`sub` (subject) é o ID do utilizador.

> **Decisão — JWT carrega o ID, não o email:**
> Emails podem mudar — IDs não. Um token com email ficaria inválido se o
> utilizador mudasse o email.

`exp` é um timestamp Unix. `decode_token` lança automaticamente um erro se `exp`
estiver no passado.

> **Decisão — duas funções separadas para access vs refresh:**
> A única diferença é o TTL. Ter duas funções torna isso explícito e evita criar
> acidentalmente um access token de 7 dias.

---

## 3. Schemas — `app/schemas/`

### `schemas/user.py`

```python
class UserPublic(BaseModel):
    id: str
    name: str
    email: str
    role: RoleEnum

    model_config = ConfigDict(from_attributes=True)
```

> **Decisão — `UserPublic` separado do modelo SQLAlchemy:**
> O modelo de banco tem `password_hash`, `accepted_terms_at`, `anonymized_at` e
> outros campos internos. Nunca os deves expor numa resposta. `UserPublic` é uma
> whitelist — só estes quatro campos chegam ao frontend.

`from_attributes=True` permite ao Pydantic ler de objetos SQLAlchemy (acedendo
atributos como `user.id`) em vez de apenas de dicionários.

### `schemas/auth.py`

```python
class RegisterRequest(BaseModel):
    name: str
    email: EmailStr
    password: str
    role: RoleEnum
    phone: str | None = None
    accepted_terms: bool

    @field_validator("password")
    @classmethod
    def password_min_length(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("A senha deve ter no mínimo 8 caracteres")
        return v

    @field_validator("accepted_terms")
    @classmethod
    def must_accept_terms(cls, v: bool) -> bool:
        if not v:
            raise ValueError("Você deve aceitar os termos de uso")
        return v
```

> **Decisão — `EmailStr` em vez de `str` para o email:**
> `EmailStr` valida o formato do email. Requer o pacote `email-validator`
> (`pydantic[email]`). Sem ele, `"não_é_um_email"` seria aceite como válido.

> **Decisão — `@field_validator` em vez de validação no endpoint:**
> Quando um validador lança `ValueError`, o Pydantic converte-o automaticamente
> numa resposta `422 Unprocessable Entity` com mensagem descritiva. Sem
> necessidade de `if` manuais no endpoint. Validação no frontend é para UX —
> não é segurança. Qualquer pedido pode ser construído manualmente (curl, Postman,
> scripts). A validação no backend é a barreira real.

```python
class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserPublic
```

> **Decisão — incluir `user` na resposta de login:**
> O frontend precisa de saber o role do utilizador imediatamente após o login para
> decidir para onde redirecionar: um `client` vai para o fluxo de agendamento, um
> `professional` vai para o dashboard, um `store_admin` vai para o painel da loja.
> Sem o objeto user, o frontend teria de descodificar o JWT ou fazer um segundo
> pedido.

---

## 4. Lógica de negócio — `app/services/auth_service.py`

A camada de serviços tem a lógica central. Crucialmente, **nenhuma destas funções
usa `Depends()`** — recebem tudo como parâmetros normais.

```python
async def register(db: AsyncSession, data: RegisterRequest) -> User:
    result = await db.execute(
        select(User).where(
            User.email == data.email,
            User.deleted_at.is_(None),
        )
    )
    if result.scalar_one_or_none() is not None:
        raise HTTPException(status_code=409, detail="Email já cadastrado")
    ...
```

> **Decisão — `deleted_at.is_(None)` na verificação de email:**
> O projeto usa soft deletes — nenhuma linha é alguma vez removida fisicamente.
> Um utilizador "apagado" ainda tem uma linha, apenas com `deleted_at` preenchido.
> Sem este filtro, um utilizador que apagou a conta não conseguia registar-se
> novamente com o mesmo email.

> **Decisão — guardar `accepted_terms_version`:**
> O RGPD e as leis de proteção ao consumidor exigem que se prove que o utilizador
> aceitou os termos, e qual versão. Se os termos forem atualizados mais tarde,
> pode ser necessário pedir novamente aos utilizadores que aceitaram a versão
> antiga.

```python
async def login(db: AsyncSession, data: LoginRequest) -> tuple[str, str, User]:
    ...
    if user is None or not security.verify_password(data.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Credenciais inválidas")
```

> **Decisão — mesma mensagem de erro para email não encontrado e password errada:**
> Deliberado por segurança. Se retornasses "email não encontrado" para um email
> errado e "password errada" para uma password errada, um atacante conseguia
> enumerar quais emails estão registados apenas observando os erros. Com uma
> mensagem genérica, não obtém nenhuma informação.

> **Decisão — retornar `tuple[str, str, User]`:**
> A função retorna três coisas de uma vez — o access token, o refresh token, e
> o objeto user. O router precisa das três: os tokens para enviar, o user para
> construir a resposta. Um tuple evita criar uma dataclass descartável.

---

## 5. Dependências — `app/core/dependencies.py`

```python
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")

async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    credentials_exception = HTTPException(
        status_code=401,
        detail="Token inválido ou expirado",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = security.decode_token(token)
    except JWTError:
        raise credentials_exception

    user_id: str | None = payload.get("sub")
    if not user_id:
        raise credentials_exception

    result = await db.execute(
        select(User).where(
            User.id == user_id,
            User.deleted_at.is_(None),
        )
    )
    user = result.scalar_one_or_none()
    if user is None:
        raise credentials_exception

    return user
```

> **Decisão — buscar o utilizador no banco em cada pedido:**
> O JWT sozinho diz o ID do utilizador. Mas e se o utilizador foi apagado depois
> de o token ter sido emitido? O token continuaria a ser tecnicamente válido. Ir
> buscar ao banco e aplicar `deleted_at.is_(None)` resolve isto — uma conta
> apagada não consegue usar um token ainda válido.

> **Decisão — `OAuth2PasswordBearer` em vez de ler o header manualmente:**
> Lê o header `Authorization: Bearer <token>` e extrai o token. Também diz ao
> Swagger UI (`/docs`) para mostrar um cadeado e um botão "Authorize" nesse
> endpoint.

> **Decisão — `WWW-Authenticate: Bearer` no header de erro:**
> É o standard HTTP para dizer ao cliente "precisas de autenticar, e aceito
> Bearer tokens". Alguns clientes e ferramentas usam este header para solicitar
> credenciais automaticamente.

```python
def require_role(*roles: RoleEnum):
    def role_checker(
        current_user: User = Depends(get_current_user),
    ) -> User:
        if current_user.role not in roles:
            raise HTTPException(status_code=403, detail="Acesso negado")
        return current_user
    return role_checker
```

> **Decisão — `require_role` retorna uma função em vez de ser uma função direta:**
> Como os roles são parâmetros (`require_role(RoleEnum.store_admin)`), não
> hardcoded, a função exterior captura o argumento `roles` e retorna a função
> interior `role_checker` que o FastAPI vai injetar. É uma closure — `role_checker`
> "lembra" os `roles` com que foi criada.

> **Decisão — 401 vs 403 distintos:**
> - **401 Unauthorized** — "Não sei quem és." Sem token válido.
> - **403 Forbidden** — "Sei quem és, mas não podes fazer isto." Role errado.
> Usar sempre 401 perderia esta distinção semântica importante.

---

## 6. Os endpoints — `app/routers/auth.py`

```python
_COOKIE_PATH = "/api/v1/auth/refresh"
_COOKIE_MAX_AGE = settings.refresh_token_expire_days * 86400

def _set_refresh_cookie(response: Response, token: str) -> None:
    response.set_cookie(
        key="refresh_token",
        value=token,
        httponly=True,
        secure=False,     # True em produção
        samesite="strict",
        max_age=_COOKIE_MAX_AGE,
        path=_COOKIE_PATH,
    )
```

O que cada flag do cookie faz e por que importa:

| Flag | O que previne |
|------|--------------|
| `httponly=True` | JavaScript na página não consegue ler este cookie. Protege contra ataques XSS que tentam roubar tokens. |
| `secure=True` | O browser só envia o cookie via HTTPS. Previne intercepção em HTTP simples. `False` em dev porque localhost não tem HTTPS. |
| `samesite="strict"` | O browser só envia o cookie quando o pedido vem do teu próprio site. Previne ataques CSRF — um site malicioso não consegue acionar `/refresh` silenciosamente. |
| `path="/api/v1/auth/refresh"` | O browser só anexa este cookie a pedidos para esse caminho exato. |

> **Decisão — `path` do cookie restrito a `/api/v1/auth/refresh`:**
> Se o path fosse `/`, o refresh token seria enviado em todos os pedidos —
> `GET /stores`, `GET /offerings`, tudo. Isso alarga a superfície de ataque sem
> razão. Limitar ao `/api/v1/auth/refresh` significa que o token só viaja quando
> é necessário.

```python
@router.post("/register", response_model=UserPublic, status_code=201)
async def register(data: RegisterRequest, db: AsyncSession = Depends(get_db)):
    user = await auth_service.register(db, data)
    return user
```

`response_model=UserPublic` diz ao FastAPI para filtrar o objeto retornado através
de `UserPublic` antes de enviar a resposta. Mesmo que `auth_service.register`
retorne um `User` completo com `password_hash` e tudo, só os campos de `UserPublic`
saem. É uma rede de segurança.

```python
@router.post("/login", response_model=TokenResponse)
async def login(data: LoginRequest, response: Response, db: AsyncSession = Depends(get_db)):
    access_token, refresh_token, user = await auth_service.login(db, data)
    _set_refresh_cookie(response, refresh_token)
    return TokenResponse(
        access_token=access_token,
        user=UserPublic.model_validate(user),
    )
```

`response: Response` é injetado pelo FastAPI para permitir modificar a resposta
HTTP — definir headers, cookies, status codes — sem perder a capacidade de também
retornar um body.

```python
@router.post("/refresh", response_model=TokenResponse)
async def refresh(request: Request, response: Response, db: AsyncSession = Depends(get_db)):
    refresh_token = request.cookies.get("refresh_token")
    if not refresh_token:
        raise HTTPException(status_code=401, detail="Refresh token ausente")

    new_access_token, user = await auth_service.refresh(db, refresh_token)
    _set_refresh_cookie(response, refresh_token)  # re-define para renovar o TTL
    return TokenResponse(...)
```

O endpoint de refresh lê o cookie do pedido, valida-o, e emite um novo access
token. Re-define também o cookie — isto renova o TTL do cookie no browser.

> **Decisão — re-definir o cookie no refresh:**
> Sem isto, o cookie expiraria 7 dias após o login original, mesmo que o
> utilizador esteja ativo todos os dias. Re-definir o cookie renova o TTL a
> cada refresh — um utilizador ativo nunca é forçado a fazer login novamente.

```python
@router.post("/logout", status_code=204)
async def logout(response: Response):
    response.delete_cookie(
        key="refresh_token",
        path=_COOKIE_PATH,
        httponly=True,
        secure=False,
        samesite="strict",
    )
```

> **Decisão — flags idênticas no `delete_cookie` e no `set_cookie`:**
> `delete_cookie` funciona enviando um header `Set-Cookie` com `Max-Age=0`, o que
> diz ao browser para expirar imediatamente o cookie. As flags (`path`, `httponly`,
> `samesite`, `secure`) têm de ser idênticas à chamada `set_cookie` original. Se
> não corresponderem, o browser não reconhece como o mesmo cookie e ignora a
> instrução de apagar — o utilizador parece desligado no frontend mas o refresh
> token sobrevive.

> **Decisão — 204 sem body no logout:**
> HTTP 204 significa "sucesso, sem conteúdo". O logout não precisa de retornar
> nada. Retornar `{}` funcionaria tecnicamente, mas 204 é o status semanticamente
> correto.

---

## 7. Ponto de entrada — `app/main.py`

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

> **Decisão — `allow_credentials=True` é obrigatório com cookies:**
> Sem isto, o browser remove cookies dos pedidos cross-origin. Como o refresh
> token vive num cookie, esta configuração é obrigatória. O trade-off: com
> `allow_credentials=True` não podes usar `allow_origins=["*"]` — os browsers
> rejeitam essa combinação por razões de segurança.

```python
app.include_router(auth_router.router, prefix="/api/v1")
```

O router define o seu próprio prefix (`/auth`) e o `main.py` adiciona `/api/v1`
por cima. O prefixo `v1` permite versionar a API mais tarde — se forem feitas
alterações incompatíveis, cria-se `/api/v2` sem remover a v1, para que clientes
antigos não se partam.

---

## 8. Por que esta estrutura em camadas?

O código está dividido em quatro camadas — router, service, security, schema —
e não é apenas preferência de organização. Cada camada tem um trabalho específico:

| Camada | Trabalho | Conhece |
|--------|----------|---------|
| `schemas/` | Define shapes de dados, valida input | Pydantic, nada mais |
| `core/security.py` | Operações criptográficas | bcrypt, bibliotecas JWT |
| `services/` | Lógica de negócio e queries ao banco | SQLAlchemy, schemas, security |
| `routers/` | HTTP: parseia pedidos, define cookies, retorna respostas | FastAPI, services, schemas |

> **Decisão — services recebem `db: AsyncSession` como parâmetro, não via `Depends`:**
> Isto significa que podes chamá-los em testes sem iniciar uma app FastAPI — basta
> passar uma sessão de banco diretamente. Services que dependem de `Depends()` só
> podem correr dentro de um contexto de pedido.

---

## 9. O fluxo de tokens do início ao fim

```
Utilizador abre a app → frontend chama POST /auth/refresh
  ↓ sem cookie ainda → 401
  ↓ frontend mostra página de login

Utilizador submete email + password → POST /auth/login
  ↓ service procura utilizador no banco
  ↓ service verifica hash bcrypt
  ↓ service cria access token (15min) + refresh token (7 dias)
  ↓ router: access token vai no body JSON
  ↓ router: refresh token vai no header Set-Cookie (httpOnly)
  ↓ frontend guarda access token em memória (Zustand)
  ↓ browser guarda refresh token no cookie automaticamente

Utilizador navega → frontend envia access token no header Authorization
  ↓ get_current_user() descodifica-o, encontra utilizador no banco, retorna-o
  ↓ endpoint corre normalmente

15 minutos passam → access token expira
  ↓ próxima chamada à API retorna 401
  ↓ interceptor Axios do frontend apanha o 401
  ↓ frontend chama POST /auth/refresh (cookie enviado automaticamente)
  ↓ service valida refresh token, emite novo access token
  ↓ frontend repete o pedido original com o novo token
  ↓ o utilizador nunca dá conta de nada

Utilizador clica em logout → POST /auth/logout
  ↓ router limpa o cookie via Set-Cookie: Max-Age=0
  ↓ frontend limpa o store Zustand
  ↓ sem cookie → próxima chamada a refresh retorna 401 → página de login
```
