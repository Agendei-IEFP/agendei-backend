from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.routers import auth, appointments, invites, me, services
from app.routers.professionals import router as professionals_router
from app.routers.stores import router as stores_router

app = FastAPI(title="Agendei API", version="0.5.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=[""],
    allow_headers=[""],
)

PREFIX = "/api/v1"

app.include_router(auth.router,            prefix=PREFIX)
app.include_router(stores_router,          prefix=PREFIX)
app.include_router(professionals_router,   prefix=PREFIX)
app.include_router(appointments.router,    prefix=PREFIX)
app.include_router(invites.router,         prefix=PREFIX)
app.include_router(me.router,              prefix=PREFIX)
app.include_router(services.router,        prefix=PREFIX)