"""Excepciones de dominio tipadas.

Cada una lleva un `codigo` estable (el que viaja en el contrato JSON de errores) y un `detalle`
con los datos que explican el fallo. El dominio no conoce HTTP: la traducción a códigos de
estado vive en el adaptador de entrada (adapters/inbound/api.py).

Autor: Nicolás Cano Leal
Fecha: 12 de noviembre 2026
"""

from datetime import date, time
from typing import Any


class ErrorDominio(Exception):
    """Base de los errores de negocio; no se lanza directamente."""

    codigo = "ERROR_DOMINIO"

    def __init__(self, mensaje: str, detalle: dict[str, Any] | None = None) -> None:
        super().__init__(mensaje)
        self.mensaje = mensaje
        self.detalle = detalle or {}


class BloqueNoDisponible(ErrorDominio):
    """El bloque pedido está fuera de toda franja o ya tiene una cita activa."""

    codigo = "BLOQUE_NO_DISPONIBLE"

    @classmethod
    def para(cls, id_profesional: int, fecha: date, hora: time) -> "BloqueNoDisponible":
        """Construye el error con el mismo mensaje y detalle desde cualquier capa."""
        return cls(
            "El bloque solicitado no está disponible.",
            {
                "profesional_id": id_profesional,
                "fecha": fecha.isoformat(),
                "hora": hora.strftime("%H:%M"),
            },
        )


class ProfesionalNoEncontrado(ErrorDominio):
    """No existe un profesional con ese identificador."""

    codigo = "PROFESIONAL_NO_ENCONTRADO"


class PacienteNoEncontrado(ErrorDominio):
    """No existe un paciente con ese identificador."""

    codigo = "PACIENTE_NO_ENCONTRADO"


class DatosInvalidos(ErrorDominio):
    """Un dato no cumple su validación (vacío, RUT inválido, franja con inicio >= fin...)."""

    codigo = "DATOS_INVALIDOS"
