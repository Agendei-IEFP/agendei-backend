# Phase 2 — Authentication Guide

This guide explains everything built in Phase 2 of the backend. It assumes you understand basic web concepts (HTTP, cookies, passwords) but not necessarily how FastAPI or this project works internally.

---

## The Problem This Phase Solves

After Phase 1, the database existed but anyone could call any endpoint and do anything. There was no concept of "who is making this request" or "is this person allowed to do this."

Authentication answers: **who are you?**
Authorization answers: **what are you allowed to do?**

Phase 2 builds both.

---

## The Big Picture — How Auth Works Here

The system uses two tokens:

**Access token** — a short-lived JWT (15 minutes). The frontend stores it in memory (a JavaScript variable). It's sent in the `Authorization` header on every API request.

**Refresh token** — a long-lived JWT (7 days). Stored in an httpOnly cookie, which means JavaScript can't read it — only the browser sends it automatically. It's only used to get a new access token when the old one expires.

Think of it like a building security system:
- The **access token** is your daily visitor badge — valid for a few hours, lets you through most doors.
- The **refresh token** is the master key you keep in a locked safe — you only use it to get a new visitor badge, never to open doors directly.

This split exists because:
- If someone steals your access token, it expires in 15 minutes and becomes useless.
- If someone steals your refresh token... that's more serious, but the cookie flags (`httpOnly`, `SameSite=Strict`) make it very hard to steal in the first place.

---

## File Map

```
backend/
├── .env                          ← environment variables (secrets, config)
└── app/
    ├── core/
    │   ├── config.py             ← reads .env into Python
    │   ├── security.py           ← password hashing, JWT creation/decoding
    │   └── dependencies.py       ← get_current_user, require_role
    ├── schemas/
    │   ├── usuario.py            ← what a user looks like in API responses
    │   └── auth.py               ← request/response shapes for auth endpoints
    ├── services/
    │   └── auth_service.py       ← business logic (register, login, refresh)
    ├── routers/
    │   └── auth.py               ← the actual HTTP endpoints
    └── main.py                   ← app entry point, wires everything together
```

---

## 1. Environment Variables — `.env`

```
JWT_SECRET=7625d894fc30f...      # secret key used to sign tokens
JWT_ALGORITHM=HS256              # signing algorithm
JWT_EXPIRATION_MINUTES=15        # access token lives 15 minutes
REFRESH_TOKEN_EXPIRE_DAYS=7      # refresh token lives 7 days
ALLOWED_ORIGINS=["http://localhost:5173"]   # which frontends can call the API
CURRENT_TERMS_VERSION=1.0        # version of terms of service users accept
```

**Why a `JWT_SECRET`?** JWTs are not encrypted — anyone can decode them and read the contents. But they are *signed*. The signature proves the token was created by your server and hasn't been tampered with. The secret is what makes the signature trustworthy. If the secret leaks, attackers can forge valid tokens.

**Why `ALLOWED_ORIGINS` instead of `"*"`?** CORS (Cross-Origin Resource Sharing) is a browser security mechanism. When the frontend on `localhost:5173` calls the API on `localhost:8000`, the browser first checks: "is this API willing to talk to this frontend?" The API answers by listing allowed origins. Using `"*"` (any origin) with cookies is actually rejected by browsers — you have to be explicit.

---

## 2. Settings — `app/core/config.py`

```python
class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env")

    jwt_secret: str
    jwt_algorithm: str
    jwt_expiration_minutes: int
    refresh_token_expire_days: int
    allowed_origins: list[str]
    current_terms_version: str
```

**What this does:** Pydantic reads the `.env` file and maps each variable to a typed Python field. If a variable is missing or the wrong type, the app crashes immediately on startup with a clear error — not silently later when the field is first accessed.

**Note about `list[str]`:** Pydantic-settings expects list values in the `.env` file as JSON: `ALLOWED_ORIGINS=["http://localhost:5173"]`. A plain comma-separated string will fail to parse.

---

## 3. Password Hashing and JWTs — `app/core/security.py`

```python
import bcrypt
from jose import jwt

def hash_password(plain: str) -> str:
    return bcrypt.hashpw(plain.encode(), bcrypt.gensalt()).decode()

def verify_password(plain: str, hashed: str) -> bool:
    return bcrypt.checkpw(plain.encode(), hashed.encode())
```

**Why not store passwords directly?** If the database leaks, attackers get every user's password — and since people reuse passwords, they now own those users' accounts everywhere. Hashing transforms `"senha123"` into something like `"$2b$12$ZAwiv9..."` that can't be reversed. The only way to check a password is to hash it again and compare.

**Why bcrypt specifically?** bcrypt is intentionally slow — it takes ~100ms to hash one password. That sounds bad, but it means an attacker trying to crack a leaked hash has to wait 100ms per guess instead of nanoseconds. Cracking a million hashes goes from seconds to years.

**Why not use `passlib`?** `passlib` is a popular library that wraps bcrypt, but it broke with bcrypt versions 4.x and above (it looked for an `__about__` attribute that was removed). Using `bcrypt` directly sidesteps this fragility.

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

**What's inside a JWT?** A JWT is three base64-encoded sections separated by dots: header, payload, signature. The payload here looks like:

```json
{
  "sub": "01KP7XSEVGPGPK4HV69P7TENZG",
  "role": "cliente",
  "exp": 1776236012
}
```

`sub` (subject) is the user's ID. **It carries the ID, not the email**, because emails can change — IDs can't.

`exp` is a Unix timestamp. `decode_token` automatically raises an error if `exp` is in the past.

**Why two separate functions for access vs refresh?** The only difference is the TTL. Having two functions makes it explicit and prevents accidentally creating a 7-day access token.

---

## 4. Schemas — `app/schemas/`

Schemas define the shape of data going in and out of the API. They are Pydantic models — they validate, coerce, and document the data contract.

### `schemas/usuario.py`

```python
class UsuarioPublic(BaseModel):
    id: str
    nome: str
    email: str
    role: RoleEnum

    model_config = ConfigDict(from_attributes=True)
```

**Why not just return the full `Usuario` model?** The database model has `senha_hash`, `accepted_terms_at`, `anonymized_at`, and other internal fields. You never want to expose these in a response. `UsuarioPublic` is a whitelist — only these four fields go to the frontend.

**What is `from_attributes=True`?** By default Pydantic only reads data from dictionaries. `from_attributes=True` lets it read from SQLAlchemy model objects too, accessing fields as attributes (`usuario.id`) instead of keys (`data["id"]`).

### `schemas/auth.py`

```python
class RegisterRequest(BaseModel):
    nome: str
    email: EmailStr
    senha: str
    role: RoleEnum
    telefone: str | None = None
    accepted_terms: bool

    @field_validator("senha")
    @classmethod
    def senha_min_length(cls, v: str) -> str:
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

**What is `EmailStr`?** A Pydantic type that validates email format. It requires the `email-validator` package to be installed (`pydantic[email]`). If you just use `str`, you'd accept `"not_an_email"` as a valid address.

**What is `@field_validator`?** A hook that runs after Pydantic parses the field. If it raises `ValueError`, Pydantic converts it into a `422 Unprocessable Entity` response with a descriptive error message. No manual `if` checks in the endpoint needed.

**Why validate `accepted_terms` instead of just checking on the frontend?** Frontend validation is for user experience, not security. Any request can be crafted manually (curl, Postman, scripts). Backend validation is the real enforcement.

```python
class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UsuarioPublic
```

**Why include `user` in the login response?** The frontend needs to know the user's role immediately after login to decide where to redirect: a `cliente` goes to the booking flow, a `profissional` goes to the dashboard, an `admin_loja` goes to the store panel. Without the user object, the frontend would have to decode the JWT itself (possible but messy) or make a second request.

---

## 5. Business Logic — `app/services/auth_service.py`

The service layer holds the core logic — what actually happens when someone registers or logs in. Critically, **none of these functions use `Depends()`** — they receive everything they need as regular parameters.

```python
async def register(db: AsyncSession, data: RegisterRequest) -> Usuario:
    result = await db.execute(
        select(Usuario).where(
            Usuario.email == data.email,
            Usuario.deleted_at.is_(None),
        )
    )
    if result.scalar_one_or_none() is not None:
        raise HTTPException(status_code=409, detail="Email já cadastrado")

    usuario = Usuario(
        ...
        senha_hash=security.hash_password(data.senha),
        accepted_terms_at=datetime.now(timezone.utc),
        accepted_terms_version=settings.current_terms_version,
    )
    db.add(usuario)
    await db.commit()
    await db.refresh(usuario)
    return usuario
```

**Why `deleted_at.is_(None)` on the email check?** The project uses soft deletes — no row is ever physically removed from the database. A "deleted" user still has a row, just with `deleted_at` set. Without this filter, a user who deleted their account couldn't register again with the same email.

**Why store `accepted_terms_version`?** GDPR and consumer protection laws require you to prove a user accepted your terms, and which version they accepted. If you update the terms later, you may need to re-ask users who accepted the old version.

**Why 409 for duplicate email?** HTTP 409 means "Conflict" — the request is valid but conflicts with existing state. It's more precise than 400 (bad request). The frontend can catch specifically 409 and show "this email is already registered."

```python
async def login(db: AsyncSession, data: LoginRequest) -> tuple[str, str, Usuario]:
    ...
    if usuario is None or not security.verify_password(data.senha, usuario.senha_hash):
        raise HTTPException(status_code=401, detail="Credenciais inválidas")
```

**Why the same error message whether the email doesn't exist or the password is wrong?** This is deliberate security design. If you returned "email not found" for a wrong email and "wrong password" for a wrong password, an attacker could enumerate which emails are registered by just trying emails and watching the error. With a single generic message, they get no information either way.

**Why `tuple[str, str, Usuario]`?** The function returns three things at once — the access token, the refresh token, and the user object. The router needs all three: the tokens to send back, the user to build the response. Returning a tuple avoids creating a throwaway dataclass.

---

## 6. Dependencies — `app/core/dependencies.py`

```python
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")

async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db),
) -> Usuario:
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
        select(Usuario).where(
            Usuario.id == user_id,
            Usuario.deleted_at.is_(None),
        )
    )
    usuario = result.scalar_one_or_none()
    if usuario is None:
        raise credentials_exception

    return usuario
```

**What is `Depends()`?** FastAPI's dependency injection. Instead of calling `get_current_user()` manually in every endpoint, you write `user = Depends(get_current_user)` in the function signature and FastAPI calls it automatically, passing the result as the argument. This is how you protect an endpoint — add the dependency and the endpoint becomes unreachable without a valid token.

**What is `OAuth2PasswordBearer`?** A helper that reads the `Authorization: Bearer <token>` header from the request and extracts the token string. It also tells the Swagger UI (`/docs`) to show a lock icon and an "Authorize" button for that endpoint.

**Why look up the user in the database on every request?** The JWT alone tells you the user's ID. But what if the user was deleted after the token was issued? The token would still be technically valid. Fetching from the database and applying `deleted_at.is_(None)` catches this — a deleted account can't use a still-valid token.

**Why `WWW-Authenticate: Bearer` in the error headers?** This is the HTTP standard for telling a client "you need to authenticate, and I accept Bearer tokens." Some clients and tools use this header to automatically prompt for credentials.

```python
def require_role(*roles: RoleEnum):
    def role_checker(
        current_user: Usuario = Depends(get_current_user),
    ) -> Usuario:
        if current_user.role not in roles:
            raise HTTPException(status_code=403, detail="Acesso negado")
        return current_user
    return role_checker
```

**What problem does `require_role` solve?** `get_current_user` only verifies that someone is logged in. `require_role` verifies they have the right permission level. Future endpoints will use it like this:

```python
# Only store admins can access this
@router.get("/admin/lojas")
async def list_stores(user = Depends(require_role(RoleEnum.admin_loja))):
    ...

# Both professionals and admins can access this
@router.get("/agendamentos")
async def list_appointments(user = Depends(require_role(RoleEnum.profissional, RoleEnum.admin_loja))):
    ...
```

**Why does `require_role` return a function instead of being a function itself?** Because the roles are parameters (`require_role(RoleEnum.admin_loja)`), not hard-coded. The outer function captures the roles argument and returns the inner `role_checker` function that FastAPI will actually inject. This is a closure — `role_checker` "remembers" the `roles` it was created with.

The difference between 401 and 403:
- **401 Unauthorized** — "I don't know who you are." No valid token.
- **403 Forbidden** — "I know who you are, but you can't do this." Wrong role.

---

## 7. The Endpoints — `app/routers/auth.py`

```python
router = APIRouter(prefix="/auth", tags=["auth"])

_COOKIE_PATH = "/api/v1/auth/refresh"
_COOKIE_MAX_AGE = settings.refresh_token_expire_days * 86400

def _set_refresh_cookie(response: Response, token: str) -> None:
    response.set_cookie(
        key="refresh_token",
        value=token,
        httponly=True,
        secure=False,     # True in production
        samesite="strict",
        max_age=_COOKIE_MAX_AGE,
        path=_COOKIE_PATH,
    )
```

**What does each cookie flag do?**

| Flag | What it prevents |
|------|-----------------|
| `httponly=True` | JavaScript on the page cannot read this cookie. Protects against XSS attacks that try to steal tokens. |
| `secure=True` | Browser only sends cookie over HTTPS. Prevents interception on plain HTTP. Set `False` in dev since localhost doesn't have HTTPS. |
| `samesite="strict"` | Browser only sends cookie when the request originated from your own site. Prevents CSRF attacks — a malicious site can't silently trigger a `/refresh` call. |
| `path="/api/v1/auth/refresh"` | Browser only attaches this cookie to requests to that exact path. Without this, the cookie would go on every single API call. |

**Why does `path` matter so much?** If the cookie path were `/`, the refresh token would be sent on every request — `GET /lojas`, `GET /servicos`, everything. That broadens the attack surface for no reason. Scoping it to `/api/v1/auth/refresh` means the token only travels when it needs to.

```python
@router.post("/register", response_model=UsuarioPublic, status_code=201)
async def register(data: RegisterRequest, db: AsyncSession = Depends(get_db)):
    usuario = await auth_service.register(db, data)
    return usuario
```

`response_model=UsuarioPublic` tells FastAPI to filter the returned object through `UsuarioPublic` before sending the response. Even if `auth_service.register` returns a full `Usuario` with `senha_hash` and everything, only the four fields in `UsuarioPublic` go out. It's a safety net.

```python
@router.post("/login", response_model=TokenResponse)
async def login(data: LoginRequest, response: Response, db: AsyncSession = Depends(get_db)):
    access_token, refresh_token, usuario = await auth_service.login(db, data)
    _set_refresh_cookie(response, refresh_token)
    return TokenResponse(
        access_token=access_token,
        user=UsuarioPublic.model_validate(usuario),
    )
```

`response: Response` is injected by FastAPI to let you modify the HTTP response — set headers, cookies, status codes — without losing the ability to also return a body. The `set_cookie` call here is what tells the browser to store the refresh token.

```python
@router.post("/refresh", response_model=TokenResponse)
async def refresh(request: Request, response: Response, db: AsyncSession = Depends(get_db)):
    refresh_token = request.cookies.get("refresh_token")
    if not refresh_token:
        raise HTTPException(status_code=401, detail="Refresh token ausente")

    new_access_token, usuario = await auth_service.refresh(db, refresh_token)
    _set_refresh_cookie(response, refresh_token)  # re-set to renew TTL
    return TokenResponse(...)
```

The refresh endpoint reads the cookie from the incoming request (`request.cookies.get()`), validates it, and issues a new access token. It also re-sets the cookie — this resets the cookie's TTL in the browser. Without this, the cookie would expire 7 days after the original login, even if the user is active every day.

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

**Important:** `delete_cookie` works by sending a `Set-Cookie` header with `Max-Age=0`, which tells the browser to immediately expire the cookie. The flags (`path`, `httponly`, `samesite`, `secure`) must be identical to the original `set_cookie` call. If they don't match, the browser doesn't recognize it as the same cookie and ignores the delete instruction — the user appears logged out on the frontend but the refresh token cookie survives.

**Why 204 and no body?** HTTP 204 means "success, no content." Logout doesn't need to return anything — there's nothing to say. Returning an empty `{}` would technically work but 204 is the semantically correct status.

---

## 8. The App Entry Point — `app/main.py`

```python
app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router.router, prefix="/api/v1")
```

**What is middleware?** Code that runs on every request before it reaches your endpoints and after the response leaves them. CORS middleware intercepts every request and adds the appropriate CORS headers to the response.

**Why `allow_credentials=True`?** Without this, the browser strips cookies from cross-origin requests. Since the refresh token lives in a cookie, this setting is mandatory. The trade-off: `allow_credentials=True` is why you can't use `allow_origins=["*"]` — browsers reject that combination for security reasons.

**What does `app.include_router(auth_router.router, prefix="/api/v1")` do?** The router defines its own prefix (`/auth`), and `main.py` adds `/api/v1` on top. The resulting paths are:
- `POST /api/v1/auth/register`
- `POST /api/v1/auth/login`
- `POST /api/v1/auth/refresh`
- `POST /api/v1/auth/logout`

The `v1` prefix lets you version your API later — if you make breaking changes, you create a `/api/v2` without removing v1, so old clients don't break.

---

## 9. Why This Layer Structure?

The code is split into four layers — router, service, security, schema — and this isn't just organization preference. Each layer has a specific job:

| Layer | Job | Knows about |
|-------|-----|-------------|
| `schemas/` | Define data shapes, validate input | Pydantic, nothing else |
| `core/security.py` | Cryptographic operations | bcrypt, JWT libraries |
| `services/` | Business logic and database queries | SQLAlchemy, schemas, security |
| `routers/` | HTTP: parse requests, set cookies, return responses | FastAPI, services, schemas |

**The key consequence:** `auth_service.py` receives a `db: AsyncSession` as a plain parameter, not via `Depends(get_db)`. This means you can call it in tests without starting a FastAPI app — just pass a database session directly. Services that depend on `Depends()` can only run inside a request context.

---

## 10. The Token Flow End-to-End

Here's what happens from the user's perspective and what's happening in the code at each step:

```
User opens app → frontend calls POST /auth/refresh
  ↓ no cookie yet → 401
  ↓ frontend shows /login page

User submits email + password → POST /auth/login
  ↓ service looks up user in DB
  ↓ service verifies bcrypt hash
  ↓ service creates access token (15min) + refresh token (7 days)
  ↓ router: access token goes in JSON body
  ↓ router: refresh token goes in Set-Cookie header (httpOnly)
  ↓ frontend stores access token in Zustand (memory)
  ↓ browser stores refresh token in cookie automatically

User navigates around → frontend sends access token in Authorization header
  ↓ get_current_user() decodes it, finds user in DB, returns user
  ↓ endpoint runs normally

15 minutes pass → access token expires
  ↓ next API call returns 401
  ↓ frontend's Axios interceptor catches 401
  ↓ frontend calls POST /auth/refresh (cookie sent automatically)
  ↓ service validates refresh token, issues new access token
  ↓ frontend retries original request with new token
  ↓ user never notices anything

User clicks logout → POST /auth/logout
  ↓ router clears cookie via Set-Cookie: Max-Age=0
  ↓ frontend clears Zustand store
  ↓ no cookie → next refresh call returns 401 → login page
```

---

## What Comes Next

Phase 2 built the authentication foundation. Every future endpoint that needs to be protected uses the tools created here:

```python
# Any future endpoint can now do this:
from app.core.dependencies import get_current_user, require_role

@router.get("/minhas-lojas")
async def my_stores(user: Usuario = Depends(require_role(RoleEnum.admin_loja))):
    # user is already fetched, validated, and role-checked
    # just write the business logic
    ...
```

Phase 3 builds on this: CRUD for lojas, profissionais, serviços, horários, agendamentos — and the availability slot algorithm.
