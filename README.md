# Agenda de citas — agenda de un centro de atención sin dobles reservas

[![CI](https://github.com/NicolasAndresCL/Agenda-Citas/actions/workflows/ci.yml/badge.svg)](https://github.com/NicolasAndresCL/Agenda-Citas/actions/workflows/ci.yml)
![Versión](https://img.shields.io/badge/versi%C3%B3n-0.1.0-blue)
![Python](https://img.shields.io/badge/python-3.13-3776AB)

| | |
|---|---|
| **Versión** | 0.1.0 |
| **Fecha** | 12 de noviembre de 2026 |
| **Autor** | [Nicolás Andrés Cano Leal](#autor) |

Sistema de agenda de citas para un centro de atención, desarrollado para la asignatura Diseño de
Software (IEI-050, Universidad Santo Tomás; el docente aceptó Python en lugar de Java). Un paciente
solicita una cita con un profesional, una fecha y una hora; el sistema la registra **solo si el
bloque está disponible** y, si no, informa la indisponibilidad. Un profesional nunca tiene dos citas
activas en el mismo horario.

- **Interfaz:** NiceGUI (Profesionales, Pacientes, Agendar cita, Citas), que consume la API por HTTP.
- **API:** FastAPI con contrato único de errores, `/livez` y `/healthz`.
- **Persistencia:** PostgreSQL 17 con migraciones SQL versionadas; la fuente de verdad de la regla
  central son tres barreras (servicio, entidad e índice único parcial de la base).
- **Todo dockerizado:** una imagen multi-stage no-root para `api` y `ui`, más `db` en Compose.

El diseño (los cuatro diagramas UML, el contrato y el informe) vive en `docs/`.

## Arquitectura

```text
agenda-citas/
├── agenda_citas/                  # backend (hexagonal)
│   ├── domain/
│   │   ├── entidades.py           # Profesional, FranjaHoraria, Paciente, Cita, EstadoCita y la regla
│   │   ├── excepciones.py         # errores de dominio tipados (con código estable)
│   │   └── puertos.py             # Protocol RepositorioAgenda
│   ├── application/agenda.py      # caso de uso Agenda (R1 a R4)
│   ├── adapters/
│   │   ├── inbound/api.py         # FastAPI: rutas y manejadores de error
│   │   └── outbound/              # RepositorioPostgres (psycopg 3) y RepositorioMemoria (pruebas)
│   ├── infra/                     # configuración (pydantic-settings) y migrador de esquema
│   └── main.py                    # raíz de composición: elige el repositorio e inyecta Agenda
├── frontend/                      # NiceGUI; solo habla HTTP (cliente httpx con timeout)
├── migrations/001_inicial.sql     # esquema + índice único parcial uq_cita_activa
├── tests/                         # unit/ (fake), api/ (TestClient), integration/ (PostgreSQL real)
├── docs/                          # contrato, diagramas, informe, ADR y generadores
├── evidencias/                    # JUnit, salida de pytest y capturas de la interfaz
├── scripts/verificar.ps1          # reproduce el CI en local
├── Dockerfile                     # multi-stage, no-root, HEALTHCHECK a /livez
└── docker-compose.yml             # db (postgres:17-alpine), api, ui
```

**Flujo:** navegador → `ui` (NiceGUI) → HTTP → `api` (FastAPI) → `Agenda` → `RepositorioAgenda` →
`db` (PostgreSQL). La interfaz no importa el dominio; el dominio no importa FastAPI, psycopg ni NiceGUI.

## Levantar con Docker

Cada comando va en su propio bloque; ejecútalos en este orden desde la carpeta `agenda-citas/`.

Copia la plantilla de variables. Se hace una sola vez; `.env` está en `.gitignore` y nunca se versiona.

```powershell
Copy-Item .env.example .env
```

Salida esperada: ninguna. Si `.env` ya existe, PowerShell lo sobrescribe: no lo hagas dos veces.

Genera una contraseña para la base y pégala en `POSTGRES_PASSWORD` de `.env`.

```powershell
python -c "import secrets; print(secrets.token_urlsafe(24))"
```

`secrets.token_urlsafe(24)` produce 24 bytes aleatorios en texto seguro para URL. La salida es una
cadena de unos 32 caracteres; sin una contraseña real, `compose` se niega a arrancar
(`define POSTGRES_PASSWORD en tu .env`), a propósito.

Construye las imágenes y levanta los tres servicios.

```powershell
docker compose up -d --build --wait
```

- `up` crea y arranca los contenedores; `-d` los deja en segundo plano.
- `--build` reconstruye la imagen si cambió el código.
- `--wait` bloquea hasta que cada servicio esté sano (`healthy`) según su `healthcheck`: `db`
  espera a `pg_isready`, `api` a `/healthz` (que consulta la base) y `ui` a que responda.

Salida esperada: líneas `Container agenda-citas-db-1 Healthy`, luego `api` y `ui`. Si algo falla,
`docker compose logs api` muestra por qué.

| Servicio | URL | Para qué |
|---|---|---|
| `ui` | http://localhost:8085 | Interfaz (el 8080 es de Jenkins) |
| `api` | http://localhost:8001/docs | API y documentación OpenAPI |
| `api` | http://localhost:8001/livez · `/healthz` | Sondas de vida y de preparación |
| `db` | `localhost:5433` | PostgreSQL (5433 porque el 5432 suele ocupar un Postgres local) |

Para terminar:

```powershell
docker compose down
```

`down` borra los contenedores y la red pero **conserva los datos** (volumen `datos_postgres`).
**`docker compose down -v` borra también el volumen: se pierden todas las citas.**

## Correr en local sin Docker

Requiere Python 3.13 y, para persistir, un PostgreSQL accesible. Crea el entorno virtual con la misma
versión que usa el CI.

```powershell
py -3.13 -m venv .venv
```

`py -3.13` elige esa versión entre las instaladas; `-m venv .venv` crea el entorno en `.venv/`.

Instala el proyecto con las herramientas de desarrollo.

```powershell
.\.venv\Scripts\python -m pip install -e ".[dev]"
```

`-e` es una instalación editable (los cambios en el código se ven sin reinstalar) y `".[dev]"`
agrega los extras de `[project.optional-dependencies] dev` (pytest, ruff, pillow...).

Arranca la API. Sin base de datos, usa el almacenamiento en memoria (los datos se pierden al cerrar).

```powershell
$env:ALMACENAMIENTO = "memoria"; .\.venv\Scripts\python -m agenda_citas
```

Con PostgreSQL, define `DATABASE_URL` en lugar de `ALMACENAMIENTO`; la API aplica las migraciones
al arrancar. En otra terminal, arranca la interfaz:

```powershell
.\.venv\Scripts\python -m frontend.app
```

Salida esperada: `NiceGUI ready to go on http://localhost:8085`.

## Endpoints

Prefijo `/api`.

| Método | Ruta | Qué hace |
|---|---|---|
| POST | `/api/profesionales` | Registra un profesional (R1) |
| GET | `/api/profesionales` | Lista profesionales con sus franjas |
| POST | `/api/profesionales/{id}/franjas` | Agrega una franja horaria (R1) |
| POST | `/api/pacientes` | Registra un paciente (R1) |
| GET | `/api/pacientes` | Lista pacientes |
| POST | `/api/citas` | Solicita una cita (R2 a R4): 201 si se registra, 409 si el bloque no está disponible |
| GET | `/api/citas` | Lista citas por fecha y hora |
| GET | `/livez` | Vivo (no consulta la base) |
| GET | `/healthz` | Listo: consulta la base; 503 si no responde |

Todo error usa el mismo contrato:

```json
{"error": {"codigo": "BLOQUE_NO_DISPONIBLE", "mensaje": "El bloque solicitado no está disponible.",
           "detalle": {"profesional_id": 1, "fecha": "2026-11-17", "hora": "10:00"}}}
```

| Código | HTTP | Cuándo |
|---|---|---|
| `BLOQUE_NO_DISPONIBLE` | 409 | Fuera de franja, no alineado a bloques de 30 min o con cita activa |
| `PROFESIONAL_NO_ENCONTRADO` | 404 | El profesional no existe |
| `PACIENTE_NO_ENCONTRADO` | 404 | El paciente no existe |
| `DATOS_INVALIDOS` | 422 | Nombre vacío, RUT inválido o repetido, franja con inicio >= fin |
| `SOLICITUD_INVALIDA` | 422 | El cuerpo no cumple el formato (tipos, campos faltantes) |
| `ERROR_INTERNO` | 500 | Falla inesperada; no filtra detalles |

## La interfaz

- **Profesionales:** registrar profesionales y agregar franjas horarias.
- **Pacientes:** registrar pacientes (el RUT se valida con su dígito verificador).
- **Agendar cita:** elegir paciente, profesional, fecha y hora; muestra «Cita registrada» o
  «Bloque no disponible».
- **Citas:** tabla de todas las citas.

Si la API no responde (timeout o conexión rechazada), la interfaz lo avisa con una notificación y
sigue viva; no se cae.

## Variables de entorno

| Variable | Servicio | Por defecto | Para qué |
|---|---|---|---|
| **`POSTGRES_PASSWORD`** | db, api | — (obligatoria en Compose) | Contraseña de la base |
| `POSTGRES_USER` · `POSTGRES_DB` | db, api | `agenda` | Usuario y base |
| `DB_PUERTO_HOST` | db | `5433` | Puerto del host hacia PostgreSQL |
| **`DATABASE_URL`** | api | — (obligatoria con `ALMACENAMIENTO=postgres` fuera de Compose) | Cadena de conexión |
| `ALMACENAMIENTO` | api | `postgres` | `postgres` o `memoria` |
| `APLICAR_MIGRACIONES` | api | `true` | Aplica `migrations/` al arrancar |
| `MIGRATIONS_DIR` | api | `./migrations` | Carpeta de migraciones |
| `API_PORT` | api | `8001` | Puerto de la API |
| `API_URL` | ui | `http://localhost:8001` | Dirección de la API vista desde la interfaz |
| `FRONTEND_PORT` | ui | `8085` | Puerto de la interfaz |
| `HTTP_TIMEOUT_S` | ui | `5` | Plazo de las llamadas a la API |

## Verificación

```powershell
.\scripts\verificar.ps1
```

Reproduce en este mismo orden los tres jobs del CI (`.github/workflows/ci.yml`), con un venv nuevo
de Python 3.13 y una base PostgreSQL de prueba (`docker compose -p agenda-citas-test`, puerto 5434)
que **siempre se elimina al terminar**, aunque algo falle:

1. **lint:** `ruff check` y `ruff format --check`.
2. **tests:** `pytest` contra PostgreSQL real, con cobertura mínima de 85 % y evidencia JUnit en
   `evidencias/junit-pruebas.xml`. Última corrida: **49 pruebas aprobadas** (24 unitarias, 12 de
   API, 5 del cliente, 1 de versión, 7 de integración), cobertura **97 %**.
3. **build:** construye la imagen, la arranca y comprueba que `/livez` responde.

Con `-Clon` clona `HEAD` a una carpeta temporal y verifica ahí lo versionado, que es lo único que
ve el runner del CI.

## Decisiones de diseño

- **La regla vive en el dominio, no solo en el servicio.** `Profesional.agregar_cita` vuelve a
  verificar la disponibilidad: la entidad no confía en que alguien preguntó antes.
- **Defensa en profundidad con un índice único parcial.** Dos solicitudes concurrentes pueden pasar
  la verificación en memoria; `uq_cita_activa` hace que la base rechace la segunda y el adaptador la
  traduce a `BloqueNoDisponible`. Es parcial para que una cita cancelada no ocupe el bloque
  (ADR 0002).
- **Hexagonal con puerto `Protocol`.** El dominio no importa psycopg ni FastAPI; las pruebas
  unitarias usan un repositorio en memoria que imita la segunda barrera.
- **La interfaz nunca importa el dominio.** Habla HTTP con timeout; cambia la interfaz sin tocar la
  regla.
- **`/livez` no consulta la base, `/healthz` sí.** Un Postgres caído deja la API «viva» pero no
  «lista»; no se unifican.
- **Bloques de 30 minutos como supuesto explícito.** El enunciado no define «bloque»; se fijó
  `DURACION_BLOQUE = 30` alineado al inicio de la franja y se documentó en el contrato.
- **SQL explícito sin ORM.** Cuatro tablas no justifican un ORM y dejan a la vista el índice parcial
  (ADR 0001).

## Autor

**Nicolás Andrés Cano Leal**\
Backend Engineer → SRE | Python · Django · Kubernetes · Terraform · CI/CD

- LinkedIn: [linkedin.com/in/nicolasandrescl](https://www.linkedin.com/in/nicolasandrescl/)
- Portafolio: [nicolasandrescl.github.io](https://nicolasandrescl.github.io/)
- Correo: [nicolas.cano.leal@gmail.com](mailto:nicolas.cano.leal@gmail.com)

Agenda de citas v0.1.0 · 12 de noviembre de 2026
