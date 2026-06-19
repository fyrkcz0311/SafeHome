# SafeHome Kitchen Monitor — API (FastAPI)

Backend del sistema IoT de prevención de riesgos en cocinas domésticas
(proyecto **SafeHome Kitchen Monitor**, ver [Proyecto.md](Proyecto.md)).

Recibe la telemetría del circuito (ESP32 + sensor de gas MQ-2, temperatura DHT22 y
presencia PIR), evalúa umbrales de seguridad, genera alertas, ordena el corte o
reactivación de la electroválvula, guarda el historial y alimenta un dashboard en
tiempo real por WebSocket.

## Requisitos
- Python 3.11+ (probado con 3.14)
- Dependencias en [requirements.txt](requirements.txt)

## Instalación
```bash
pip install -r requirements.txt
```

## Ejecutar la API
```bash
uvicorn app.main:app --reload
```
- Documentación interactiva (Swagger): http://localhost:8000/docs
- Dashboard en vivo: http://localhost:8000/static/dashboard.html
- Base de datos: archivo `safehome.db` (SQLite, se crea solo al arrancar).

## Probar sin hardware (simulador)
Con la API corriendo, en otra terminal:
```bash
python simulador/simulador.py
```
Genera lecturas cada 2 s (con picos de alerta a ~420–600 ppm y de emergencia a
≥800 ppm), las envía a `POST /api/telemetria` e imprime el comando devuelto. Abre el
dashboard para verlo en vivo.

## Conectar con Proteus
Proteus no hace peticiones HTTP reales de forma fiable desde un ESP32 simulado. Flujo
recomendado:

1. En el firmware (Arduino/ESP32), imprime cada lectura por el puerto serie, una por
   línea, en formato CSV `gas,temp,presencia` (o JSON). Ej.: `850.0,31.2,1`.
2. Crea un par de puertos COM virtuales con **com0com** (p. ej. `COM4 <-> COM5`).
   Configura el UART de Proteus para que escriba en `COM4`.
3. Lanza el bridge apuntando al otro extremo:
   ```bash
   python simulador/bridge_serial.py --port COM5 --baud 9600 --device 1
   ```
El bridge lee del serie y reenvía a la API igual que el simulador. Si tu montaje de
Proteus sí permite HTTP nativo, puede apuntar directo a `POST /api/telemetria`.

## Endpoints principales
| Método | Ruta | Descripción |
| --- | --- | --- |
| POST | `/api/telemetria` | Ingesta de lectura; devuelve comando (válvula/buzzer) |
| GET | `/api/dispositivos` · `/api/dispositivos/{id}` | Listar / obtener dispositivo |
| POST | `/api/dispositivos` | Crear dispositivo |
| GET | `/api/dispositivos/{id}/estado` | Estado actual + última lectura |
| GET | `/api/dispositivos/{id}/comando` | Comando pendiente (polling del firmware) |
| POST | `/api/dispositivos/{id}/valvula` | Control manual: `{"accion":"cerrar"\|"reactivar"}` |
| GET/POST | `/api/dispositivos/{id}/umbrales` | Consultar / configurar umbrales |
| GET | `/api/lecturas?device_id=&limit=` | Historial de lecturas |
| GET | `/api/alertas?device_id=&limit=` | Historial de alertas |
| WS | `/ws/dashboard` | Stream en tiempo real |

### Ejemplo de telemetría
```bash
curl -X POST http://localhost:8000/api/telemetria \
  -H "Content-Type: application/json" \
  -d '{"device_id":1,"gas_ppm":850,"temperatura":31.2,"presencia":true}'
```
Respuesta (emergencia → corte automático):
```json
{
  "lectura_id": 12, "nivel_alerta": "emergencia", "estado_valvula": "cerrada",
  "comando": {"valvula": "cerrar", "buzzer": true}, "alertas_generadas": 1
}
```

## Umbrales (documento, sección 9.3)
- Gas: **alerta ≥ 400 ppm**, **emergencia ≥ 800 ppm** (corte automático de válvula).
- Temperatura: alerta ≥ 60 °C (configurable por dispositivo).

## Tests
```bash
pytest
```

## Estructura
```
app/        API: main, config, database, models, schemas, crud, websocket
  routers/  telemetria, dispositivos, lecturas, alertas, dashboard_ws
  services/ alertas.py (lógica pura de umbrales)
simulador/  simulador.py (HTTP) y bridge_serial.py (Proteus -> serie -> HTTP)
static/     dashboard.html (tiempo real)
tests/      pruebas pytest
```

## Fuera de alcance v1 (evolución futura)
MQTT, PostgreSQL, Firebase Cloud Messaging y BI/Power BI (perfiles de uso y detección
de anomalías por Z-score). La estructura por routers/servicios deja espacio para añadirlos.
