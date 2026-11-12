"""Raíz de composición: único lugar que conoce las implementaciones concretas.

`crear_app` elige el repositorio según la configuración (Postgres o memoria), lo inyecta en
`Agenda` y monta la API. Las pruebas pasan su propio repositorio para no tocar ninguna base.
Si el almacenamiento es Postgres y `APLICAR_MIGRACIONES` está activa, aplica las migraciones
al arrancar (idempotente). `/livez` no consulta la base; `/healthz` sí y responde 503 si no
contesta.

Autor: Nicolás Cano Leal
Fecha: 12 de noviembre 2026
"""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.responses import JSONResponse

from agenda_citas import __version__
from agenda_citas.adapters.inbound.api import construir_router, registrar_manejadores
from agenda_citas.adapters.outbound.memoria import RepositorioMemoria
from agenda_citas.adapters.outbound.postgres import RepositorioPostgres
from agenda_citas.application.agenda import Agenda
from agenda_citas.domain.puertos import RepositorioAgenda
from agenda_citas.infra.config import Configuracion
from agenda_citas.infra.migrador import aplicar_migraciones


def _repositorio(config: Configuracion) -> RepositorioAgenda:
    if config.almacenamiento == "memoria":
        return RepositorioMemoria()
    if not config.database_url:
        raise RuntimeError("DATABASE_URL es obligatoria cuando ALMACENAMIENTO=postgres.")
    return RepositorioPostgres(config.database_url)


def crear_app(
    config: Configuracion | None = None, repositorio: RepositorioAgenda | None = None
) -> FastAPI:
    config = config or Configuracion()
    repo = repositorio or _repositorio(config)

    @asynccontextmanager
    async def ciclo_de_vida(_: FastAPI) -> AsyncIterator[None]:
        if (
            repositorio is None
            and config.almacenamiento == "postgres"
            and config.aplicar_migraciones
        ):
            aplicar_migraciones(config.database_url, config.migrations_dir)
        yield

    app = FastAPI(title="Agenda de citas", version=__version__, lifespan=ciclo_de_vida)
    app.state.agenda = Agenda(repo)
    registrar_manejadores(app)
    app.include_router(construir_router(), prefix="/api")

    @app.get("/livez")
    def livez() -> dict[str, str]:
        return {"estado": "vivo", "version": __version__}

    @app.get("/healthz")
    def healthz() -> JSONResponse:
        try:
            app.state.agenda.comprobar()
        except Exception:
            return JSONResponse(status_code=503, content={"estado": "sin_base_de_datos"})
        return JSONResponse(content={"estado": "ok", "version": __version__})

    return app
