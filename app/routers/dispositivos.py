"""Gestion de dispositivos: alta, estado, control de valvula y umbrales."""

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, desc, select

from app.crud import get_dispositivo, get_or_create_umbral
from app.database import get_session
from app.models import Dispositivo, Lectura
from app.schemas import (
    DispositivoIn,
    DispositivoOut,
    EstadoOut,
    LecturaOut,
    UmbralIn,
    UmbralOut,
    ValvulaIn,
)
from app.websocket import manager

router = APIRouter(prefix="/api/dispositivos", tags=["dispositivos"])


@router.post("", response_model=DispositivoOut, status_code=201)
def crear_dispositivo(datos: DispositivoIn, session: Session = Depends(get_session)):
    dispositivo = Dispositivo(nombre=datos.nombre, ubicacion=datos.ubicacion)
    session.add(dispositivo)
    session.commit()
    session.refresh(dispositivo)
    # Crea sus umbrales por defecto.
    get_or_create_umbral(session, dispositivo.id)
    return dispositivo


@router.get("", response_model=list[DispositivoOut])
def listar_dispositivos(session: Session = Depends(get_session)):
    return session.exec(select(Dispositivo)).all()


@router.get("/{dispositivo_id}", response_model=DispositivoOut)
def obtener_dispositivo(dispositivo_id: int, session: Session = Depends(get_session)):
    dispositivo = get_dispositivo(session, dispositivo_id)
    if dispositivo is None:
        raise HTTPException(status_code=404, detail="Dispositivo no encontrado")
    return dispositivo


@router.get("/{dispositivo_id}/estado", response_model=EstadoOut)
def estado_dispositivo(dispositivo_id: int, session: Session = Depends(get_session)):
    dispositivo = get_dispositivo(session, dispositivo_id)
    if dispositivo is None:
        raise HTTPException(status_code=404, detail="Dispositivo no encontrado")
    ultima = session.exec(
        select(Lectura)
        .where(Lectura.dispositivo_id == dispositivo_id)
        .order_by(desc(Lectura.timestamp))
    ).first()
    return EstadoOut(
        dispositivo_id=dispositivo.id,
        nombre=dispositivo.nombre,
        ubicacion=dispositivo.ubicacion,
        estado_valvula=dispositivo.estado_valvula,
        nivel_alerta=dispositivo.nivel_alerta,
        last_seen=dispositivo.last_seen,
        ultima_lectura=LecturaOut(**ultima.model_dump()) if ultima else None,
    )


@router.get("/{dispositivo_id}/comando")
def obtener_comando(dispositivo_id: int, session: Session = Depends(get_session)):
    """El firmware puede sondear este endpoint para obtener el comando pendiente."""
    dispositivo = get_dispositivo(session, dispositivo_id)
    if dispositivo is None:
        raise HTTPException(status_code=404, detail="Dispositivo no encontrado")
    return {"valvula": dispositivo.comando_valvula, "buzzer": dispositivo.comando_buzzer}


@router.post("/{dispositivo_id}/valvula", response_model=DispositivoOut)
async def controlar_valvula(
    dispositivo_id: int,
    datos: ValvulaIn,
    session: Session = Depends(get_session),
):
    dispositivo = get_dispositivo(session, dispositivo_id)
    if dispositivo is None:
        raise HTTPException(status_code=404, detail="Dispositivo no encontrado")

    if datos.accion == "cerrar":
        dispositivo.estado_valvula = "cerrada"
        dispositivo.comando_valvula = "cerrar"
    elif datos.accion == "reactivar":
        dispositivo.estado_valvula = "abierta"
        dispositivo.comando_valvula = "abrir"
    else:
        raise HTTPException(status_code=400, detail="Accion invalida (use 'cerrar' o 'reactivar')")

    dispositivo.last_seen = datetime.now(timezone.utc)
    session.add(dispositivo)
    session.commit()
    session.refresh(dispositivo)

    await manager.broadcast(
        {
            "tipo": "valvula",
            "device_id": dispositivo_id,
            "estado_valvula": dispositivo.estado_valvula,
            "accion": datos.accion,
        }
    )
    return dispositivo


@router.get("/{dispositivo_id}/umbrales", response_model=UmbralOut)
def obtener_umbrales(dispositivo_id: int, session: Session = Depends(get_session)):
    if get_dispositivo(session, dispositivo_id) is None:
        raise HTTPException(status_code=404, detail="Dispositivo no encontrado")
    umbral = get_or_create_umbral(session, dispositivo_id)
    return UmbralOut(**umbral.model_dump(exclude={"id"}))


@router.post("/{dispositivo_id}/umbrales", response_model=UmbralOut)
def configurar_umbrales(
    dispositivo_id: int,
    datos: UmbralIn,
    session: Session = Depends(get_session),
):
    if get_dispositivo(session, dispositivo_id) is None:
        raise HTTPException(status_code=404, detail="Dispositivo no encontrado")
    umbral = get_or_create_umbral(session, dispositivo_id)
    if datos.gas_alerta is not None:
        umbral.gas_alerta = datos.gas_alerta
    if datos.gas_emergencia is not None:
        umbral.gas_emergencia = datos.gas_emergencia
    if datos.temp_warning is not None:
        umbral.temp_warning = datos.temp_warning
    if datos.temp_max is not None:
        umbral.temp_max = datos.temp_max
    session.add(umbral)
    session.commit()
    session.refresh(umbral)
    return UmbralOut(**umbral.model_dump(exclude={"id"}))
