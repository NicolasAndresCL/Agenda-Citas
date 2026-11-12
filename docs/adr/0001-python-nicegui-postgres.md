# ADR 0001 · Python, NiceGUI y PostgreSQL

- **Estado:** aceptada
- **Fecha:** 12 de noviembre de 2026

## Contexto

La asignatura (IEI-050) trabaja habitualmente con Java y BlueJ. Para esta actividad grupal el
docente, Giovanni Cáceres, aceptó que el equipo usara Python. El producto debe llevar el diseño
UML (actividades, secuencia, comunicación y clases) a código ejecutable con pruebas, y el
responsable de la implementación (Nicolás Cano Leal) domina el ecosistema Python.

## Decisión

- **Lenguaje:** Python 3.13 con tipado explícito, verificado con ruff.
- **Arquitectura hexagonal:** `domain` (entidades y reglas) y `application` (casos de uso)
  no importan nada de fuera; el puerto `RepositorioAgenda` se implementa en adaptadores de
  salida (`RepositorioPostgres`, `RepositorioMemoria`) y la API FastAPI es el adaptador de
  entrada. `main.py` es la raíz de composición. La estructura replica el diagrama de clases:
  la interfaz del repositorio y sus realizaciones están dibujadas.
- **API:** FastAPI, con un único manejador que traduce los errores de dominio al contrato JSON
  `{"error": {"codigo", "mensaje", "detalle"}}`.
- **Interfaz:** NiceGUI. Consume la API por HTTP (httpx, con *timeout*) y nunca importa el
  dominio, de modo que la regla de negocio vive en un solo lugar.
- **Persistencia:** PostgreSQL 17 con psycopg 3, SQL explícito y migraciones versionadas
  (`migrations/NNN_*.sql`) aplicadas por un migrador mínimo con tabla `schema_migrations`.
- **Empaquetado:** una imagen Docker multi-stage no-root, usada por `api` y `ui` con distinto
  comando, más `db` en Compose.

## Consecuencias

- **A favor.** El dominio se prueba sin base de datos (repositorio en memoria); la regla central
  tiene tres barreras (servicio, entidad, índice de la base); la interfaz se puede reemplazar sin
  tocar la lógica.
- **En contra.** Más piezas que un monolito de BlueJ, y un salto HTTP entre interfaz y API que el
  modelo de objetos no dibuja (se documenta como detalle de despliegue).
- **Alternativas descartadas.** Java/BlueJ (el docente aceptó Python y el equipo prefiere la
  cadena de verificación de Python); ORM (SQL explícito basta para cuatro tablas y deja visible
  el índice parcial); *pool* de conexiones (una agenda de este tamaño no lo necesita: se abre una
  conexión por operación).
