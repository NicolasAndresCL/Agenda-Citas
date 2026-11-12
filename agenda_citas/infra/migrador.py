"""Migrador mínimo de esquema: aplica en orden los `NNN_nombre.sql` que aún no se han aplicado.

Lleva la cuenta en la tabla `schema_migrations`, así que correrlo dos veces no repite nada
(idempotente). Cada archivo se aplica en su propia transacción junto con su registro: o queda
aplicado y anotado, o no queda nada. Un candado asesor (`pg_advisory_xact_lock`) evita que dos
procesos que arrancan a la vez apliquen la misma migración.

Autor: Nicolás Cano Leal
Fecha: 12 de noviembre 2026
"""

from pathlib import Path

import psycopg

CANDADO = 727_001  # número arbitrario, común a todos los procesos de esta aplicación


def aplicar_migraciones(dsn: str, carpeta: Path) -> list[str]:
    """Aplica las migraciones pendientes y devuelve los nombres de las que aplicó."""
    archivos = sorted(carpeta.glob("[0-9][0-9][0-9]_*.sql"))
    aplicadas: list[str] = []
    with psycopg.connect(dsn, connect_timeout=5, autocommit=True) as conexion:
        conexion.execute(
            "CREATE TABLE IF NOT EXISTS schema_migrations ("
            " version TEXT PRIMARY KEY, aplicada_en TIMESTAMPTZ NOT NULL DEFAULT now())"
        )
        for archivo in archivos:
            with conexion.transaction():
                conexion.execute("SELECT pg_advisory_xact_lock(%s)", (CANDADO,))
                ya = conexion.execute(
                    "SELECT 1 FROM schema_migrations WHERE version = %s", (archivo.name,)
                ).fetchone()
                if ya:
                    continue
                conexion.execute(archivo.read_text(encoding="utf-8"))
                conexion.execute(
                    "INSERT INTO schema_migrations (version) VALUES (%s)", (archivo.name,)
                )
                aplicadas.append(archivo.name)
    return aplicadas
