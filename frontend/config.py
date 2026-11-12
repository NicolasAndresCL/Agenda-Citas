"""Configuración de la interfaz: dónde está la API y en qué puerto sirve la UI.

El puerto 8085 evita el 8080, que en este equipo ocupa Jenkins.

Autor: Nicolás Cano Leal
Fecha: 12 de noviembre 2026
"""

from pydantic_settings import BaseSettings, SettingsConfigDict


class ConfiguracionUI(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    api_url: str = "http://localhost:8001"
    frontend_host: str = "0.0.0.0"  # noqa: S104 - dentro del contenedor debe escuchar en todas
    frontend_port: int = 8085
    http_timeout_s: float = 5.0
