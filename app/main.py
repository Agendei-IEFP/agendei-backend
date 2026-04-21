from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.routers import auth as auth_router
from app.routers.lojas import router as lojas_router
from app.routers.profissionais import router as profissionais_router
from app.routers.servicos_horarios import servicos_router, horarios_router
from app.routers.agendamentos import router as agendamentos_router

app = FastAPI(
    title="Agendei API",
    description="Sistema de agendamentos para salões e clínicas",
    version="0.3.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

PREFIX = "/api/v1"

app.include_router(auth_router.router,      prefix=PREFIX)
app.include_router(lojas_router,            prefix=PREFIX)
app.include_router(profissionais_router,    prefix=PREFIX)
app.include_router(servicos_router,         prefix=PREFIX)
app.include_router(horarios_router,         prefix=PREFIX)
app.include_router(agendamentos_router,     prefix=PREFIX)