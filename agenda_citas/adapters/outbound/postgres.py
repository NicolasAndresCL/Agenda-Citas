"""RepositorioPostgres: implementación del puerto con psycopg 3 y SQL explícito.

Abre una conexión por operación (el volumen de una agenda no justifica un pool; ver ADR 0001).
La segunda barrera contra la doble reserva es el índice único parcial `uq_cita_activa`
(migrations/001_inicial.sql): si dos solicitudes concurrentes pasan la verificación en memoria,
Postgres rechaza la segunda con UniqueViolation y este adaptador la traduce a BloqueNoDisponible
(ADR 0002). La otra violación posible, el RUT repetido, se traduce a DatosInvalidos.

Autor: Nicolás Cano Leal
Fecha: 12 de noviembre 2026
"""

from collections.abc import Iterator
from contextlib import contextmanager
from datetime import date

import psycopg
from psycopg.errors import ForeignKeyViolation, UniqueViolation
from psycopg.rows import dict_row

from agenda_citas.domain.entidades import (
    Cita,
    EstadoCita,
    FranjaHoraria,
    Paciente,
    Profesional,
)
from agenda_citas.domain.excepciones import (
    BloqueNoDisponible,
    DatosInvalidos,
    PacienteNoEncontrado,
    ProfesionalNoEncontrado,
)

INDICE_CITA_ACTIVA = "uq_cita_activa"


class RepositorioPostgres:
    """Almacena la agenda en PostgreSQL."""

    def __init__(self, dsn: str) -> None:
        self._dsn = dsn

    @contextmanager
    def _conexion(self) -> Iterator[psycopg.Connection]:
        # `with connect()` confirma al salir sin error y revierte si hubo excepción.
        with psycopg.connect(self._dsn, row_factory=dict_row, connect_timeout=5) as conexion:
            yield conexion

    # lecturas ---------------------------------------------------------------------------------
    def obtener_profesional(self, id_profesional: int, fecha: date) -> Profesional:
        with self._conexion() as c:
            fila = c.execute(
                "SELECT id, nombre, especialidad FROM profesional WHERE id = %s", (id_profesional,)
            ).fetchone()
            if fila is None:
                raise ProfesionalNoEncontrado(
                    "No existe el profesional.", {"profesional_id": id_profesional}
                )
            profesional = Profesional(fila["id"], fila["nombre"], fila["especialidad"])
            profesional.franjas = self._franjas(c, id_profesional)
            for f in c.execute(
                "SELECT c.id, c.fecha, c.hora, p.id AS pid, p.rut, p.nombre FROM cita c"
                " JOIN paciente p ON p.id = c.paciente_id"
                " WHERE c.profesional_id = %s AND c.fecha = %s AND c.estado = 'ACTIVA'",
                (id_profesional, fecha),
            ):
                paciente = Paciente(f["pid"], f["rut"], f["nombre"])
                profesional.citas.append(
                    Cita(paciente, profesional, f["fecha"], f["hora"], EstadoCita.ACTIVA, f["id"])
                )
            return profesional

    @staticmethod
    def _franjas(c: psycopg.Connection, id_profesional: int) -> list[FranjaHoraria]:
        return [
            FranjaHoraria(f["fecha"], f["hora_inicio"], f["hora_fin"])
            for f in c.execute(
                "SELECT fecha, hora_inicio, hora_fin FROM franja_horaria"
                " WHERE profesional_id = %s ORDER BY fecha, hora_inicio",
                (id_profesional,),
            )
        ]

    def obtener_paciente(self, id_paciente: int) -> Paciente:
        with self._conexion() as c:
            fila = c.execute(
                "SELECT id, rut, nombre FROM paciente WHERE id = %s", (id_paciente,)
            ).fetchone()
        if fila is None:
            raise PacienteNoEncontrado("No existe el paciente.", {"paciente_id": id_paciente})
        return Paciente(fila["id"], fila["rut"], fila["nombre"])

    def listar_profesionales(self) -> list[Profesional]:
        with self._conexion() as c:
            filas = c.execute("SELECT id, nombre, especialidad FROM profesional ORDER BY id")
            resultado = []
            for f in filas.fetchall():
                p = Profesional(f["id"], f["nombre"], f["especialidad"])
                p.franjas = self._franjas(c, p.id)
                resultado.append(p)
            return resultado

    def listar_pacientes(self) -> list[Paciente]:
        with self._conexion() as c:
            filas = c.execute("SELECT id, rut, nombre FROM paciente ORDER BY id").fetchall()
        return [Paciente(f["id"], f["rut"], f["nombre"]) for f in filas]

    def listar_citas(self) -> list[Cita]:
        with self._conexion() as c:
            filas = c.execute(
                "SELECT c.id, c.fecha, c.hora, c.estado,"
                " p.id AS pid, p.rut, p.nombre AS pnombre,"
                " r.id AS rid, r.nombre AS rnombre, r.especialidad"
                " FROM cita c JOIN paciente p ON p.id = c.paciente_id"
                " JOIN profesional r ON r.id = c.profesional_id"
                " ORDER BY c.fecha, c.hora, c.id"
            ).fetchall()
        return [
            Cita(
                Paciente(f["pid"], f["rut"], f["pnombre"]),
                Profesional(f["rid"], f["rnombre"], f["especialidad"]),
                f["fecha"],
                f["hora"],
                EstadoCita(f["estado"]),
                f["id"],
            )
            for f in filas
        ]

    # escrituras -------------------------------------------------------------------------------
    def guardar_profesional(self, profesional: Profesional) -> Profesional:
        with self._conexion() as c:
            fila = c.execute(
                "INSERT INTO profesional (nombre, especialidad) VALUES (%s, %s) RETURNING id",
                (profesional.nombre, profesional.especialidad),
            ).fetchone()
        profesional.id = fila["id"]
        return profesional

    def guardar_paciente(self, paciente: Paciente) -> Paciente:
        try:
            with self._conexion() as c:
                fila = c.execute(
                    "INSERT INTO paciente (rut, nombre) VALUES (%s, %s) RETURNING id",
                    (paciente.rut, paciente.nombre),
                ).fetchone()
        except UniqueViolation as error:
            raise DatosInvalidos(
                "Ya existe un paciente con ese RUT.", {"rut": paciente.rut}
            ) from error
        paciente.id = fila["id"]
        return paciente

    def guardar_franja(self, id_profesional: int, franja: FranjaHoraria) -> FranjaHoraria:
        try:
            with self._conexion() as c:
                c.execute(
                    "INSERT INTO franja_horaria (profesional_id, fecha, hora_inicio, hora_fin)"
                    " VALUES (%s, %s, %s, %s)",
                    (id_profesional, franja.fecha, franja.hora_inicio, franja.hora_fin),
                )
        except ForeignKeyViolation as error:
            raise ProfesionalNoEncontrado(
                "No existe el profesional.", {"profesional_id": id_profesional}
            ) from error
        return franja

    def guardar_cita(self, cita: Cita) -> Cita:
        try:
            with self._conexion() as c:
                fila = c.execute(
                    "INSERT INTO cita (paciente_id, profesional_id, fecha, hora, estado)"
                    " VALUES (%s, %s, %s, %s, %s) RETURNING id",
                    (
                        cita.paciente.id,
                        cita.profesional.id,
                        cita.fecha,
                        cita.hora,
                        cita.estado.value,
                    ),
                ).fetchone()
        except UniqueViolation as error:
            if error.diag.constraint_name == INDICE_CITA_ACTIVA:
                raise BloqueNoDisponible.para(cita.profesional.id, cita.fecha, cita.hora) from error
            raise
        cita.id = fila["id"]
        return cita

    def comprobar(self) -> None:
        with self._conexion() as c:
            c.execute("SELECT 1")
