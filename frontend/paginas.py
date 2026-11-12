"""Páginas de la interfaz: Profesionales, Pacientes, Agendar cita y Citas.

Cada vista es una función que construye su contenido; `ui.sub_pages` las enruta por URL. Todo
dato viene de `ClienteAgenda`; si la API no responde se avisa con `ui.notify` y la página sigue
viva. No usa `from __future__ import annotations`: sub_pages inyecta por la anotación real.

Autor: Nicolás Cano Leal
Fecha: 12 de noviembre 2026
"""

from collections.abc import Awaitable
from datetime import date
from typing import Any

from nicegui import ui

from frontend.cliente import ApiNoDisponible, ClienteAgenda, ErrorApi


async def _intentar(llamada: Awaitable[Any], exito: str | None = None) -> Any:
    """Ejecuta una llamada a la API; notifica el error y devuelve None si falló."""
    try:
        resultado = await llamada
    except ErrorApi as error:
        ui.notify(error.mensaje, type="negative")
        return None
    except ApiNoDisponible:
        ui.notify("La API no responde. Intenta de nuevo en unos segundos.", type="warning")
        return None
    if exito:
        ui.notify(exito, type="positive")
    return resultado


def _franjas_texto(profesional: dict[str, Any]) -> str:
    texto = "; ".join(
        f"{f['fecha']} {f['hora_inicio']}-{f['hora_fin']}" for f in profesional["franjas"]
    )
    return texto or "sin franjas"


def _col(nombre: str, etiqueta: str) -> dict[str, Any]:
    return {"name": nombre, "label": etiqueta, "field": nombre, "align": "left"}


def vista_profesionales(cliente: ClienteAgenda) -> None:
    ui.label("Profesionales").classes("text-h5")
    with ui.card().classes("w-full max-w-4xl"):
        ui.label("Registrar profesional").classes("text-subtitle1")
        with ui.row().classes("items-end gap-4"):
            nombre = ui.input("Nombre").mark("prof-nombre")
            especialidad = ui.input("Especialidad").mark("prof-especialidad")
            ui.button("Registrar", on_click=lambda: registrar()).mark("prof-registrar")

    with ui.card().classes("w-full max-w-4xl"):
        ui.label("Agregar franja horaria").classes("text-subtitle1")
        with ui.row().classes("items-end gap-4"):
            seleccion = ui.select({}, label="Profesional").classes("w-64").mark("franja-prof")
            fecha = ui.input("Fecha", value=date.today().isoformat()).props("type=date")
            inicio = ui.input("Desde", value="09:00").props("type=time")
            fin = ui.input("Hasta", value="13:00").props("type=time")
            ui.button("Agregar franja", on_click=lambda: franja()).mark("franja-agregar")

    tabla = ui.table(
        columns=[
            _col("id", "N.º"),
            _col("nombre", "Nombre"),
            _col("especialidad", "Especialidad"),
            _col("franjas", "Franjas"),
        ],
        rows=[],
        row_key="id",
    ).classes("w-full")

    async def cargar() -> None:
        datos = await _intentar(cliente.listar_profesionales())
        if datos is None:
            return
        tabla.rows = [{**p, "franjas": _franjas_texto(p)} for p in datos]
        tabla.update()
        seleccion.set_options({p["id"]: f"{p['nombre']} ({p['especialidad']})" for p in datos})

    async def registrar() -> None:
        if await _intentar(
            cliente.registrar_profesional(nombre.value or "", especialidad.value or ""),
            "Profesional registrado",
        ):
            nombre.value = especialidad.value = ""
            await cargar()

    async def franja() -> None:
        if seleccion.value is None:
            ui.notify("Elige un profesional.", type="warning")
            return
        if await _intentar(
            cliente.registrar_franja(seleccion.value, fecha.value, inicio.value, fin.value),
            "Franja registrada",
        ):
            await cargar()

    ui.timer(0.1, cargar, once=True)


def vista_pacientes(cliente: ClienteAgenda) -> None:
    ui.label("Pacientes").classes("text-h5")
    with ui.card().classes("w-full max-w-4xl"):
        ui.label("Registrar paciente").classes("text-subtitle1")
        with ui.row().classes("items-end gap-4"):
            rut = ui.input("RUT", placeholder="12.345.678-5").mark("pac-rut")
            nombre = ui.input("Nombre").mark("pac-nombre")
            ui.button("Registrar", on_click=lambda: registrar()).mark("pac-registrar")

    tabla = ui.table(
        columns=[_col("id", "N.º"), _col("rut", "RUT"), _col("nombre", "Nombre")],
        rows=[],
        row_key="id",
    ).classes("w-full")

    async def cargar() -> None:
        datos = await _intentar(cliente.listar_pacientes())
        if datos is not None:
            tabla.rows = datos
            tabla.update()

    async def registrar() -> None:
        if await _intentar(
            cliente.registrar_paciente(rut.value or "", nombre.value or ""), "Paciente registrado"
        ):
            rut.value = nombre.value = ""
            await cargar()

    ui.timer(0.1, cargar, once=True)


def vista_agendar(cliente: ClienteAgenda) -> None:
    ui.label("Agendar cita").classes("text-h5")
    with ui.card().classes("w-full max-w-4xl"), ui.column().classes("gap-3"):
        paciente = ui.select({}, label="Paciente").classes("w-80").mark("cita-paciente")
        profesional = ui.select({}, label="Profesional").classes("w-80").mark("cita-prof")
        with ui.row().classes("gap-4"):
            fecha = ui.input("Fecha", value=date.today().isoformat()).props("type=date")
            hora = ui.input("Hora", value="10:00").props("type=time")
        ui.button("Solicitar cita", on_click=lambda: solicitar()).mark("cita-solicitar")
        resultado = ui.label("").classes("text-subtitle1").mark("cita-resultado")

    async def cargar() -> None:
        pacientes = await _intentar(cliente.listar_pacientes())
        profesionales = await _intentar(cliente.listar_profesionales())
        if pacientes is not None:
            paciente.set_options({p["id"]: f"{p['nombre']} ({p['rut']})" for p in pacientes})
        if profesionales is not None:
            profesional.set_options(
                {p["id"]: f"{p['nombre']} ({p['especialidad']})" for p in profesionales}
            )

    async def solicitar() -> None:
        if paciente.value is None or profesional.value is None:
            ui.notify("Elige un paciente y un profesional.", type="warning")
            return
        try:
            await cliente.agendar_cita(paciente.value, profesional.value, fecha.value, hora.value)
        except ErrorApi as error:
            texto = (
                "Bloque no disponible" if error.codigo == "BLOQUE_NO_DISPONIBLE" else error.mensaje
            )
            resultado.text = texto
            ui.notify(texto, type="negative")
        except ApiNoDisponible:
            ui.notify("La API no responde. Intenta de nuevo en unos segundos.", type="warning")
        else:
            resultado.text = "Cita registrada"
            ui.notify("Cita registrada", type="positive")

    ui.timer(0.1, cargar, once=True)


def vista_citas(cliente: ClienteAgenda) -> None:
    ui.label("Citas").classes("text-h5")
    tabla = ui.table(
        columns=[
            _col("fecha", "Fecha"),
            _col("hora", "Hora"),
            _col("profesional", "Profesional"),
            _col("paciente", "Paciente"),
            _col("estado", "Estado"),
        ],
        rows=[],
        row_key="id",
    ).classes("w-full")

    async def cargar() -> None:
        datos = await _intentar(cliente.listar_citas())
        if datos is not None:
            tabla.rows = [{**c, "paciente": c["paciente"]["nombre"]} for c in datos]
            tabla.update()

    ui.timer(0.1, cargar, once=True)
