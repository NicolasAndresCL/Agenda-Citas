"""Puerto de salida del dominio: el contrato que cualquier almacenamiento debe cumplir.

Hay dos implementaciones: RepositorioPostgres (producción) y RepositorioMemoria (pruebas
unitarias y de API). Es un Protocol: el dominio no hereda de nada ni importa psycopg.

Autor: Nicolás Cano Leal
Fecha: 12 de noviembre 2026
"""

from datetime import date
from typing import Protocol

from agenda_citas.domain.entidades import Cita, FranjaHoraria, Paciente, Profesional


class RepositorioAgenda(Protocol):
    """Persistencia de profesionales, pacientes, franjas y citas."""

    def obtener_profesional(self, id_profesional: int, fecha: date) -> Profesional:
        """Profesional con todas sus franjas y sus citas ACTIVAS de esa fecha.

        Lanza ProfesionalNoEncontrado si no existe.
        """
        ...

    def obtener_paciente(self, id_paciente: int) -> Paciente:
        """Lanza PacienteNoEncontrado si no existe."""
        ...

    def guardar_cita(self, cita: Cita) -> Cita:
        """Persiste la cita y devuelve la misma con su id. Lanza BloqueNoDisponible si el
        almacenamiento rechaza un segundo bloque activo (barrera final contra la concurrencia)."""
        ...

    def guardar_profesional(self, profesional: Profesional) -> Profesional: ...

    def guardar_paciente(self, paciente: Paciente) -> Paciente:
        """Lanza DatosInvalidos si el RUT ya está registrado."""
        ...

    def guardar_franja(self, id_profesional: int, franja: FranjaHoraria) -> FranjaHoraria:
        """Lanza ProfesionalNoEncontrado si el profesional no existe."""
        ...

    def listar_profesionales(self) -> list[Profesional]:
        """Profesionales con sus franjas (sin citas)."""
        ...

    def listar_pacientes(self) -> list[Paciente]: ...

    def listar_citas(self) -> list[Cita]:
        """Todas las citas, con su paciente y su profesional, por fecha y hora."""
        ...

    def comprobar(self) -> None:
        """Consulta liviana al almacenamiento; lanza si no responde (la usa /healthz)."""
        ...
