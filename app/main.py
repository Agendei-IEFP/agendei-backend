from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from starlette.responses import JSONResponse

from app.core.config import settings
from app.limiter.limiter import limiter
from app.routers import auth as auth_router
from app.routers.stores import router as stores_router
from app.routers.professionals import router as professionals_router, professional_links_router
from app.routers.professional_nested import (
    professionals_router as prof_endpoints_router,
    prof_store_router,
    offerings_router,
    schedules_router,
)
from app.routers.appointments import router as appointments_router
from app.routers.invites import router as invites_router
from app.routers.me import router as me_router
from app.routers.notifications import router as notification_router
from app.worker.celery_app import celery  # noqa: F401
app = FastAPI(
    title="Agendei API",
    description="Sistema de agendamentos para salões",
    version="0.4.0",
)
app.state.limiter = limiter
app.add_middleware(SlowAPIMiddleware)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.exception_handler(RateLimitExceeded)
async def custom_exception_handler(request: Request, exc: RateLimitExceeded):
    return JSONResponse(
        status_code=429,
        content={
            "detail": "Too many request. Please slow down.",
            "limit": str(exc.limit.limit),
            "route": request.url.path
        }
    )

PREFIX = "/api/v1"

app.include_router(auth_router.router,       prefix=PREFIX)
app.include_router(stores_router,            prefix=PREFIX)
app.include_router(professionals_router,     prefix=PREFIX)
app.include_router(professional_links_router, prefix=PREFIX)
app.include_router(prof_endpoints_router,    prefix=PREFIX)
app.include_router(prof_store_router,        prefix=PREFIX)
app.include_router(offerings_router,         prefix=PREFIX)
app.include_router(schedules_router,         prefix=PREFIX)
app.include_router(appointments_router,      prefix=PREFIX)
app.include_router(invites_router,           prefix=PREFIX)
app.include_router(me_router,                prefix=PREFIX)

app.include_router(notification_router,      prefix=PREFIX)