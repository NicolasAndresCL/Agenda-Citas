"""Arranque de la API: `python -m agenda_citas` (uvicorn sirviendo `crear_app`).

Autor: Nicolás Cano Leal
Fecha: 12 de noviembre 2026
"""

import uvicorn

from agenda_citas.infra.config import Configuracion
from agenda_citas.main import crear_app

if __name__ == "__main__":
    config = Configuracion()
    uvicorn.run(crear_app(config), host=config.api_host, port=config.api_port)
