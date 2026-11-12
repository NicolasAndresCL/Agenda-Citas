"""La versión debe ser la misma en pyproject, el paquete, la app FastAPI, el README y el CHANGELOG.

Autor: Nicolás Cano Leal
Fecha: 12 de noviembre 2026
"""

import re
import tomllib
from pathlib import Path

from fastapi.testclient import TestClient

from agenda_citas import __version__
from agenda_citas.adapters.outbound.memoria import RepositorioMemoria
from agenda_citas.main import crear_app

RAIZ = Path(__file__).resolve().parents[1]


def test_version_sincronizada():
    v = tomllib.loads((RAIZ / "pyproject.toml").read_text(encoding="utf-8"))["project"]["version"]
    app = crear_app(repositorio=RepositorioMemoria())
    assert __version__ == v
    assert app.version == v
    assert TestClient(app).get("/livez").json()["version"] == v
    changelog = (RAIZ / "CHANGELOG.md").read_text(encoding="utf-8")
    assert re.search(r"^## \[(\d+\.\d+\.\d+[^\]]*)\]", changelog, re.M).group(1) == v
    assert f"versi%C3%B3n-{v}-" in (RAIZ / "README.md").read_text(encoding="utf-8")
