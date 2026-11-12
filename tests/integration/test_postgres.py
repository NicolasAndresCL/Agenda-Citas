"""Pruebas contra un PostgreSQL real (marcador `integracion`, variable DATABASE_URL).

Se saltan si no hay base: en el CI corren contra el servicio postgres:17 y en local contra la de
`scripts/verificar.ps1` (puerto 5434). Incluyen la prueba que justifica el ADR 0002: el índice
único parcial rechaza dos citas activas aunque se salte toda la lógica del dominio.

Autor: Nicolás Cano Leal
Fecha: 12 de noviembre 2026
"""

import os
import threading
from datetime import time
from pathlib import Path

import psycopg
import pytest
from psycopg.errors import UniqueViolation

from agenda_citas.adapters.outbound.postgres import RepositorioPostgres
from agenda_citas.application.agenda import Agenda
from agenda_citas.domain.entidades import Cita, EstadoCita
from agenda_citas.domain.excepciones import (
    BloqueNoDisponible,
    DatosInvalidos,
    PacienteNoEncontrado,
    ProfesionalNoEncontrado,
)
from agenda_citas.infra.migrador import aplicar_migraciones
from tests.conftest import MARTES

DSN = os.environ.get("DATABASE_URL", "")
MIGRACIONES = Path(__file__).resolve().parents[2] / "migrations"

pytestmark = [
    pytest.mark.integracion,
    pytest.mark.skipif(not DSN, reason="DATABASE_URL no definida: no hay PostgreSQL de prueba"),
]


@pytest.fixture(scope="module", autouse=True)
def esquema():
    aplicar_migraciones(DSN, MIGRACIONES)


@pytest.fixture
def agenda():
    with psycopg.connect(DSN, autocommit=True) as c:
        c.execute("TRUNCATE cita, franja_horaria, paciente, profesional RESTART IDENTITY CASCADE")
    return Agenda(RepositorioPostgres(DSN))


@pytest.fixture
def escenario(agenda):
    rojas = agenda.registrar_profesional("Dra. Ana Rojas", "Medicina general")
    agenda.registrar_franja(rojas.id, MARTES, time(9, 0), time(13, 0))
    juan = agenda.registrar_paciente("12.345.678-5", "Juan Pérez")
    maria = agenda.registrar_paciente("9.876.543-3", "María Soto")
    return agenda, rojas, juan, maria


def test_migrador_es_idempotente():
    assert aplicar_migraciones(DSN, MIGRACIONES) == []
    with psycopg.connect(DSN) as c:
        filas = c.execute("SELECT version FROM schema_migrations").fetchall()
    assert filas == [("001_inicial.sql",)]


def test_escenarios_a_y_b_contra_postgres(escenario):
    agenda, rojas, juan, maria = escenario
    cita = agenda.agendar_cita(juan.id, rojas.id, MARTES, time(10, 0))
    assert cita.id is not None
    with pytest.raises(BloqueNoDisponible):
        agenda.agendar_cita(maria.id, rojas.id, MARTES, time(10, 0))
    assert agenda.agendar_cita(maria.id, rojas.id, MARTES, time(12, 30)).id is not None
    with pytest.raises(BloqueNoDisponible):
        agenda.agendar_cita(maria.id, rojas.id, MARTES, time(13, 0))
    citas = agenda.listar_citas()
    assert [(c.hora, c.paciente.nombre) for c in citas] == [
        (time(10, 0), "Juan Pérez"),
        (time(12, 30), "María Soto"),
    ]
    assert agenda.listar_profesionales()[0].franjas[0].hora_fin == time(13, 0)
    assert [p.nombre for p in agenda.listar_pacientes()] == ["Juan Pérez", "María Soto"]
    agenda.comprobar()


def test_indice_parcial_rechaza_dos_citas_activas_insertadas_directo(escenario):
    """Salta la lógica del dominio: la base sola debe impedir la doble reserva."""
    _, rojas, juan, maria = escenario
    sql = (
        "INSERT INTO cita (paciente_id, profesional_id, fecha, hora, estado)"
        " VALUES (%s, %s, %s, %s, %s)"
    )
    with psycopg.connect(DSN, autocommit=True) as c:
        c.execute(sql, (juan.id, rojas.id, MARTES, time(10, 0), "ACTIVA"))
        with pytest.raises(UniqueViolation) as error:
            c.execute(sql, (maria.id, rojas.id, MARTES, time(10, 0), "ACTIVA"))
        assert error.value.diag.constraint_name == "uq_cita_activa"
        # El índice es parcial: una CANCELADA en el mismo bloque sí cabe.
        c.execute(sql, (maria.id, rojas.id, MARTES, time(10, 0), "CANCELADA"))


def test_cita_cancelada_no_bloquea_en_postgres(escenario):
    agenda, rojas, juan, maria = escenario
    repo = agenda._repositorio
    profesional = repo.obtener_profesional(rojas.id, MARTES)
    repo.guardar_cita(Cita(juan, profesional, MARTES, time(10, 0), EstadoCita.CANCELADA))
    assert agenda.agendar_cita(maria.id, rojas.id, MARTES, time(10, 0)).id is not None


def test_solicitudes_concurrentes_solo_una_gana(escenario):
    """Ambas copias ven el bloque libre; la base deja pasar solo a una."""
    agenda, rojas, juan, maria = escenario
    repo = agenda._repositorio
    barrera = threading.Barrier(2)
    resultados: list[str] = []

    def solicitar(paciente) -> None:
        profesional = repo.obtener_profesional(rojas.id, MARTES)
        cita = Cita(paciente, profesional, MARTES, time(11, 0))
        profesional.agregar_cita(cita)  # las dos pasan la verificación del dominio
        barrera.wait()
        try:
            repo.guardar_cita(cita)
            resultados.append("ok")
        except BloqueNoDisponible:
            resultados.append("rechazada")

    hilos = [threading.Thread(target=solicitar, args=(p,)) for p in (juan, maria)]
    for h in hilos:
        h.start()
    for h in hilos:
        h.join()

    assert sorted(resultados) == ["ok", "rechazada"]


def test_rut_duplicado_y_entidades_inexistentes(escenario):
    agenda, *_ = escenario
    with pytest.raises(DatosInvalidos):
        agenda.registrar_paciente("12345678-5", "Otro")
    with pytest.raises(ProfesionalNoEncontrado):
        agenda.registrar_franja(999, MARTES, time(9, 0), time(10, 0))
    with pytest.raises(ProfesionalNoEncontrado):
        agenda._repositorio.obtener_profesional(999, MARTES)
    with pytest.raises(PacienteNoEncontrado):
        agenda._repositorio.obtener_paciente(999)


def test_borrar_profesional_borra_sus_franjas_composicion(escenario):
    _, rojas, *_ = escenario
    with psycopg.connect(DSN, autocommit=True) as c:
        c.execute("DELETE FROM profesional WHERE id = %s", (rojas.id,))
        assert c.execute("SELECT count(*) FROM franja_horaria").fetchone() == (0,)
