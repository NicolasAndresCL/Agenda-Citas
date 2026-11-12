"""Pruebas del cliente HTTP de la interfaz con un transporte simulado (sin red ni NiceGUI).

Autor: Nicolás Cano Leal
Fecha: 12 de noviembre 2026
"""

import httpx
import pytest

from frontend.cliente import ApiNoDisponible, ClienteAgenda, ErrorApi


def cliente_con(manejador) -> ClienteAgenda:
    return ClienteAgenda("http://api", transporte=httpx.MockTransport(manejador))


async def test_agendar_cita_envia_el_cuerpo_y_devuelve_json():
    def manejador(peticion: httpx.Request) -> httpx.Response:
        assert peticion.url.path == "/api/citas"
        return httpx.Response(201, json={"id": 1})

    resultado = await cliente_con(manejador).agendar_cita(1, 1, "2026-11-17", "10:00")
    assert resultado == {"id": 1}


async def test_error_del_contrato_se_convierte_en_error_api():
    def manejador(_: httpx.Request) -> httpx.Response:
        cuerpo = {"error": {"codigo": "BLOQUE_NO_DISPONIBLE", "mensaje": "ocupado", "detalle": {}}}
        return httpx.Response(409, json=cuerpo)

    with pytest.raises(ErrorApi) as error:
        await cliente_con(manejador).agendar_cita(1, 1, "2026-11-17", "10:00")
    assert (error.value.estado, error.value.codigo) == (409, "BLOQUE_NO_DISPONIBLE")


async def test_respuesta_sin_contrato_se_trata_como_error_generico():
    cliente = cliente_con(lambda _: httpx.Response(502, text="Bad gateway"))
    with pytest.raises(ErrorApi) as error:
        await cliente.listar_citas()
    assert error.value.codigo == "ERROR_API"


async def test_api_caida_lanza_api_no_disponible():
    def manejador(_: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("rechazada")

    with pytest.raises(ApiNoDisponible):
        await cliente_con(manejador).listar_pacientes()


async def test_el_resto_de_operaciones_usan_sus_rutas():
    rutas = []

    def manejador(peticion: httpx.Request) -> httpx.Response:
        rutas.append((peticion.method, peticion.url.path))
        return httpx.Response(200, json=[])

    c = cliente_con(manejador)
    await c.listar_profesionales()
    await c.registrar_profesional("Dra. Rojas", "Medicina general")
    await c.registrar_franja(1, "2026-11-17", "09:00", "13:00")
    await c.registrar_paciente("12.345.678-5", "Juan Pérez")
    assert rutas == [
        ("GET", "/api/profesionales"),
        ("POST", "/api/profesionales"),
        ("POST", "/api/profesionales/1/franjas"),
        ("POST", "/api/pacientes"),
    ]
