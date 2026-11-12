"""Casos de uso de la agenda (R1 a R4 del enunciado).

`Agenda` recibe el repositorio por constructor (inyección): no sabe si detrás hay Postgres o un
diccionario. `agendar_cita` es el mensaje 1.1 del diagrama de comunicación; el diagrama omite
la búsqueda del paciente (`obtener_paciente`) por simplicidad, pero el código la hace antes de
consultar al profesional.

Autor: Nicolás Cano Leal
Fecha: 12 de noviembre 2026
"""

from datetime import date, time

from agenda_citas.domain.entidades import Cita, FranjaHoraria, Paciente, Profesional
from agenda_citas.domain.excepciones import BloqueNoDisponible
from agenda_citas.domain.puertos import RepositorioAgenda


class Agenda:
    """Registra profesionales, pacientes y franjas, y agenda citas sin doble reserva."""

    def __init__(self, repositorio: RepositorioAgenda) -> None:
        self._repositorio = repositorio

    # R1 · registrar profesionales, pacientes y franjas ---------------------------------------
    def registrar_profesional(self, nombre: str, especialidad: str) -> Profesional:
        return self._repositorio.guardar_profesional(Profesional(0, nombre, especialidad))

    def registrar_paciente(self, rut: str, nombre: str) -> Paciente:
        return self._repositorio.guardar_paciente(Paciente(0, rut, nombre))

    def registrar_franja(
        self, id_profesional: int, fecha: date, hora_inicio: time, hora_fin: time
    ) -> FranjaHoraria:
        franja = FranjaHoraria(fecha, hora_inicio, hora_fin)  # valida inicio < fin
        return self._repositorio.guardar_franja(id_profesional, franja)

    # R2 a R4 · solicitar, verificar y registrar (o informar indisponibilidad) ----------------
    def agendar_cita(self, id_paciente: int, id_profesional: int, fecha: date, hora: time) -> Cita:
        """Crea la cita si el bloque está disponible; si no, lanza BloqueNoDisponible.

        Orden de los mensajes (1.1.1 a 1.1.5 del contrato): obtener el profesional, preguntarle
        si está disponible, crear la cita, agregarla y guardarla. En el camino rechazado la
        `Cita` nunca se crea.
        """
        paciente = self._repositorio.obtener_paciente(id_paciente)
        profesional = self._repositorio.obtener_profesional(id_profesional, fecha)  # 1.1.1
        if not profesional.esta_disponible(fecha, hora):  # 1.1.2
            raise BloqueNoDisponible.para(id_profesional, fecha, hora)  # rama [else]
        cita = Cita(paciente, profesional, fecha, hora)  # 1.1.3
        profesional.agregar_cita(cita)  # 1.1.4
        return self._repositorio.guardar_cita(cita)  # 1.1.5

    # consultas para la interfaz -----------------------------------------------------------------
    def listar_profesionales(self) -> list[Profesional]:
        return self._repositorio.listar_profesionales()

    def listar_pacientes(self) -> list[Paciente]:
        return self._repositorio.listar_pacientes()

    def listar_citas(self) -> list[Cita]:
        return self._repositorio.listar_citas()

    def comprobar(self) -> None:
        """Verifica que el almacenamiento responde (lo usa /healthz)."""
        self._repositorio.comprobar()
