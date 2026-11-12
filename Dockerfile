# Una sola imagen para la API y la interfaz: cambia solo el comando (ver docker-compose.yml).
# ---------------------------------------------------------------- build
FROM python:3.13-slim AS builder
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1
WORKDIR /src
COPY pyproject.toml README.md ./
COPY agenda_citas/ agenda_citas/
COPY frontend/ frontend/
RUN python -m venv /opt/venv \
    && /opt/venv/bin/pip install --upgrade pip \
    && /opt/venv/bin/pip install .

# ---------------------------------------------------------------- runtime
FROM python:3.13-slim AS runtime
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PATH="/opt/venv/bin:$PATH" \
    MIGRATIONS_DIR=/app/migrations
RUN useradd --create-home --shell /usr/sbin/nologin agenda
WORKDIR /app
COPY --from=builder /opt/venv /opt/venv
COPY --chown=agenda:agenda migrations/ migrations/
USER agenda
EXPOSE 8001 8085
# /livez no consulta la base: el contenedor de la API está "vivo" aunque Postgres caiga;
# /healthz (con base) lo usa Compose para saber si está listo. La UI sobrescribe esta sonda.
HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
    CMD ["python", "-c", "import urllib.request; urllib.request.urlopen('http://localhost:8001/livez', timeout=3)"]
CMD ["python", "-m", "agenda_citas"]
