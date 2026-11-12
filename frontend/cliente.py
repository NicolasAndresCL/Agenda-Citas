"""Cliente HTTP de la API (httpx asíncrono, con timeout).

Es la única puerta de la interfaz hacia los datos. Convierte los errores del contrato
`{"error": {...}}` en `ErrorApi` y la caída de la API (timeout, conexión rechazada) en
`ApiNoDisponible`, para que las páginas muestren un mensaje en vez de romperse.

Autor: Nicolás Cano Leal
Fecha: 12 de noviembre 2026
"""

from typing import Any

import httpx


class ErrorApi(Exception):
    """La API respondió con un error del contrato (409, 404, 422...)."""

    def __init__(self, estado: int, codigo: str, mensaje: str) -> None:
        super().__init__(mensaje)
        self.estado = estado
        self.codigo = codigo
        self.mensaje = mensaje


class ApiNoDisponible(Exception):
    """No hubo respuesta de la API dentro del plazo."""


class ClienteAgenda:
    def __init__(
        self,
        base_url: str,
        timeout_s: float = 5.0,
        transporte: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self._http = httpx.AsyncClient(
            base_url=base_url.rstrip("/") + "/api",
            timeout=httpx.Timeout(timeout_s, connect=3.0),
            transport=transporte,
        )

    async def _llamar(self, metodo: str, ruta: str, cuerpo: dict[str, Any] | None = None) -> Any:
        try:
            respuesta = await self._http.request(metodo, ruta, json=cuerpo)
        except httpx.HTTPError as error:
            raise ApiNoDisponible("No hay respuesta de la API.") from error
        if respuesta.is_success:
            return respuesta.json()
        try:
            datos = respuesta.json()["error"]
            codigo, mensaje = datos["codigo"], datos["mensaje"]
        except (ValueError, KeyError, TypeError):
            codigo, mensaje = "ERROR_API", "Respuesta inesperada de la API."
        raise ErrorApi(respuesta.status_code, codigo, mensaje)

    async def listar_profesionales(self) -> list[dict[str, Any]]:
        return await self._llamar("GET", "/profesionales")

    async def registrar_profesional(self, nombre: str, especialidad: str) -> dict[str, Any]:
        return await self._llamar(
            "POST", "/profesionales", {"nombre": nombre, "especialidad": especialidad}
        )

    async def registrar_franja(
        self, id_profesional: int, fecha: str, hora_inicio: str, hora_fin: str
    ) -> dict[str, Any]:
        cuerpo = {"fecha": fecha, "hora_inicio": hora_inicio, "hora_fin": hora_fin}
        return await self._llamar("POST", f"/profesionales/{id_profesional}/franjas", cuerpo)

    async def listar_pacientes(self) -> list[dict[str, Any]]:
        return await self._llamar("GET", "/pacientes")

    async def registrar_paciente(self, rut: str, nombre: str) -> dict[str, Any]:
        return await self._llamar("POST", "/pacientes", {"rut": rut, "nombre": nombre})

    async def agendar_cita(
        self, paciente_id: int, profesional_id: int, fecha: str, hora: str
    ) -> dict[str, Any]:
        cuerpo = {
            "paciente_id": paciente_id,
            "profesional_id": profesional_id,
            "fecha": fecha,
            "hora": hora,
        }
        return await self._llamar("POST", "/citas", cuerpo)

    async def listar_citas(self) -> list[dict[str, Any]]:
        return await self._llamar("GET", "/citas")
