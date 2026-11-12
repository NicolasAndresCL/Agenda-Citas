"""Aplicación NiceGUI: cabecera, menú lateral y cuatro vistas enrutadas con `ui.sub_pages`.

La página raíz se pasa a `ui.run(raiz, ...)` y no se decora con `@ui.page("/")`: así actúa de
respaldo para cualquier URL (recargar en /citas no devuelve 404). Arranque:
`python -m frontend.app`, puerto 8085 (el 8080 es de Jenkins). Estética sobria: tonos neutros,
sin colores llamativos.

Autor: Nicolás Cano Leal
Fecha: 12 de noviembre 2026
"""

from nicegui import ui

from frontend.cliente import ClienteAgenda
from frontend.config import ConfiguracionUI
from frontend.paginas import vista_agendar, vista_citas, vista_pacientes, vista_profesionales

CONFIG = ConfiguracionUI()
CLIENTE = ClienteAgenda(CONFIG.api_url, CONFIG.http_timeout_s)

MENU = [
    ("/", "Profesionales"),
    ("/pacientes", "Pacientes"),
    ("/agendar", "Agendar cita"),
    ("/citas", "Citas"),
]


def raiz() -> None:
    ui.colors(primary="#37474f", secondary="#546e7a", accent="#455a64")
    with ui.header().classes("items-center bg-primary"):
        ui.label("Agenda de citas").classes("text-h6")
    with ui.left_drawer(fixed=True).classes("bg-grey-2"), ui.column().classes("gap-1"):
        for ruta, titulo in MENU:
            ui.link(titulo, ruta).classes("text-primary no-underline text-body1")
    with ui.column().classes("w-full p-4 gap-4"):
        ui.sub_pages(
            {
                "/": lambda: vista_profesionales(CLIENTE),
                "/pacientes": lambda: vista_pacientes(CLIENTE),
                "/agendar": lambda: vista_agendar(CLIENTE),
                "/citas": lambda: vista_citas(CLIENTE),
            }
        ).classes("w-full")


if __name__ in {"__main__", "__mp_main__"}:
    ui.run(
        raiz,
        host=CONFIG.frontend_host,
        port=CONFIG.frontend_port,
        title="Agenda de citas",
        reload=False,
        show=False,
    )
