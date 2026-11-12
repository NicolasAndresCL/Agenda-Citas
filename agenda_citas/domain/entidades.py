"""Entidades del dominio y su regla central: un profesional no tiene dos citas activas a la vez.

Sigue el diagrama de clases de docs/caso-agenda.md. La regla se evalúa en
`Profesional.esta_disponible` y se vuelve a exigir en `Profesional.agregar_cita`: la entidad no
confía en que el servicio ya haya preguntado. Una tercera barrera, el índice único parcial de la
base de datos, cubre las solicitudes concurrentes (ADR 0002).

Las entidades se comparan por identidad (`eq=False`): Profesional y Cita se referencian
mutuamente y una igualdad por campos recursionaría sin fin.

Autor: Nicolás Cano Leal
Fecha: 12 de noviembre 2026
"""

from dataclasses import dataclass, field
from datetime import date, time
from enum import Enum

from agenda_citas.domain.excepciones import BloqueNoDisponible, DatosInvalidos

DURACION_BLOQUE = 30  # minutos; todo bloque arranca alineado a la hora_inicio de su franja


def _minutos(hora: time) -> int:
    return hora.hour * 60 + hora.minute


def normalizar_rut(rut: str) -> str:
    """Valida el dígito verificador (módulo 11) y devuelve el RUT como `12.345.678-5`.

    Lanza DatosInvalidos si el formato o el dígito no corresponden.
    """
    limpio = rut.replace(".", "").replace(" ", "").upper()
    cuerpo, _, dv = limpio.partition("-")
    if not cuerpo.isdigit() or len(dv) != 1 or not 7 <= len(cuerpo) <= 8:
        raise DatosInvalidos("El RUT no tiene el formato 12.345.678-5.", {"rut": rut})
    suma = sum(int(d) * (2 + i % 6) for i, d in enumerate(reversed(cuerpo)))
    resto = 11 - suma % 11
    esperado = "0" if resto == 11 else "K" if resto == 10 else str(resto)
    if dv != esperado:
        raise DatosInvalidos("El dígito verificador del RUT no coincide.", {"rut": rut})
    return f"{int(cuerpo):,}".replace(",", ".") + f"-{dv}"


class EstadoCita(Enum):
    """ACTIVA ocupa el bloque; CANCELADA existe solo porque la regla habla de citas activas."""

    ACTIVA = "ACTIVA"
    CANCELADA = "CANCELADA"


@dataclass(eq=False)
class FranjaHoraria:
    """Tramo de un día en que un profesional atiende, dividido en bloques de 30 minutos."""

    fecha: date
    hora_inicio: time
    hora_fin: time

    def __post_init__(self) -> None:
        if self.hora_inicio >= self.hora_fin:
            raise DatosInvalidos(
                "La hora de inicio debe ser anterior a la hora de término.",
                {"hora_inicio": str(self.hora_inicio), "hora_fin": str(self.hora_fin)},
            )

    def contiene(self, hora: time) -> bool:
        """True si `hora` abre un bloque completo: alineada a hora_inicio y dentro de la franja."""
        if hora.second or hora.microsecond:
            return False
        desde = _minutos(self.hora_inicio)
        h = _minutos(hora)
        return (
            h >= desde
            and (h - desde) % DURACION_BLOQUE == 0
            and h + DURACION_BLOQUE <= _minutos(self.hora_fin)
        )


@dataclass(eq=False)
class Paciente:
    """Persona que solicita citas. `id = 0` significa que aún no se guarda."""

    id: int
    rut: str
    nombre: str

    def __post_init__(self) -> None:
        if not self.nombre.strip():
            raise DatosInvalidos("El nombre del paciente es obligatorio.")
        self.nombre = self.nombre.strip()
        self.rut = normalizar_rut(self.rut)


@dataclass(eq=False)
class Cita:
    """Reserva de un bloque de un profesional por un paciente."""

    paciente: Paciente
    profesional: "Profesional" = field(repr=False)
    fecha: date
    hora: time
    estado: EstadoCita = EstadoCita.ACTIVA
    id: int | None = None

    def esta_activa(self) -> bool:
        return self.estado is EstadoCita.ACTIVA


@dataclass(eq=False)
class Profesional:
    """Quien atiende. Sus franjas le pertenecen (composición): sin él no existen."""

    id: int
    nombre: str
    especialidad: str
    franjas: list[FranjaHoraria] = field(default_factory=list)
    citas: list[Cita] = field(default_factory=list, repr=False)

    def __post_init__(self) -> None:
        if not self.nombre.strip() or not self.especialidad.strip():
            raise DatosInvalidos("El nombre y la especialidad del profesional son obligatorios.")
        self.nombre = self.nombre.strip()
        self.especialidad = self.especialidad.strip()

    def esta_disponible(self, fecha: date, hora: time) -> bool:
        """True si alguna franja contiene el bloque y no hay una cita ACTIVA en esa fecha y hora."""
        en_franja = any(f.fecha == fecha and f.contiene(hora) for f in self.franjas)
        ocupado = any(c.esta_activa() and c.fecha == fecha and c.hora == hora for c in self.citas)
        return en_franja and not ocupado

    def agregar_cita(self, cita: Cita) -> None:
        """Incorpora la cita; vuelve a verificar la disponibilidad (la regla vive aquí)."""
        if not self.esta_disponible(cita.fecha, cita.hora):
            raise BloqueNoDisponible.para(self.id, cita.fecha, cita.hora)
        self.citas.append(cita)
