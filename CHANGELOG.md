# Changelog

Todos los cambios notables de este proyecto se documentan aquí. El formato sigue
[Keep a Changelog](https://keepachangelog.com/es-ES/1.1.0/) y el versionado,
[SemVer](https://semver.org/lang/es/).

## [Sin publicar]

## [0.1.0] — 2026-11-12

### Agregado

- Dominio con la regla central: un profesional no puede tener dos citas activas en el mismo
  bloque (`Profesional`, `FranjaHoraria`, `Paciente`, `Cita`, `EstadoCita`) y excepciones de
  dominio tipadas.
- Caso de uso `Agenda` (registrar profesionales, pacientes y franjas; agendar cita) y puerto
  `RepositorioAgenda` con adaptadores PostgreSQL (psycopg 3) y en memoria.
- Migraciones SQL versionadas con migrador mínimo (`schema_migrations`) e índice único parcial
  `uq_cita_activa` como segunda barrera contra solicitudes concurrentes.
- API FastAPI con contrato único de errores, `/livez` y `/healthz`.
- Interfaz NiceGUI (Profesionales, Pacientes, Agendar cita, Citas) que consume la API por HTTP.
- Docker (imagen multi-stage no-root, Compose con PostgreSQL 17), CI de tres jobs, release por
  tag, Dependabot y plantillas de issue y pull request.
- Contrato de diseño, cuatro diagramas UML en blanco y negro, informe en PDF y evidencia JUnit.
