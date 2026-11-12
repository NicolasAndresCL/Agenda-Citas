"""RepositorioMemoria: implementación del puerto sobre diccionarios, para pruebas sin base de datos.

Imita lo que garantiza Postgres para que las pruebas unitarias y de API vean el mismo
comportamiento: `obtener_profesional` devuelve una copia con sus franjas y sus citas ACTIVAS de la
fecha (no el objeto guardado), y `guardar_cita` rechaza un segundo bloque activo igual, como el
índice único parcial `uq_cita_activa`. Esa segunda barrera permite probar el camino de la
concurrencia sin levantar Postgres.

Autor: Nicolás Cano Leal
Fecha: 12 de noviembre 2026
"""

from datetime import date

from agenda_citas.domain.entidades import Cita, FranjaHoraria, Paciente, Profesional
from agenda_citas.domain.excepciones import (
    BloqueNoDisponible,
    DatosInvalidos,
    PacienteNoEncontrado,
    ProfesionalNoEncontrado,
)


class RepositorioMemoria:
    """Almacén volátil con ids autoincrementales por tabla, como las columnas IDENTITY."""

    def __init__(self) -> None:
        self._profesionales: dict[int, Profesional] = {}
        self._pacientes: dict[int, Paciente] = {}
        self._franjas: dict[int, list[FranjaHoraria]] = {}
        self._citas: list[Cita] = []

    def obtener_profesional(self, id_profesional: int, fecha: date) -> Profesional:
        base = self._profesionales.get(id_profesional)
        if base is None:
            raise ProfesionalNoEncontrado(
                "No existe el profesional.", {"profesional_id": id_profesional}
            )
        copia = Profesional(base.id, base.nombre, base.especialidad)
        copia.franjas = list(self._franjas.get(id_profesional, []))
        copia.citas = [
            c
            for c in self._citas
            if c.profesional.id == id_profesional and c.fecha == fecha and c.esta_activa()
        ]
        return copia

    def obtener_paciente(self, id_paciente: int) -> Paciente:
        paciente = self._pacientes.get(id_paciente)
        if paciente is None:
            raise PacienteNoEncontrado("No existe el paciente.", {"paciente_id": id_paciente})
        return paciente

    def guardar_cita(self, cita: Cita) -> Cita:
        if cita.esta_activa() and any(
            c.esta_activa()
            and c.profesional.id == cita.profesional.id
            and c.fecha == cita.fecha
            and c.hora == cita.hora
            for c in self._citas
        ):
            raise BloqueNoDisponible.para(cita.profesional.id, cita.fecha, cita.hora)
        cita.id = len(self._citas) + 1
        self._citas.append(cita)
        return cita

    def guardar_profesional(self, profesional: Profesional) -> Profesional:
        profesional.id = len(self._profesionales) + 1
        self._profesionales[profesional.id] = profesional
        self._franjas[profesional.id] = []
        return profesional

    def guardar_paciente(self, paciente: Paciente) -> Paciente:
        if any(p.rut == paciente.rut for p in self._pacientes.values()):
            raise DatosInvalidos("Ya existe un paciente con ese RUT.", {"rut": paciente.rut})
        paciente.id = len(self._pacientes) + 1
        self._pacientes[paciente.id] = paciente
        return paciente

    def guardar_franja(self, id_profesional: int, franja: FranjaHoraria) -> FranjaHoraria:
        if id_profesional not in self._profesionales:
            raise ProfesionalNoEncontrado(
                "No existe el profesional.", {"profesional_id": id_profesional}
            )
        self._franjas[id_profesional].append(franja)
        return franja

    def listar_profesionales(self) -> list[Profesional]:
        resultado = []
        for p in self._profesionales.values():
            copia = Profesional(p.id, p.nombre, p.especialidad)
            copia.franjas = list(self._franjas[p.id])
            resultado.append(copia)
        return resultado

    def listar_pacientes(self) -> list[Paciente]:
        return list(self._pacientes.values())

    def listar_citas(self) -> list[Cita]:
        return sorted(self._citas, key=lambda c: (c.fecha, c.hora))

    def comprobar(self) -> None:
        """La memoria siempre responde."""
