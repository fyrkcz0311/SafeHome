# Documentacion


> **Especificaciones que sigue la API**
> - [circuit.md](circuit.md) — comportamiento del circuito ESP32 (estados, umbrales, actuadores).
> - [circuit-endpoints.md](circuit-endpoints.md) — contrato HTTP que consume el firmware.
> - [Proyecto.md](Proyecto.md) — documento original del proyecto.

---

## 1. Qué problema resuelve

El proyecto SafeHome es un sistema IoT que vigila una cocina con un **ESP32** y:

- **Gas (MQ-2)** — concentración en ppm.
- **Temperatura y humedad (DHT22)** — en °C y %.
- **Presencia (PIR)** — detección de personas.

Y como actuadores: una **electroválvula** que corta el gas, un **buzzer** de alarma,
**LEDs** (verde/amarillo/rojo) y dos **botones físicos** OPEN/CLOSE.

Punto clave de `circuit.md`: **la seguridad crítica se decide en el ESP32, no en la
nube**. El circuito detecta el peligro y cierra el gas aunque no haya Internet. La API
cumple un papel de **supervisión, almacenamiento histórico, configuración y control
remoto** — no participa en la respuesta crítica.

---

## 2. Decisiones de diseño (y por qué)

| Decisión | Elección | Por qué |
| --- | --- | --- |
| Framework | **FastAPI** | Rápido, tipado, Swagger automático y WebSockets nativos. |
| Comunicación circuito → API | **HTTP REST (POST)** | El dispositivo solo hace un POST con JSON. |
| Base de datos | **SQLite** | Cero configuración, un solo archivo. Ideal para demo/curso. |
| ORM | **SQLModel** | Une SQLAlchemy + Pydantic: el mismo modelo es tabla y validación. |
| Tiempo real | **WebSocket** | Empuja cada lectura al dashboard sin que el navegador pregunte. |
| Pruebas | **pytest + TestClient** | Lógica probada de forma aislada y endpoints end-to-end. |

### Ideas clave del diseño

1. **La API es "agnóstica al origen".** No sabe si los datos vienen de un ESP32 real,
   de Proteus o de un script: solo recibe JSON por HTTP. Esto permitió desarrollarla y
   probarla sin hardware.

2. **El comando viaja en la respuesta del POST.** El dispositivo no mantiene conexión
   abierta; la decisión (`cerrar`/`abrir`/`mantener` + buzzer) vuelve en la respuesta
   del mismo POST de telemetría. Como alternativa, `GET /comando` permite *polling*.

3. **El circuito y la API se sincronizan.** Como el ESP32 actúa por su cuenta (botones
   físicos, auto-cierre por DANGER), cada telemetría incluye `valve_open` y
   `alarm_enabled` (el estado real de sus actuadores). La API toma ese estado como base
   y **solo lo sobreescribe si su propia evaluación detecta emergencia** (la seguridad
   prevalece).

4. **Nunca se abre el gas automáticamente.** El sistema cierra solo, pero la reapertura
   siempre exige una acción explícita del usuario (botón OPEN, app, web o API).

---

## 3. La lógica de seguridad (el "cerebro")

Está aislada en [app/services/alertas.py](app/services/alertas.py) como una **función
pura** (`evaluar_lectura`): recibe números, devuelve una decisión y **no toca la base de
datos**. Replica los estados de `circuit.md`:

| Estado circuito | Nivel en la API | Condición | Acción |
| --- | --- | --- | --- |
| **NORMAL** | `normal` | gas < 1000 ppm y sin condición peligrosa | Sin cambios |
| **WARNING** | `alerta` | gas ≥ 1000 ppm  **o**  temp ≥ 55 °C **sin presencia** | Solo aviso |
| **DANGER** | `emergencia` | gas ≥ 2000 ppm  **o**  temp ≥ 70 °C **sin presencia** | Cerrar válvula + buzzer |

Detalle importante tomado de `circuit.md`: **la temperatura solo se evalúa cuando no hay
presencia** (PIR sin detección). Una cocina caliente con alguien presente es normal; la
misma temperatura con la cocina vacía es sospechosa.

Cuando hay varios riesgos a la vez, el más grave manda (gas en DANGER tiene prioridad,
pero igual se registran todas las alertas).

---

## 4. Arquitectura y flujo de datos

```
   ┌─────────────┐   POST /api/telemetria                     ┌──────────────────────────┐
   │  CIRCUITO   │  {gas, temp, presencia,                    │        API (FastAPI)     │
   │ ESP32 +     │   valve_open, alarm_enabled}               │                          │
   │ sensores    │ ─────────────────────────────────────────►│  1. guarda la Lectura    │
   │ + botones   │ ◄───────────────────────────────────────── │  2. evalúa umbrales      │
   └─────────────┘   respuesta: {valvula, buzzer}             │  3. crea Alertas         │
        (Proteus / simulador / bridge serie)                  │  4. sincroniza + decide  │
                                                              │  5. broadcast WebSocket  │
                                                              │  6. responde el comando  │
                                                              └───────────┬──────────────┘
                                                                          │
                          ┌────────────────────────────────────────────────┼─────────────┐
                          ▼                                                 ▼             ▼
                    ┌───────────┐                                   ┌────────────┐  ┌──────────┐
                    │  SQLite   │                                   │ Dashboard  │  │  Swagger │
                    │ safehome  │                                   │  (WS live) │  │  /docs   │
                    └───────────┘                                   └────────────┘  └──────────┘
```

**Paso a paso cuando llega una lectura** ([app/routers/telemetria.py](app/routers/telemetria.py)):

1. Busca el dispositivo (404 si no existe) y sus umbrales.
2. Guarda la `Lectura`.
3. Llama a `evaluar_lectura(...)` → nivel `normal` / `alerta` / `emergencia`.
4. Crea una `Alerta` por cada riesgo detectado.
5. **Sincroniza el estado**: si el circuito reportó `valve_open`/`alarm_enabled`, los
   adopta; luego, si la evaluación es emergencia, fuerza `estado_valvula = "cerrada"`.
6. Difunde por WebSocket para el dashboard en vivo.
7. Devuelve el comando `{valvula, buzzer}` al circuito.

---

## 5. El modelo de datos

Cuatro tablas en [app/models.py](app/models.py):

- **Dispositivo** — el nodo de la cocina: estado de válvula, nivel, comando pendiente.
- **Umbral** — límites configurables por dispositivo: `gas_alerta` (1000),
  `gas_emergencia` (2000), `temp_warning` (55), `temp_max` (70).
- **Lectura** — cada muestreo (gas, temperatura, presencia, timestamp).
- **Alerta** — cada evento de riesgo (tipo, nivel, valor, mensaje).

(El documento original menciona *PerfilUso* y *Reporte* —análisis BI— que quedan fuera
de esta versión. La humedad del DHT22 se transmite pero aún no se persiste.)

---

## 6. Mapa de archivos

```
app/
  main.py            Arranca FastAPI, CORS, monta routers y el dashboard estático.
  config.py          Ajustes y umbrales por defecto (1000 / 2000 / 55 / 70).
  database.py        Motor SQLite y sesión por request.
  models.py          Las 4 tablas (SQLModel).
  schemas.py         Formas de entrada/salida (incluye valve_open / alarm_enabled).
  crud.py            Funciones de datos reutilizadas (buscar dispositivo, umbrales).
  websocket.py       Gestor de conexiones del dashboard (broadcast).
  services/
    alertas.py       ★ Lógica pura de estados NORMAL/WARNING/DANGER.
  routers/
    telemetria.py    ★ POST de ingesta (orquesta y sincroniza estado circuito↔API).
    dispositivos.py  Alta, estado, control de válvula (OPEN/CLOSE remoto), umbrales.
    lecturas.py      Historial de lecturas.
    alertas.py       Historial de alertas.
    dashboard_ws.py  WebSocket /ws/dashboard.
static/
  dashboard.html     Pantalla en vivo (tarjetas + log de eventos).
simulador/
  simulador.py       Imita el circuito: envía lecturas con picos y reporta valve_open.
  bridge_serial.py   Puente Proteus → puerto serie → HTTP.
tests/
  test_alertas.py    Lógica de umbrales (incluye reglas de temperatura con/sin presencia).
  test_telemetria.py Ingesta end-to-end.
  test_dispositivos.py Control de válvula y umbrales.
  conftest.py        Base de datos en memoria para los tests.
```

El símbolo ★ marca los dos archivos con la inteligencia del sistema; el resto es
"plomería" (almacenar, exponer endpoints, mostrar).

---

## 7. El contrato con el circuito

Resumen de [circuit-endpoints.md](circuit-endpoints.md), que es lo que implementa el firmware:

- **`POST /api/telemetria`** — envío periódico (cada ~1 s). Incluye lecturas + estado de
  actuadores (`valve_open`, `alarm_enabled`). Devuelve el comando a ejecutar.
- **`GET /api/dispositivos/{id}/comando`** — *polling* de comandos remotos (p. ej. el
  usuario pulsa OPEN en la app y el circuito lo recoge aquí).
- **`POST /api/dispositivos`** — alta única del dispositivo; devuelve el `id` que el
  ESP32 guarda en memoria persistente (NVS/EEPROM).

> El firmware **siempre** ejecuta su evaluación local de seguridad. Si la lectura local
> indica DANGER, cierra la válvula y activa el buzzer **independientemente** del comando
> de la API. La API solo aporta control remoto y confirmación.

---

## 8. Cómo se conecta con la simulación (Proteus)

Proteus no hace peticiones HTTP reales de forma fiable desde un ESP32 simulado. Por eso
se usa un patrón de **puente**:

```
Proteus (UART)  ──►  puerto COM virtual (com0com)  ──►  bridge_serial.py  ──►  HTTP  ──►  API
```

El firmware imprime por serie una línea `gas,temp,presencia`; el script
[bridge_serial.py](simulador/bridge_serial.py) la lee y la reenvía a la API como si
fuera el circuito real. Si el montaje de Proteus permitiera HTTP nativo, podría llamar
directo a `/api/telemetria` sin el puente. Para probar sin Proteus está
[simulador.py](simulador/simulador.py), que genera picos de gas y temperatura.

---

## 9. Estado de las pruebas

Suite con `pytest`. En la última ejecución: **19 pasan, 1 falla**.

- ✅ `test_alertas.py` — lógica de umbrales y reglas de temperatura con/sin presencia.
- ✅ `test_telemetria.py` — ingesta, alertas y cierre por emergencia.
- ⚠️ `test_dispositivos.py::test_cerrar_y_reactivar_valvula` — **falla**: el test espera
  que reactivar la válvula deje `nivel_alerta = "normal"`, pero el handler actual de
  `POST /dispositivos/{id}/valvula` ya no resetea el nivel al reactivar. Es una
  inconsistencia entre el test y el código tras los últimos cambios: hay que decidir cuál
  refleja el comportamiento deseado (resetear el nivel al reabrir, o no).

