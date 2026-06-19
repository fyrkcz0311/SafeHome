"""Ingesta de telemetria desde el circuito (ESP32 / simulador / bridge Proteus)."""

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session

from app.crud import get_dispositivo, get_or_create_umbral, umbral_a_dataclass
from app.database import get_session
from app.models import Alerta, Lectura
from app.schemas import ComandoOut, TelemetriaIn, TelemetriaOut
from app.services.alertas import evaluar_lectura
from app.websocket import manager

router = APIRouter(prefix="/api", tags=["telemetria"])


@router.post("/telemetria", response_model=TelemetriaOut)
async def recibir_telemetria(
    datos: TelemetriaIn,
    session: Session = Depends(get_session),
):
    dispositivo = get_dispositivo(session, datos.device_id)
    if dispositivo is None:
        raise HTTPException(status_code=404, detail="Dispositivo no encontrado")

    umbral = get_or_create_umbral(session, datos.device_id)

    # 1. Guardar la lectura.
    lectura = Lectura(
        dispositivo_id=datos.device_id,
        gas_ppm=datos.gas_ppm,
        temperatura=datos.temperatura,
        presencia=datos.presencia,
    )
    session.add(lectura)

    # 2. Evaluar contra umbrales (logica pura).
    resultado = evaluar_lectura(
        gas_ppm=datos.gas_ppm,
        temperatura=datos.temperatura,
        presencia=datos.presencia,
        umbrales=umbral_a_dataclass(umbral),
    )

    # 3. Registrar alertas.
    for a in resultado.alertas:
        session.add(
            Alerta(
                dispositivo_id=datos.device_id,
                tipo=a.tipo,
                nivel=a.nivel,
                valor=a.valor,
                mensaje=a.mensaje,
            )
        )

    # 4. Actualizar estado del dispositivo.
    #    Sincronizar desde lo que el circuito reporta (botones fisicos, accion local).
    #    La evaluacion de la API puede sobreescribir por seguridad.
    if datos.valve_open is not None:
        dispositivo.estado_valvula = "abierta" if datos.valve_open else "cerrada"
    if datos.alarm_enabled is not None:
        dispositivo.comando_buzzer = datos.alarm_enabled

    dispositivo.nivel_alerta = resultado.nivel
    dispositivo.last_seen = datetime.now(timezone.utc)
    dispositivo.comando_valvula = resultado.comando.valvula
    dispositivo.comando_buzzer = resultado.comando.buzzer
    if resultado.comando.valvula == "cerrar":
        dispositivo.estado_valvula = "cerrada"
    session.add(dispositivo)

    session.commit()
    session.refresh(lectura)

    # 5. Difundir al dashboard en vivo.
    await manager.broadcast(
        {
            "tipo": "telemetria",
            "device_id": datos.device_id,
            "gas_ppm": datos.gas_ppm,
            "temperatura": datos.temperatura,
            "presencia": datos.presencia,
            "nivel_alerta": resultado.nivel,
            "estado_valvula": dispositivo.estado_valvula,
            "alertas": [
                {"tipo": a.tipo, "nivel": a.nivel, "mensaje": a.mensaje}
                for a in resultado.alertas
            ],
            "timestamp": lectura.timestamp.isoformat(),
        }
    )

    # 6. Responder el comando al firmware.
    return TelemetriaOut(
        lectura_id=lectura.id,
        nivel_alerta=resultado.nivel,
        estado_valvula=dispositivo.estado_valvula,
        comando=ComandoOut(
            valvula=resultado.comando.valvula,
            buzzer=resultado.comando.buzzer,
        ),
        alertas_generadas=len(resultado.alertas),
    )
