from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.core.config import settings
from app.db import create_db_and_tables
from app.routers import (
    auth,
    campanhas,
    clientes,
    comercial,
    configuracoes,
    empresas,
    financeiro,
    health,
    integracoes,
    juridico,
    notificacoes,
    portal,
    web,
)
from app.services.bootstrap_admin import ensure_seed_admin

app = FastAPI(title=settings.app_name)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def on_startup() -> None:
    create_db_and_tables()
    ensure_seed_admin()


app.include_router(health.router)
app.include_router(auth.router)
app.include_router(empresas.router)
app.include_router(clientes.router)
app.include_router(financeiro.router)
app.include_router(comercial.router)
app.include_router(juridico.router)
app.include_router(campanhas.router)
app.include_router(integracoes.router)
app.include_router(portal.router)
app.include_router(notificacoes.router)
app.include_router(configuracoes.router)
app.include_router(web.router)
app.mount("/static", StaticFiles(directory="app/static"), name="static")
