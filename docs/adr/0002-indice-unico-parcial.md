# ADR 0002 · Índice único parcial contra la doble reserva

- **Estado:** aceptada
- **Fecha:** 12 de noviembre de 2026

## Contexto

La condición de negocio central dice que un profesional no puede tener dos citas **activas** en
un mismo horario. El dominio la verifica (`Profesional.esta_disponible` y, de nuevo,
`Profesional.agregar_cita`), pero esa verificación ocurre en memoria sobre una lectura previa:
si dos solicitudes concurrentes leen el bloque libre antes de que cualquiera guarde, ambas lo
dan por disponible y ambas insertarían su cita (condición de carrera de tipo *check-then-act*).

## Decisión

Agregar la restricción en la base de datos como segunda barrera:

```sql
CREATE UNIQUE INDEX uq_cita_activa ON cita (profesional_id, fecha, hora) WHERE estado = 'ACTIVA';
```

- Es **parcial**: solo indexa las citas `ACTIVA`, de modo que una `CANCELADA` no ocupa el bloque,
  igual que en el dominio.
- `RepositorioPostgres.guardar_cita` captura `UniqueViolation` y, si la restricción violada es
  `uq_cita_activa`, la traduce a `BloqueNoDisponible`. El cliente recibe el mismo 409 que si la
  regla hubiera saltado en el dominio. Otras violaciones únicas se propagan: no se esconden.
- `RepositorioMemoria` imita la barrera para que las pruebas unitarias cubran este camino.

## Consecuencias

- **A favor.** La regla se cumple aunque haya varias instancias de la API, scripts que escriban
  directo en la base o dos solicitudes simultáneas; no hace falta bloquear filas ni serializar.
- **Verificación.** `tests/integration/test_postgres.py` inserta dos citas activas directamente
  (salta el dominio) y comprueba que la segunda falla con `uq_cita_activa`; una prueba con dos
  hilos y una barrera comprueba que, de dos solicitudes simultáneas, una gana y la otra recibe
  `BloqueNoDisponible`.
- **En contra.** La regla queda expresada en dos lugares (dominio y SQL); el ADR y las pruebas
  existen para que no diverjan.
