-- Esquema inicial de la agenda de citas (v0.1.0).
-- Las claves foráneas siguen el diagrama de clases: la franja es composición de su profesional
-- (ON DELETE CASCADE) y la cita referencia a un paciente y a un profesional.

CREATE TABLE profesional (
    id            INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    nombre        TEXT NOT NULL CHECK (length(btrim(nombre)) > 0),
    especialidad  TEXT NOT NULL CHECK (length(btrim(especialidad)) > 0)
);

CREATE TABLE paciente (
    id      INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    rut     TEXT NOT NULL UNIQUE,
    nombre  TEXT NOT NULL CHECK (length(btrim(nombre)) > 0)
);

CREATE TABLE franja_horaria (
    id              INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    profesional_id  INTEGER NOT NULL REFERENCES profesional (id) ON DELETE CASCADE,
    fecha           DATE NOT NULL,
    hora_inicio     TIME NOT NULL,
    hora_fin        TIME NOT NULL,
    CHECK (hora_inicio < hora_fin)
);

CREATE INDEX ix_franja_profesional ON franja_horaria (profesional_id, fecha);

CREATE TABLE cita (
    id              INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    paciente_id     INTEGER NOT NULL REFERENCES paciente (id),
    profesional_id  INTEGER NOT NULL REFERENCES profesional (id),
    fecha           DATE NOT NULL,
    hora            TIME NOT NULL,
    estado          TEXT NOT NULL DEFAULT 'ACTIVA' CHECK (estado IN ('ACTIVA', 'CANCELADA'))
);

-- Segunda barrera de la regla «un profesional no tiene dos citas activas a la misma hora»:
-- si dos solicitudes concurrentes pasan la verificación del dominio, la base rechaza la
-- segunda. Es parcial: una cita CANCELADA no ocupa el bloque (ADR 0002).
CREATE UNIQUE INDEX uq_cita_activa ON cita (profesional_id, fecha, hora) WHERE estado = 'ACTIVA';
