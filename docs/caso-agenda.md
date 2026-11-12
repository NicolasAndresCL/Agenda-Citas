# Caso de diseño · Agenda de citas

**Asignatura:** Diseño de Software (IEI-050) · actividad grupal
**Docente:** Giovanni Cáceres R. (aceptó Python en lugar de Java)
**Líder:** Nicolás Cano Leal · **Equipo:** Tais Montecinos, Alex Díaz
**Fecha:** 12 de noviembre de 2026

Este archivo es el **contrato de diseño**: los cuatro diagramas, el código de `agenda_citas/` y las
pruebas de `tests/` usan exactamente los nombres, mensajes, guardas y datos de abajo. Si algo
cambia aquí, cambia en todos lados (un mismo nombre para cada objeto y operación).

## 1. El caso en una frase

Un centro de atención agenda citas para sus profesionales. Un paciente solicita una cita con un
profesional, una fecha y una hora; el sistema **solo la registra si el bloque está disponible**
(dentro de una franja de atención del profesional y sin otra cita activa). Si no lo está, **la cita
no se crea** y se informa la indisponibilidad.

## 2. Requisitos de la iteración 1 y dónde se resuelven

| Req. | Enunciado | Dónde vive |
|---|---|---|
| R1 | Registrar profesionales, pacientes y franjas horarias de atención | `Agenda.registrar_profesional`, `registrar_paciente`, `registrar_franja` |
| R2 | Un paciente solicita una cita con profesional, fecha y hora | mensaje 1 `solicitar_cita` y 1.1 `agendar_cita` |
| R3 | El sistema verifica que el bloque esté disponible | `Profesional.esta_disponible` (mensaje 1.1.2) |
| R4 | Si lo está, registra la cita; si no, informa indisponibilidad | mensajes 1.1.3 a 1.1.5 (camino `[disponible]`) o `BloqueNoDisponible` (camino `[else]`) |

**Condiciones de negocio:** (a) un profesional no puede tener dos citas activas en un mismo
horario; (b) cada cita pertenece a un paciente y a un profesional.
La iteración 2 (producto mínimo) cubre dos comportamientos: agendar una cita válida y bloquear
dos citas del mismo profesional a la misma hora. No se agregan requisitos más allá de R1 a R4.

## 3. Participantes (iguales en los tres diagramas dinámicos)

| Participante | Tipo | Responsabilidad en el caso |
|---|---|---|
| `Paciente` | Actor | Ingresa profesional, fecha y hora y lee el resultado |
| `:PantallaAgenda` | Objeto (interfaz) | Recibe la solicitud y muestra el mensaje; **no decide** si el bloque está libre |
| `agenda:Agenda` | Objeto (caso de uso) | Coordina: obtiene al profesional, le pregunta, crea la cita, la agrega y la guarda |
| `:RepositorioAgenda` | Objeto (puerto) | Entrega al profesional con sus franjas y citas activas, y guarda la cita |
| `rojas:Profesional` | Objeto | Conoce sus franjas y sus citas; responde si un bloque está disponible |
| `c:Cita` | Objeto | Se crea **solo** si el bloque está disponible |

## 4. Clases y firmas (el diagrama de clases las muestra todas)

| Clase | Atributos | Operaciones |
|---|---|---|
| `Profesional` | `id: int`, `nombre: str`, `especialidad: str`, `franjas: list[FranjaHoraria]`, `citas: list[Cita]` | `esta_disponible(fecha: date, hora: time): bool`, `agregar_cita(cita: Cita): None` |
| `FranjaHoraria` | `fecha: date`, `hora_inicio: time`, `hora_fin: time` | `contiene(hora: time): bool` |
| `Paciente` | `id: int`, `rut: str`, `nombre: str` | — |
| `Cita` | `id: int \| None`, `paciente: Paciente`, `profesional: Profesional`, `fecha: date`, `hora: time`, `estado: EstadoCita` | `esta_activa(): bool` |
| `EstadoCita` «enumeration» | `ACTIVA`, `CANCELADA` | — |
| `Agenda` | `_repositorio: RepositorioAgenda` | `registrar_profesional`, `registrar_paciente`, `registrar_franja`, `agendar_cita`, `listar_profesionales`, `listar_pacientes`, `listar_citas`, `comprobar` |
| `RepositorioAgenda` «interface» | — | `obtener_profesional(id_profesional, fecha)`, `obtener_paciente`, `guardar_cita`, `guardar_profesional`, `guardar_paciente`, `guardar_franja`, `listar_profesionales`, `listar_pacientes`, `listar_citas`, `comprobar` |
| `RepositorioPostgres` | `_dsn: str` | realiza las operaciones del puerto con PostgreSQL |
| `RepositorioMemoria` | diccionarios y lista internos | realiza las operaciones del puerto en memoria (pruebas) |

Notas de diseño:

- **Visibilidad.** En Python los atributos de las entidades son públicos (sin *getters*), por eso
  se anotan con `+`; solo `_repositorio` y `_dsn` son privados por convención.
- **Constante del módulo.** `DURACION_BLOQUE = 30` (minutos) vive en `domain/entidades.py`, no es
  un atributo de clase y por eso no figura en el diagrama.
- **Identificadores.** `id = 0` significa «aún no persistido»; el repositorio asigna el definitivo.
  `Cita.id` es `int | None` porque la cita se crea antes de guardarse.
- **Excepciones de dominio** (no dibujadas, para no recargar el diagrama): `BloqueNoDisponible`,
  `ProfesionalNoEncontrado`, `PacienteNoEncontrado` y `DatosInvalidos`, todas hijas de
  `ErrorDominio`.
- **Obtención del paciente.** El código resuelve primero al `Paciente` por su identificador
  (`obtener_paciente`, que puede lanzar `PacienteNoEncontrado`). Los diagramas lo omiten para
  centrarse en la verificación del bloque; no altera el orden de los mensajes 1.1.1 a 1.1.5.

## 5. Reglas de negocio y validaciones

| Regla | Dónde se aplica |
|---|---|
| Un bloque dura `DURACION_BLOQUE = 30` minutos y arranca alineado a `hora_inicio` de la franja | `FranjaHoraria.contiene` |
| El bloque debe terminar dentro de la franja: `hora + 30 min <= hora_fin` | `FranjaHoraria.contiene` |
| `hora_inicio < hora_fin` | `FranjaHoraria` (constructor, lanza `DatosInvalidos`) |
| Una cita **activa** ocupa el bloque; una `CANCELADA` no | `Profesional.esta_disponible` |
| Defensa en profundidad: la entidad vuelve a verificar | `Profesional.agregar_cita` lanza `BloqueNoDisponible` |
| Defensa en profundidad: la base rechaza dos activas concurrentes | índice único parcial `uq_cita_activa` (ADR 0002) |
| RUT con dígito verificador válido (módulo 11) y único | `Paciente`, restricción `UNIQUE` |

`CANCELADA` existe solo porque la regla habla de «citas activas»: no hay caso de uso de cancelar.

## 6. Datos del ejemplo

Dra. Ana Rojas (Medicina general), con una franja el **martes 17/11/2026 de 09:00 a 13:00**.
Pacientes: Juan Pérez (12.345.678-5) y María Soto (9.876.543-3).

| Escenario | Entrada | Resultado |
|---|---|---|
| A · disponible | Juan pide a Rojas el 17/11 a las 10:00 | `esta_disponible` → `true`; se crea `c`; «Cita registrada» |
| B · ocupado | María pide a Rojas el 17/11 a las 10:00 | `esta_disponible` → `false`; **no se crea `c`**; «Bloque no disponible» |

Casos límite (todos con prueba automática):

| Entrada | Resultado | Motivo |
|---|---|---|
| 12:30 | aceptada | último bloque: termina a las 13:00 |
| 13:00 | rechazada | fuera de franja (terminaría a las 13:30) |
| 10:15 | rechazada | no alineada a bloques de 30 min desde las 09:00 |
| otro profesional a las 10:00 | aceptada | la regla es por profesional |
| cita `CANCELADA` en 10:00 | no bloquea | solo las activas ocupan el bloque |

## 7. Diagrama de actividades

Carriles: **Paciente** · **PantallaAgenda** · **Agenda**. Nodo inicial → *Ingresar profesional,
fecha y hora* → *Enviar la solicitud* → *Verificar el bloque (franja + cita activa)* → decisión:

- `[bloque disponible]` → *Crear la cita* → *Registrar la cita* → *Mostrar «Cita registrada»* →
  nodo final.
- `[bloque ocupado o fuera de franja]` → *Mostrar «Bloque no disponible»* → nodo final.

Dos nodos finales, uno por camino. Las guardas son complementarias y cubren todos los casos.

## 8. Diagrama de secuencia (escenario A)

Líneas de vida con barras de activación, en este orden:

1. `Paciente` → `:PantallaAgenda`: `solicitar_cita(paciente, profesional, fecha, hora)`
2. `:PantallaAgenda` → `agenda:Agenda`: `c := agendar_cita(paciente, profesional, fecha, hora)`
3. `agenda:Agenda` → `:RepositorioAgenda`: `rojas := obtener_profesional(profesional, fecha)`;
   retorno punteado `rojas`
4. `agenda:Agenda` → `rojas:Profesional`: `disponible := esta_disponible(fecha, hora)`;
   retorno punteado `disponible`
5. Fragmento **alt**:
   - `[disponible]`: «create» `Cita(paciente, rojas, fecha, hora)` hacia `c:Cita` (su cabecera
     aparece a la altura del mensaje, no arriba); `agregar_cita(c)` hacia `rojas`;
     `guardar_cita(c)` hacia `:RepositorioAgenda`; retorno `c` hacia `:PantallaAgenda`;
     automensaje `mostrar_mensaje("Cita registrada")`.
   - `[else]`: retorno punteado `BloqueNoDisponible` hacia `:PantallaAgenda`; automensaje
     `mostrar_mensaje("Bloque no disponible")`.

En `[else]` no hay ningún mensaje hacia `c:Cita`: la cita rechazada no existe.

## 9. Diagrama de comunicación

Los mismos seis participantes, unidos por **enlaces** (líneas sin flecha) solo donde hay
mensajes: Paciente—PantallaAgenda, PantallaAgenda—Agenda, Agenda—RepositorioAgenda,
Agenda—Profesional, Agenda—Cita y un enlace reflexivo en PantallaAgenda.

| N.º | Mensaje | Enlace |
|---|---|---|
| 1 | `solicitar_cita(paciente, profesional, fecha, hora)` | Paciente → PantallaAgenda |
| 1.1 | `c := agendar_cita(paciente, profesional, fecha, hora)` | PantallaAgenda → Agenda |
| 1.1.1 | `rojas := obtener_profesional(profesional, fecha)` | Agenda → RepositorioAgenda |
| 1.1.2 | `disponible := esta_disponible(fecha, hora)` | Agenda → Profesional |
| 1.1.3 | `[disponible] «create» Cita(paciente, rojas, fecha, hora)` | Agenda → Cita |
| 1.1.4 | `[disponible] agregar_cita(c)` | Agenda → Profesional |
| 1.1.5 | `[disponible] guardar_cita(c)` | Agenda → RepositorioAgenda |
| 1.2 | `[c registrada] mostrar_mensaje("Cita registrada")` | PantallaAgenda → sí misma |
| 1.3 | `[BloqueNoDisponible] mostrar_mensaje("Bloque no disponible")` | PantallaAgenda → sí misma |

Lo que en la secuencia daba la **posición vertical**, aquí lo da el **número**; lo que daba el
fragmento **alt**, aquí lo dan las **guardas** entre corchetes.

## 10. Diagrama de clases: relaciones

| Relación | Notación | Multiplicidad |
|---|---|---|
| `Profesional` — `FranjaHoraria` | composición (rombo negro en `Profesional`): la franja no existe sin su profesional | 1 ◆ 0..* |
| `Profesional` — `Cita` | asociación bidireccional (`citas` / `profesional`) | 1 — 0..* |
| `Cita` → `Paciente` | asociación navegable hacia `Paciente` (`paciente`) | 0..* — 1 |
| `Cita` → `EstadoCita` | asociación al tipo enumerado (`estado`) | 1 |
| `Agenda` ⇢ `RepositorioAgenda` | dependencia (usa la interfaz, no la implementación) | — |
| `RepositorioPostgres`, `RepositorioMemoria` ⇢▷ `RepositorioAgenda` | realización | — |

El rombo y el triángulo hueco se dibujan como polígonos: Arial no trae esos glifos.

## 11. El salto HTTP es detalle de despliegue

La interfaz (NiceGUI) llama a la API (FastAPI) por HTTP, y la API invoca a `Agenda`. Ese salto
no se dibuja en la secuencia ni en la comunicación: `:PantallaAgenda` representa la capa de
interfaz como un solo participante, y el protocolo que la une con el caso de uso es una decisión
de despliegue (ADR 0001), no de diseño de objetos. En cambio, el **diagrama de clases sí muestra**
el puerto `RepositorioAgenda` y su implementación `RepositorioPostgres`, porque ahí se decide la
inversión de dependencias que permite probar con `RepositorioMemoria`.

## 12. Pruebas mínimas y su trazabilidad

| Prueba | Función | Escenario | Resultado esperado |
|---|---|---|---|
| P1 | `test_prueba_1_escenario_exitoso` | A | cita registrada, estado `ACTIVA` |
| P2 | `test_prueba_2_regla_doble_cita_rechazada` | B | `BloqueNoDisponible`, sin cita nueva |
| P3 | `test_prueba_3_limite_fin_de_franja` | 13:00 / 12:30 | 13:00 rechazada, 12:30 aceptada |

## 13. Registro del gerente

| Rol | Persona |
|---|---|
| Líder / Gestor de proyecto | Nicolás Cano Leal |
| Responsable UML | Alex Díaz |
| Responsable Python | Nicolás Cano Leal |
| Responsable de pruebas y enlace Trello | Tais Montecinos (enlace: por completar) |

La tarjeta de cambio llega por separado en la última iteración y se documentará entonces.
