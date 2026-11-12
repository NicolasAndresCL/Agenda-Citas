"""Pruebas de la API con TestClient y el repositorio en memoria: rutas, códigos HTTP y el
contrato de error `{"error": {"codigo", "mensaje", "detalle"}}`.

Autor: Nicolás Cano Leal
Fecha: 12 de noviembre 2026
"""

import pytest
from fastapi.testclient import TestClient

from agenda_citas.adapters.outbound.memoria import RepositorioMemoria
from agenda_citas.main import crear_app

FRANJA = {"fecha": "2026-11-17", "hora_inicio": "09:00", "hora_fin": "13:00"}


@pytest.fixture
def cliente() -> TestClient:
    return TestClient(crear_app(repositorio=RepositorioMemoria()), raise_server_exceptions=False)


@pytest.fixture
def datos(cliente):
    """Rojas con franja el 17/11/2026 de 09:00 a 13:00; Juan y María registrados."""
    profesional = {"nombre": "Dra. Ana Rojas", "especialidad": "Medicina general"}
    cliente.post("/api/profesionales", json=profesional)
    assert cliente.post("/api/profesionales/1/franjas", json=FRANJA).status_code == 201
    cliente.post("/api/pacientes", json={"rut": "12.345.678-5", "nombre": "Juan Pérez"})
    cliente.post("/api/pacientes", json={"rut": "9.876.543-3", "nombre": "María Soto"})
    return cliente


def solicitud(paciente: int, hora: str) -> dict:
    return {"paciente_id": paciente, "profesional_id": 1, "fecha": "2026-11-17", "hora": hora}


def test_livez_y_healthz(cliente):
    assert cliente.get("/livez").json()["estado"] == "vivo"
    assert cliente.get("/healthz").json()["estado"] == "ok"


def test_healthz_responde_503_si_la_base_no_contesta():
    class Caido(RepositorioMemoria):
        def comprobar(self) -> None:
            raise ConnectionError("sin base")

    c = TestClient(crear_app(repositorio=Caido()))
    assert c.get("/healthz").status_code == 503
    assert c.get("/livez").status_code == 200  # /livez no consulta la base


def test_agendar_cita_valida_devuelve_201(datos):
    r = datos.post("/api/citas", json=solicitud(1, "10:00"))
    assert r.status_code == 201
    cuerpo = r.json()
    assert (cuerpo["hora"], cuerpo["estado"], cuerpo["profesional"]) == (
        "10:00",
        "ACTIVA",
        "Dra. Ana Rojas",
    )
    assert datos.get("/api/citas").json()[0]["paciente"]["nombre"] == "Juan Pérez"


def test_doble_cita_devuelve_409_con_el_contrato_de_error(datos):
    datos.post("/api/citas", json=solicitud(1, "10:00"))
    r = datos.post("/api/citas", json=solicitud(2, "10:00"))
    assert r.status_code == 409
    error = r.json()["error"]
    assert error["codigo"] == "BLOQUE_NO_DISPONIBLE"
    assert error["mensaje"]
    assert error["detalle"] == {"profesional_id": 1, "fecha": "2026-11-17", "hora": "10:00"}
    assert len(datos.get("/api/citas").json()) == 1


@pytest.mark.parametrize("hora", ["13:00", "10:15"])
def test_limites_devuelven_409(datos, hora):
    assert datos.post("/api/citas", json=solicitud(1, hora)).status_code == 409


def test_ultimo_bloque_12_30_devuelve_201(datos):
    assert datos.post("/api/citas", json=solicitud(1, "12:30")).status_code == 201


def test_paciente_o_profesional_inexistente_devuelve_404(datos):
    r = datos.post("/api/citas", json=solicitud(99, "10:00"))
    assert (r.status_code, r.json()["error"]["codigo"]) == (404, "PACIENTE_NO_ENCONTRADO")
    r = datos.post("/api/citas", json={**solicitud(1, "10:00"), "profesional_id": 99})
    assert (r.status_code, r.json()["error"]["codigo"]) == (404, "PROFESIONAL_NO_ENCONTRADO")
    assert datos.post("/api/profesionales/99/franjas", json=FRANJA).status_code == 404


def test_datos_invalidos_devuelven_422(datos):
    r = datos.post("/api/pacientes", json={"rut": "1-1", "nombre": "X"})
    assert (r.status_code, r.json()["error"]["codigo"]) == (422, "DATOS_INVALIDOS")
    franja = {"fecha": "2026-11-17", "hora_inicio": "13:00", "hora_fin": "09:00"}
    assert datos.post("/api/profesionales/1/franjas", json=franja).status_code == 422


def test_cuerpo_mal_formado_usa_el_mismo_contrato(datos):
    r = datos.post("/api/citas", json={"paciente_id": "uno"})
    assert r.status_code == 422
    error = r.json()["error"]
    assert error["codigo"] == "SOLICITUD_INVALIDA"
    assert {d["campo"] for d in error["detalle"]} >= {"paciente_id", "profesional_id"}


def test_error_inesperado_devuelve_500_sin_filtrar_detalles():
    class Roto(RepositorioMemoria):
        def listar_citas(self):
            raise RuntimeError("secreto interno")

    c = TestClient(crear_app(repositorio=Roto()), raise_server_exceptions=False)
    r = c.get("/api/citas")
    assert r.status_code == 500
    assert r.json()["error"]["codigo"] == "ERROR_INTERNO"
    assert "secreto" not in r.text


def test_listados(datos):
    assert datos.get("/api/profesionales").json()[0]["franjas"][0]["hora_fin"] == "13:00"
    ruts = [p["rut"] for p in datos.get("/api/pacientes").json()]
    assert ruts == ["12.345.678-5", "9.876.543-3"]
