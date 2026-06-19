
| Decisión | Elección | Por qué |
| --- | --- | --- |
| Framework | **FastAPI** | Rápido, tipado, genera Swagger automático y trae WebSockets nativos. |
| Comunicación circuito → API | **HTTP REST (POST)** | Lo más simple y universal: el dispositivo solo hace un POST con JSON. |
| Base de datos | **SQLite** | Cero configuración, un solo archivo. Perfecto para demo/proyecto de curso. |
| ORM | **SQLModel** | Une SQLAlchemy + Pydantic: el mismo modelo sirve de tabla y de validación. |
| Tiempo real | **WebSocket** | Empuja cada lectura al dashboard sin que el navegador tenga que preguntar. |
| Pruebas | **pytest + TestClient** | Se escribieron **antes** del código (TDD). |

### La idea clave: la API es "agnóstica al origen"
La API **no sabe** si los datos vienen de un ESP32 real, de Proteus o de un script.
Solo recibe un JSON por HTTP. Eso permitió desarrollarla y probarla por completo sin
hardware, y deja la puerta abierta a cualquier fuente.

### Por qué la respuesta del POST lleva el comando
El dispositivo no mantiene una conexión abierta: hace un POST y se desconecta. Por eso,
**la decisión (cerrar válvula / activar zumbador) viaja de vuelta en la respuesta del
mismo POST**. El firmware lee esa respuesta y actúa. Como alternativa existe
`GET /comando` para que el firmware "pregunte" el comando pendiente (polling).

---

## 3. Arquitectura y flujo de datos

```
   ┌─────────────┐   HTTP POST /api/telemetria    ┌──────────────────────────┐
   │  CIRCUITO   │  {gas, temp, presencia}        │        API (FastAPI)     │
   │ ESP32 +     │ ─────────────────────────────► │                          │
   │ sensores    │ ◄───────────────────────────── │  1. guarda la Lectura    │
   └─────────────┘   respuesta: {valvula, buzzer} │  2. evalúa umbrales      │
        (Proteus / simulador / bridge serie)      │  3. crea Alertas         │
                                                   │  4. actualiza Dispositivo│
                                                   │  5. broadcast WebSocket  │
                                                   │  6. responde el comando  │
                                                   └───────────┬──────────────┘
                                                               │
                          ┌────────────────────────────────────┼───────────────┐
                          ▼                                     ▼               ▼
                    ┌───────────┐                        ┌────────────┐   ┌──────────┐
                    │  SQLite   │                        │ Dashboard  │   │  Swagger │
                    │ safehome  │                        │  (WS live) │   │  /docs   │
                    └───────────┘                        └────────────┘   └──────────┘
```

**Paso a paso cuando llega una lectura** (corazón del sistema, en
[app/routers/telemetria.py](app/routers/telemetria.py)):

1. Busca el dispositivo (404 si no existe) y sus umbrales.
2. Guarda la `Lectura` en la base de datos.
3. Llama a `evaluar_lectura(...)` → decide el nivel (`normal` / `alerta` / `emergencia`).
4. Por cada riesgo detectado, crea una `Alerta`.
5. Actualiza el `Dispositivo`: nivel, última conexión y, si es emergencia, deja la
   válvula como `cerrada`.
6. Hace `broadcast` por WebSocket para que el dashboard lo muestre al instante.
7. Devuelve el comando `{valvula, buzzer}` al circuito.

---

## 4. La lógica de seguridad (el "cerebro")

Está aislada en [app/services/alertas.py](app/services/alertas.py) como una **función
pura**: recibe números, devuelve una decisión, y **no toca la base de datos**. Eso la
hace fácil de probar y de razonar.

Reglas (umbrales del documento, sección 9.3):

- `gas ≥ 800 ppm` → **emergencia**: alerta + **cerrar válvula** + zumbador.
- `gas ≥ 400 ppm` → **alerta**: solo aviso (no corta el gas).
- `temperatura ≥ 60 °C` → **alerta** de temperatura.
- Por debajo → **normal**.

Separar esta lógica del resto fue una decisión deliberada: el archivo de la API
"orquesta" (guarda, difunde, responde) pero **quién decide el peligro** es esta función.

---

## 5. El modelo de datos

Cuatro tablas en [app/models.py](app/models.py), derivadas del diagrama entidad-relación
del documento:

- **Dispositivo** — el nodo de la cocina: estado de la válvula, nivel de alerta, comando pendiente.
- **Umbral** — los límites configurables por dispositivo (400 / 800 / 60).
- **Lectura** — cada muestreo de los sensores (telemetría histórica).
- **Alerta** — cada evento de riesgo detectado.

(Las entidades *PerfilUso* y *Reporte* del documento, que son análisis BI, se dejaron
fuera de esta primera versión.)

---

## 6. Mapa de archivos

```
app/
  main.py            Arranca FastAPI, CORS, monta routers y el dashboard estático.
  config.py          Ajustes y umbrales por defecto.
  database.py        Motor SQLite y sesión por request.
  models.py          Las 4 tablas (SQLModel).
  schemas.py         Formas de entrada/salida (Pydantic) de la API.
  crud.py            Funciones de datos reutilizadas (buscar dispositivo, umbrales).
  websocket.py       Gestor de conexiones del dashboard (broadcast).
  services/
    alertas.py       ★ Lógica pura de umbrales (el cerebro).
  routers/
    telemetria.py    ★ POST de ingesta (orquesta todo el flujo).
    dispositivos.py  Alta, estado, control de válvula, umbrales.
    lecturas.py      Historial de lecturas.
    alertas.py       Historial de alertas.
    dashboard_ws.py  WebSocket /ws/dashboard.
static/
  dashboard.html     Pantalla en vivo (tarjetas + log de eventos).
simulador/
  simulador.py       Imita el circuito enviando lecturas por HTTP (prueba sin hardware).
  bridge_serial.py   Puente Proteus → puerto serie → HTTP.
tests/
  test_alertas.py    Prueban la lógica de umbrales.
  test_telemetria.py Prueban la ingesta end-to-end.
  test_dispositivos.py Prueban control de válvula y umbrales.
  conftest.py        Base de datos en memoria para los tests.
```

El símbolo ★ marca los dos archivos donde está la inteligencia del sistema; el resto es
"plomería" (almacenar, exponer endpoints, mostrar).

---

## 7. Cómo se conecta con la simulación (Proteus)

Proteus no hace peticiones HTTP reales de forma fiable desde un ESP32 simulado. Por eso
se usa un patrón de **puente**:

```
Proteus (UART)  ──►  puerto COM virtual (com0com)  ──►  bridge_serial.py  ──►  HTTP  ──►  API
```

El firmware solo imprime por el puerto serie una línea `gas,temp,presencia`; el script
[bridge_serial.py](simulador/bridge_serial.py) la lee y la reenvía a la API como si fuera
el circuito real. Si el montaje de Proteus permitiera HTTP nativo, podría llamar directo
a `/api/telemetria` sin el puente.

---

