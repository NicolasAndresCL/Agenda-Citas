"""Fixtures comunes: el escenario del contrato (Dra. Rojas, Juan y María) sobre el repositorio fake.

Autor: Nicolás Cano Leal
Fecha: 12 de noviembre 2026
"""

from datetime import date, time

import pytest

from agenda_citas.adapters.outbound.memoria import RepositorioMemoria
from agenda_citas.application.agenda import Agenda

MARTES = date(2026, 11, 17)
RUT_JUAN = "12.345.678-5"
RUT_MARIA = "9.876.543-3"


@pytest.fixture
def agenda() -> Agenda:
    return Agenda(RepositorioMemoria())


@pytest.fixture
def escenario(agenda: Agenda):
    """Rojas atiende el martes 17/11/2026 de 09:00 a 13:00; Juan y María son pacientes."""
    rojas = agenda.registrar_profesional("Dra. Ana Rojas", "Medicina general")
    agenda.registrar_franja(rojas.id, MARTES, time(9, 0), time(13, 0))
    juan = agenda.registrar_paciente(RUT_JUAN, "Juan Pérez")
    maria = agenda.registrar_paciente(RUT_MARIA, "María Soto")
    return agenda, rojas, juan, maria
