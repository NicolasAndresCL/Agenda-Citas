"""API HTTP (FastAPI): adaptador de entrada de la agenda.

Traduce JSON a llamadas de `Agenda` y los errores de dominio al contrato único
`{"error": {"codigo", "mensaje", "detalle"}}`. Las rutas no arman respuestas de error a mano:
lanzan, y los manejadores de `registrar_manejadores` responden. `/livez` no toca la base (la
usa la sonda de vida del contenedor); `/healthz` sí (la sonda de preparación).

Autor: Nicolás Cano Leal
Fecha: 12 de noviembre 2026
"""

from datetime import date, time
from typing import Annotated, Any

from fastapi import APIRouter, Depends, FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from agenda_citas.application.agenda import Agenda
from agenda_citas.domain.entidades import Cita, FranjaHoraria, Paciente, Profesional
from agenda_citas.domain.excepciones import (
    BloqueNoDisponible,
    DatosInvalidos,
    ErrorDominio,
    PacienteNoEncontrado,
    ProfesionalNoEncontrado,
)

# El dominio no conoce HTTP: el estado de cada error se decide aquí.
ESTADO_HTTP: dict[type[ErrorDominio], int] = {
    BloqueNoDisponible: 409,
    ProfesionalNoEncontrado: 404,
    PacienteNoEncontrado: 404,
    DatosInvalidos: 422,
}


# --- esquemas de entrada y salida ------------------------------------------------------------
class ProfesionalIn(BaseModel):
    nombre: str = Field(max_length=120)
    especialidad: str = Field(max_length=120)


class PacienteIn(BaseModel):
    rut: str = Field(max_length=20)
    nombre: str = Field(max_length=120)


class FranjaIn(BaseModel):
    fecha: date
    hora_inicio: time
    hora_fin: time


class CitaIn(BaseModel):
    paciente_id: int
    profesional_id: int
    fecha: date
    hora: time


class FranjaOut(BaseModel):
    fecha: date
    hora_inicio: str
    hora_fin: str


class ProfesionalOut(BaseModel):
    id: int
    nombre: str
    especialidad: str
    franjas: list[FranjaOut]


class PacienteOut(BaseModel):
    id: int
    rut: str
    nombre: str


class CitaOut(BaseModel):
    id: int | None
    paciente: PacienteOut
    profesional_id: int
    profesional: str
    fecha: date
    hora: str
    estado: str


def _hhmm(hora: time) -> str:
    return hora.strftime("%H:%M")


def _franja(f: FranjaHoraria) -> FranjaOut:
    return FranjaOut(fecha=f.fecha, hora_inicio=_hhmm(f.hora_inicio), hora_fin=_hhmm(f.hora_fin))


def _profesional(p: Profesional) -> ProfesionalOut:
    return ProfesionalOut(
        id=p.id,
        nombre=p.nombre,
        especialidad=p.especialidad,
        franjas=[_franja(f) for f in p.franjas],
    )


def _paciente(p: Paciente) -> PacienteOut:
    return PacienteOut(id=p.id, rut=p.rut, nombre=p.nombre)


def _cita(c: Cita) -> CitaOut:
    return CitaOut(
        id=c.id,
        paciente=_paciente(c.paciente),
        profesional_id=c.profesional.id,
        profesional=c.profesional.nombre,
        fecha=c.fecha,
        hora=_hhmm(c.hora),
        estado=c.estado.value,
    )


# --- dependencias y rutas --------------------------------------------------------------------
def obtener_agenda(request: Request) -> Agenda:
    return request.app.state.agenda


AgendaDep = Annotated[Agenda, Depends(obtener_agenda)]


def construir_router() -> APIRouter:
    router = APIRouter()

    @router.post("/profesionales", status_code=201, response_model=ProfesionalOut)
    def registrar_profesional(datos: ProfesionalIn, agenda: AgendaDep) -> ProfesionalOut:
        return _profesional(agenda.registrar_profesional(datos.nombre, datos.especialidad))

    @router.get("/profesionales", response_model=list[ProfesionalOut])
    def listar_profesionales(agenda: AgendaDep) -> list[ProfesionalOut]:
        return [_profesional(p) for p in agenda.listar_profesionales()]

    @router.post(
        "/profesionales/{id_profesional}/franjas", status_code=201, response_model=FranjaOut
    )
    def registrar_franja(id_profesional: int, datos: FranjaIn, agenda: AgendaDep) -> FranjaOut:
        franja = agenda.registrar_franja(
            id_profesional, datos.fecha, datos.hora_inicio, datos.hora_fin
        )
        return _franja(franja)

    @router.post("/pacientes", status_code=201, response_model=PacienteOut)
    def registrar_paciente(datos: PacienteIn, agenda: AgendaDep) -> PacienteOut:
        return _paciente(agenda.registrar_paciente(datos.rut, datos.nombre))

    @router.get("/pacientes", response_model=list[PacienteOut])
    def listar_pacientes(agenda: AgendaDep) -> list[PacienteOut]:
        return [_paciente(p) for p in agenda.listar_pacientes()]

    @router.post("/citas", status_code=201, response_model=CitaOut)
    def agendar_cita(datos: CitaIn, agenda: AgendaDep) -> CitaOut:
        cita = agenda.agendar_cita(datos.paciente_id, datos.profesional_id, datos.fecha, datos.hora)
        return _cita(cita)

    @router.get("/citas", response_model=list[CitaOut])
    def listar_citas(agenda: AgendaDep) -> list[CitaOut]:
        return [_cita(c) for c in agenda.listar_citas()]

    return router


def _respuesta_error(estado: int, codigo: str, mensaje: str, detalle: Any) -> JSONResponse:
    cuerpo = {"error": {"codigo": codigo, "mensaje": mensaje, "detalle": detalle}}
    return JSONResponse(status_code=estado, content=cuerpo)


def registrar_manejadores(app: FastAPI) -> None:
    """Un único lugar traduce excepciones al contrato de error."""

    @app.exception_handler(ErrorDominio)
    async def _dominio(_: Request, error: ErrorDominio) -> JSONResponse:
        estado = ESTADO_HTTP.get(type(error), 400)
        return _respuesta_error(estado, error.codigo, error.mensaje, error.detalle)

    @app.exception_handler(RequestValidationError)
    async def _validacion(_: Request, error: RequestValidationError) -> JSONResponse:
        campos = [
            {"campo": ".".join(str(p) for p in e["loc"][1:]), "problema": e["msg"]}
            for e in error.errors()
        ]
        return _respuesta_error(
            422, "SOLICITUD_INVALIDA", "La solicitud no cumple el formato esperado.", campos
        )

    @app.exception_handler(Exception)
    async def _inesperado(_: Request, __: Exception) -> JSONResponse:
        return _respuesta_error(500, "ERROR_INTERNO", "Error interno del servidor.", None)
