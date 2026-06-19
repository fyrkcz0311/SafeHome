# Sistema IoT de Detección de Fugas de Gas para Cocina

## Descripción

El sistema implementa un nodo IoT basado en ESP32 para supervisar las condiciones de seguridad de una cocina doméstica. Su objetivo es detectar fugas de gas, condiciones anormales de temperatura y ausencia de personas, permitiendo actuar de forma automática ante situaciones peligrosas.

Las decisiones críticas se ejecutan localmente en el dispositivo, por lo que la seguridad no depende de la disponibilidad de Internet o del servidor.

---

# Componentes

## Sensores

### MQ-2

Permite medir la concentración de gas combustible.

### DHT22

Permite obtener:

* Temperatura ambiente.
* Humedad relativa.

### PIR

Permite detectar la presencia de personas en la cocina.

---

## Actuadores

### Electroválvula

Controla el suministro de gas.

### Buzzer

Genera una alarma sonora ante situaciones de emergencia.

### Indicadores LED

* Verde: estado normal.
* Amarillo: advertencia.
* Rojo: emergencia.

---

## Botones físicos

### OPEN

Permite abrir manualmente la válvula.

La apertura solamente es posible cuando el sistema no se encuentra en estado DANGER.

### CLOSE

Permite cerrar manualmente la válvula en cualquier momento.

---

# Ciclo de operación

Cada segundo el ESP32 ejecuta las siguientes tareas:

1. Lectura de sensores.
2. Procesamiento de botones físicos.
3. Evaluación del estado del sistema.
4. Actualización de actuadores.
5. Generación de telemetría.

---

# Estados del sistema

## NORMAL

### Condiciones

* Gas < 1000 ppm.
* Temperatura < 55 °C.
* Sin condiciones peligrosas.

### Acciones

* LED verde encendido.
* Alarma apagada.
* La válvula conserva su estado actual.

---

## WARNING

### Condiciones

* Concentración de gas mayor o igual a 1000 ppm.

o

* Temperatura mayor o igual a 55 °C y ausencia de personas.

### Acciones

* LED amarillo encendido.
* Alarma apagada.
* La válvula conserva su estado actual.

---

## DANGER

### Condiciones

* Concentración de gas mayor o igual a 2000 ppm.

o

* Temperatura mayor o igual a 70 °C y ausencia de personas.

### Acciones

* LED rojo encendido.
* Activación del buzzer.
* Cierre automático de la válvula.

---

# Filosofía de seguridad

El sistema puede cerrar automáticamente el suministro de gas, pero nunca realiza una apertura automática.

La reapertura requiere una acción explícita del usuario mediante:

* Botón físico OPEN.
* Aplicación móvil.
* Panel web.
* API REST.

---

# Información generada por el dispositivo

El ESP32 genera continuamente:

* Concentración de gas (ppm).
* Temperatura.
* Humedad.
* Presencia.
* Estado del sistema.
* Estado de la válvula.
* Estado de la alarma.

---

# Integración con la API

La API tiene una función de supervisión y administración, pero no participa en la lógica crítica de seguridad.

## Envío de telemetría

El dispositivo enviará periódicamente:

```json
{
  "deviceId": "ESP32-001",
  "gas": 1250,
  "temperature": 56.8,
  "humidity": 63.2,
  "presence": false,
  "status": "WARNING",
  "valveOpen": true,
  "alarmEnabled": false
}
```

---

## Recepción de comandos

La aplicación podrá enviar comandos remotos.

### Abrir válvula

```json
{
  "action": "OPEN_VALVE"
}
```

### Cerrar válvula

```json
{
  "action": "CLOSE_VALVE"
}
```

Los comandos remotos tendrán el mismo efecto que los botones físicos.

---

# Registro histórico

La API almacenará:

## Lecturas

* Gas.
* Temperatura.
* Humedad.
* Presencia.

## Alertas

* WARNING.
* DANGER.

## Eventos

### Eventos automáticos

* WARNING_DETECTED
* DANGER_DETECTED
* AUTO_VALVE_CLOSED
* ALARM_ENABLED
* ALARM_DISABLED

### Eventos manuales

* VALVE_OPENED_MANUALLY
* VALVE_CLOSED_MANUALLY

### Eventos remotos

* VALVE_OPENED_REMOTELY
* VALVE_CLOSED_REMOTELY

---

# Dashboard

La aplicación permitirá visualizar en tiempo real:

* Concentración de gas.
* Temperatura.
* Humedad.
* Presencia.
* Estado actual del sistema.
* Estado de la válvula.
* Estado de la alarma.
* Historial de eventos y alertas.

---

# Principio fundamental

Las funciones críticas de seguridad se ejecutan localmente en el ESP32.

La API se utiliza para monitoreo, almacenamiento histórico, configuración y control remoto, pero la detección y respuesta ante una emergencia no dependen de ella.
