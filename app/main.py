from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.routers import auth as auth_router
from app.routers.stores import router as stores_router
from app.routers.professionals import router as professionals_router
from app.routers.professional_nested import (
    professionals_router as prof_endpoints_router,
    schedules_router,
)
from app.routers.appointments import router as appointments_router
from app.routers.me import router as me_router
from app.routers.services import router as services_router

app = FastAPI(
    title="Agendei API",
    description="Sistema de agendamentos para salões",
    version="0.5.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

PREFIX = "/api/v1"

app.include_router(auth_router.router,    prefix=PREFIX)
app.include_router(stores_router,         prefix=PREFIX)
app.include_router(professionals_router,  prefix=PREFIX)
app.include_router(prof_endpoints_router, prefix=PREFIX)
app.include_router(schedules_router,      prefix=PREFIX)
app.include_router(appointments_router,   prefix=PREFIX)
app.include_router(me_router,             prefix=PREFIX)
app.include_router(services_router,       prefix=PREFIX)
