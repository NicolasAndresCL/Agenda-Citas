"""Pruebas unitarias de la agenda sobre el repositorio en memoria (sin base de datos).

P1, P2 y P3 son las tres pruebas mínimas del enunciado (escenario exitoso, regla de negocio
rechazada y caso límite); el resto cubre los límites y validaciones del contrato
(docs/caso-agenda.md, sección 5). Cada docstring lleva el resultado esperado.

Autor: Nicolás Cano Leal
Fecha: 12 de noviembre 2026
"""

from datetime import date, time

import pytest

from agenda_citas.domain.entidades import Cita, EstadoCita
from agenda_citas.domain.excepciones import (
    BloqueNoDisponible,
    DatosInvalidos,
    PacienteNoEncontrado,
    ProfesionalNoEncontrado,
)
from tests.conftest import MARTES, RUT_JUAN


def test_prueba_1_escenario_exitoso(escenario):
    """P1 · Juan pide a la Dra. Rojas el martes 17/11 a las 10:00.

    Resultado esperado: la cita queda registrada (id asignado, estado ACTIVA) y el bloque
    deja de estar disponible.
    """
    agenda, rojas, juan, _ = escenario

    cita = agenda.agendar_cita(juan.id, rojas.id, MARTES, time(10, 0))

    assert cita.id is not None
    assert cita.estado is EstadoCita.ACTIVA
    assert cita.paciente.nombre == "Juan Pérez"
    assert [c.id for c in agenda.listar_citas()] == [cita.id]
    profesional = agenda._repositorio.obtener_profesional(rojas.id, MARTES)
    assert not profesional.esta_disponible(MARTES, time(10, 0))


def test_prueba_2_regla_doble_cita_rechazada(escenario):
    """P2 · María pide a la Dra. Rojas el mismo bloque que ya tomó Juan (17/11, 10:00).

    Resultado esperado: se lanza BloqueNoDisponible y no se crea ninguna cita nueva.
    """
    agenda, rojas, juan, maria = escenario
    agenda.agendar_cita(juan.id, rojas.id, MARTES, time(10, 0))

    with pytest.raises(BloqueNoDisponible) as error:
        agenda.agendar_cita(maria.id, rojas.id, MARTES, time(10, 0))

    assert error.value.detalle["hora"] == "10:00"
    assert len(agenda.listar_citas()) == 1


def test_prueba_3_limite_fin_de_franja(escenario):
    """P3 · Límite del fin de franja: 13:00 es la hora de término, no un bloque de atención.

    Resultado esperado: 13:00 se rechaza con BloqueNoDisponible (el bloque terminaría a las
    13:30, fuera de la franja) y 12:30, el último bloque que cabe, se acepta.
    """
    agenda, rojas, juan, maria = escenario

    with pytest.raises(BloqueNoDisponible):
        agenda.agendar_cita(juan.id, rojas.id, MARTES, time(13, 0))
    aceptada = agenda.agendar_cita(maria.id, rojas.id, MARTES, time(12, 30))

    assert aceptada.hora == time(12, 30)


def test_primer_bloque_09_00_aceptado(escenario):
    """Límite inferior. Resultado esperado: 09:00 (inicio de la franja) se acepta."""
    agenda, rojas, juan, _ = escenario
    assert agenda.agendar_cita(juan.id, rojas.id, MARTES, time(9, 0)).id is not None


def test_hora_no_alineada_rechazada(escenario):
    """10:15 no empieza un bloque de 30 minutos desde las 09:00.

    Resultado esperado: BloqueNoDisponible.
    """
    agenda, rojas, juan, _ = escenario
    with pytest.raises(BloqueNoDisponible):
        agenda.agendar_cita(juan.id, rojas.id, MARTES, time(10, 15))


def test_antes_de_la_franja_rechazada(escenario):
    """08:30 es anterior al inicio de la franja. Resultado esperado: BloqueNoDisponible."""
    agenda, rojas, juan, _ = escenario
    with pytest.raises(BloqueNoDisponible):
        agenda.agendar_cita(juan.id, rojas.id, MARTES, time(8, 30))


def test_dia_sin_franja_rechazado(escenario):
    """El miércoles 18/11 la doctora no tiene franja. Resultado esperado: BloqueNoDisponible."""
    agenda, rojas, juan, _ = escenario
    with pytest.raises(BloqueNoDisponible):
        agenda.agendar_cita(juan.id, rojas.id, date(2026, 11, 18), time(10, 0))


def test_hora_con_segundos_rechazada(escenario):
    """10:00:30 no es un inicio de bloque. Resultado esperado: BloqueNoDisponible."""
    agenda, rojas, juan, _ = escenario
    with pytest.raises(BloqueNoDisponible):
        agenda.agendar_cita(juan.id, rojas.id, MARTES, time(10, 0, 30))


def test_otro_profesional_a_la_misma_hora_aceptado(escenario):
    """La regla es por profesional.

    Resultado esperado: otro profesional con franja a las 10:00 acepta a María aunque Rojas
    ya tenga a Juan en ese horario.
    """
    agenda, rojas, juan, maria = escenario
    soto = agenda.registrar_profesional("Dr. Luis Soto", "Pediatría")
    agenda.registrar_franja(soto.id, MARTES, time(9, 0), time(13, 0))
    agenda.agendar_cita(juan.id, rojas.id, MARTES, time(10, 0))

    cita = agenda.agendar_cita(maria.id, soto.id, MARTES, time(10, 0))

    assert cita.profesional.nombre == "Dr. Luis Soto"


def test_cita_cancelada_no_bloquea(escenario):
    """Solo las citas ACTIVAS ocupan el bloque.

    Resultado esperado: con una cita CANCELADA a las 10:00 el profesional sigue disponible y
    esa hora se puede agendar.
    """
    agenda, rojas, juan, maria = escenario
    profesional = agenda._repositorio.obtener_profesional(rojas.id, MARTES)
    profesional.citas.append(Cita(juan, profesional, MARTES, time(10, 0), EstadoCita.CANCELADA))

    assert profesional.esta_disponible(MARTES, time(10, 0))
    cita = agenda.agendar_cita(maria.id, rojas.id, MARTES, time(10, 0))
    assert cita.esta_activa()


def test_entidad_vuelve_a_verificar_al_agregar_cita(escenario):
    """La regla vive en la entidad, no solo en el servicio.

    Resultado esperado: Profesional.agregar_cita lanza BloqueNoDisponible aunque nadie haya
    consultado esta_disponible antes.
    """
    agenda, rojas, juan, maria = escenario
    profesional = agenda._repositorio.obtener_profesional(rojas.id, MARTES)
    profesional.agregar_cita(Cita(juan, profesional, MARTES, time(10, 0)))

    with pytest.raises(BloqueNoDisponible):
        profesional.agregar_cita(Cita(maria, profesional, MARTES, time(10, 0)))


def test_segunda_barrera_del_repositorio_ante_concurrencia(escenario):
    """Dos solicitudes que consultaron antes de que la otra guardara.

    Resultado esperado: ambas pasan la verificación del dominio, pero el repositorio rechaza
    la segunda con BloqueNoDisponible (equivale al índice único parcial de Postgres).
    """
    agenda, rojas, juan, maria = escenario
    repo = agenda._repositorio
    copia_a = repo.obtener_profesional(rojas.id, MARTES)
    copia_b = repo.obtener_profesional(rojas.id, MARTES)
    cita_a = Cita(juan, copia_a, MARTES, time(10, 0))
    cita_b = Cita(maria, copia_b, MARTES, time(10, 0))
    copia_a.agregar_cita(cita_a)
    copia_b.agregar_cita(cita_b)

    repo.guardar_cita(cita_a)
    with pytest.raises(BloqueNoDisponible):
        repo.guardar_cita(cita_b)


def test_franja_con_inicio_mayor_o_igual_al_fin_es_invalida(agenda):
    """Resultado esperado: DatosInvalidos si hora_inicio >= hora_fin (13:00-09:00 y 09:00-09:00)."""
    rojas = agenda.registrar_profesional("Dra. Ana Rojas", "Medicina general")
    with pytest.raises(DatosInvalidos):
        agenda.registrar_franja(rojas.id, MARTES, time(13, 0), time(9, 0))
    with pytest.raises(DatosInvalidos):
        agenda.registrar_franja(rojas.id, MARTES, time(9, 0), time(9, 0))


def test_franja_para_profesional_inexistente(agenda):
    """Resultado esperado: ProfesionalNoEncontrado."""
    with pytest.raises(ProfesionalNoEncontrado):
        agenda.registrar_franja(99, MARTES, time(9, 0), time(13, 0))


def test_paciente_inexistente(escenario):
    """Resultado esperado: PacienteNoEncontrado y ninguna cita creada."""
    agenda, rojas, _, _ = escenario
    with pytest.raises(PacienteNoEncontrado):
        agenda.agendar_cita(99, rojas.id, MARTES, time(10, 0))
    assert agenda.listar_citas() == []


def test_profesional_inexistente(escenario):
    """Resultado esperado: ProfesionalNoEncontrado."""
    agenda, _, juan, _ = escenario
    with pytest.raises(ProfesionalNoEncontrado):
        agenda.agendar_cita(juan.id, 99, MARTES, time(10, 0))


@pytest.mark.parametrize("rut", ["12.345.678-9", "abc", "1-1", "12345678"])
def test_rut_invalido(agenda, rut):
    """Resultado esperado: DatosInvalidos si el formato o el dígito verificador no calzan."""
    with pytest.raises(DatosInvalidos):
        agenda.registrar_paciente(rut, "Alguien")


def test_rut_se_normaliza_y_acepta_k(agenda):
    """Resultado esperado: `12345678-5` se guarda como `12.345.678-5`; el dígito K es válido."""
    assert agenda.registrar_paciente("12345678-5", "Juan Pérez").rut == "12.345.678-5"
    assert agenda.registrar_paciente("10.000.013-k", "Con K").rut == "10.000.013-K"


def test_rut_duplicado(escenario):
    """Resultado esperado: DatosInvalidos al registrar dos veces el mismo RUT."""
    agenda, *_ = escenario
    with pytest.raises(DatosInvalidos):
        agenda.registrar_paciente("12345678-5", "Otro Juan")


def test_nombres_vacios(agenda):
    """Resultado esperado: DatosInvalidos con nombre o especialidad vacíos."""
    with pytest.raises(DatosInvalidos):
        agenda.registrar_profesional("  ", "Medicina general")
    with pytest.raises(DatosInvalidos):
        agenda.registrar_profesional("Dra. Rojas", "")
    with pytest.raises(DatosInvalidos):
        agenda.registrar_paciente(RUT_JUAN, " ")


def test_listados(escenario):
    """Resultado esperado: los listados devuelven lo registrado, con sus franjas."""
    agenda, *_ = escenario
    assert [p.nombre for p in agenda.listar_profesionales()] == ["Dra. Ana Rojas"]
    assert len(agenda.listar_profesionales()[0].franjas) == 1
    assert len(agenda.listar_pacientes()) == 2
    agenda.comprobar()
