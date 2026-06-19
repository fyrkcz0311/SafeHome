# Endpoints para el circuito (ESP32)

Documentación de los endpoints HTTP que el firmware del ESP32 debe consumir
para integrarse con la API SafeHome Kitchen Monitor.

---

## POST `/api/telemetria`

Envío periódico de lecturas de sensores. Es el endpoint principal del circuito.

### Request

```json
{
  "device_id": 1,
  "gas_ppm": 1250.0,
  "temperatura": 56.8,
  "presencia": false,
  "valve_open": true,
  "alarm_enabled": false
}
```

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `device_id` | int | ID del dispositivo asignado al crear el circuito |
| `gas_ppm` | float | Concentración de gas combustible (MQ-2) en ppm, >= 0 |
| `temperatura` | float | Temperatura ambiente (DHT22) en °C |
| `presencia` | bool | `true` si el PIR detecta presencia, `false` si está despejado |
| `valve_open` | bool \| null | Estado actual de la válvula tras la acción local del circuito. `true` = abierta, `false` = cerrada, `null` = no reportar. |
| `alarm_enabled` | bool \| null | Estado actual de la alarma tras la acción local del circuito. `true` = activa, `false` = apagada, `null` = no reportar. |

### Response (200 OK)

```json
{
  "lectura_id": 42,
  "nivel_alerta": "alerta",
  "estado_valvula": "abierta",
  "comando": {
    "valvula": "mantener",
    "buzzer": false
  },
  "alertas_generadas": 1
}
```

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `nivel_alerta` | string | Estado del sistema: `"normal"` \| `"alerta"` \| `"emergencia"` |
| `estado_valvula` | string | Estado actual de la electroválvula: `"abierta"` \| `"cerrada"` |
| `comando.valvula` | string | Acción a ejecutar: `"mantener"` \| `"cerrar"` \| `"abrir"` |
| `comando.buzzer` | bool | `true` = activar alarma, `false` = apagada |
| `alertas_generadas` | int | Cantidad de alertas registradas con esta lectura |

### Sincronización de estado circuito ↔ API

El circuito evalúa y actúa localmente (botones físicos, auto-cierre por DANGER).
Para mantener la API sincronizada, cada envío de telemetría debe incluir el
estado actual de sus actuadores:

- `valve_open`: estado real de la electroválvula después de la acción local.
- `alarm_enabled`: estado real del buzzer después de la acción local.

La API aplica estas reglas al recibir la telemetría:

1. Toma el estado reportado por el circuito como base (`estado_valvula`,
   `comando_buzzer`).
2. Si su propia evaluación determina **DANGER**, sobreescribe
   `estado_valvula = "cerrada"` (la seguridad prevalece).
3. Devuelve en la respuesta el comando que el circuito debe ejecutar como
   siguiente acción.

Esto permite que la API refleje fielmente aperturas/cierres manuales, y a la
vez pueda forzar un cierre de emergencia si la evaluación lo requiere.

### Interpretación de comandos por el firmware

| comando.valvula | comando.buzzer | Acción del circuito |
|-----------------|----------------|---------------------|
| `"mantener"` | `false` | No cambiar nada |
| `"cerrar"` | `true` | Cerrar electroválvula + activar buzzer |
| `"abrir"` | `false` | Abrir electroválvula |

> **Nota de seguridad**: El circuito **siempre** ejecuta su propia evaluación local
> de seguridad. Si la lectura local indica DANGER, el circuito debe cerrar la
> válvula y activar el buzzer **independentemente** del comando devuelto por la
> API. La API solo envía comandos de control remoto o confirmación del estado
> evaluado.

### Errors

| Status | Significado |
|--------|-------------|
| 404 | `device_id` no registrado. Crear el dispositivo antes de enviar telemetría. |
| 422 | Datos inválidos (gas_ppm negativo, campos faltantes). |

---

## GET `/api/dispositivos/{device_id}/comando`

Polling de comandos remotos. El circuito puede consultar este endpoint entre
envíos de telemetría para recibir órdenes enviadas desde la app o el panel web.

### Request

```
GET /api/dispositivos/1/comando
```

### Response (200)

```json
{
  "valvula": "mantener",
  "buzzer": false
}
```

Mismos campos que `comando` en la respuesta de telemetría.

### Cuándo usarlo

- Después de que el usuario pulse el botón **OPEN** en la app/web, el comando
  queda pendiente hasta que el circuito lo recoja por este endpoint.
- El circuito debería hacer polling **cada 1-2 segundos** para mantener la
  capacidad de respuesta remota.

---

## POST `/api/dispositivos` (solo setup)

Creación del dispositivo en la API. Se ejecuta una única vez en la primera
configuración del ESP32.

### Request

```json
{
  "nombre": "Cocina Principal",
  "ubicacion": "Piso 1"
}
```

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `nombre` | string | Nombre descriptivo del dispositivo |
| `ubicacion` | string | Ubicación física (opcional, default `"Cocina"`) |

### Response (201 Created)

```json
{
  "id": 1,
  "nombre": "Cocina Principal",
  "ubicacion": "Piso 1",
  "estado_valvula": "abierta",
  "nivel_alerta": "normal",
  "comando_valvula": "mantener",
  "comando_buzzer": false,
  "last_seen": null
}
```

El `id` devuelto es el `device_id` que se usará en adelante. Debe guardarse en
la memoria persistente del ESP32 (EEPROM / NVS).

---

## Ejemplo de ciclo completo del firmware

```
Cada 1 segundo:
  1. Leer MQ-2, DHT22, PIR
  2. Leer botones físicos OPEN / CLOSE
  3. Evaluar estado localmente (NORMAL / WARNING / DANGER)
  4. Actualizar LEDs, buzzer y válvula según estado local
  5. Enviar POST /api/telemetria incluyendo:
     - Lecturas de sensores (gas, temperatura, presencia)
     - Estado actual de actuadores (valve_open, alarm_enabled)
  6. Si la respuesta trae un comando diferente al accionado localmente,
     ejecutarlo (ej: abrir válvula por comando remoto)
  7. Hacer GET /api/dispositivos/{id}/comando para recoger comandos
     remotos pendientes
```

> La evaluación local (paso 3) sigue las reglas de `circuit.md`:
> gas >= 2000 ppm → DANGER, gas >= 1000 ppm → WARNING,
> temperatura >= 70 °C sin presencia → DANGER,
> temperatura >= 55 °C sin presencia → WARNING.
