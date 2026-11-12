"""Configuración de la API desde variables de entorno (12-factor) con pydantic-settings.

Sin valor por defecto para DATABASE_URL cuando el almacenamiento es Postgres: arrancar sin ella
falla ruidoso en vez de conectarse a algo inesperado. `ALMACENAMIENTO=memoria` existe para probar
la API o la interfaz sin base de datos; los datos se pierden al reiniciar.

Autor: Nicolás Cano Leal
Fecha: 12 de noviembre 2026
"""

from pathlib import Path
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict

RAIZ = Path(__file__).resolve().parents[2]


class Configuracion(BaseSettings):
    """Variables de la API; las nombra igual que el .env.example."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    almacenamiento: Literal["postgres", "memoria"] = "postgres"
    database_url: str = ""
    aplicar_migraciones: bool = True
    migrations_dir: Path = RAIZ / "migrations"
    api_host: str = "0.0.0.0"  # noqa: S104 - dentro del contenedor debe escuchar en todas
    api_port: int = 8001
