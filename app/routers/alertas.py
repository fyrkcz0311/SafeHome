"""Consulta del historial de alertas."""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlmodel import Session, desc, select

from app.database import get_session
from app.models import Alerta
from app.schemas import AlertaOut

router = APIRouter(prefix="/api/alertas", tags=["alertas"])


@router.get("", response_model=list[AlertaOut])
def listar_alertas(
    device_id: int | None = None,
    limit: int = Query(default=100, le=1000),
    session: Session = Depends(get_session),
):
    consulta = select(Alerta)
    if device_id is not None:
        consulta = consulta.where(Alerta.dispositivo_id == device_id)
    consulta = consulta.order_by(desc(Alerta.timestamp)).limit(limit)
    return session.exec(consulta).all()


@router.post("/{alerta_id}/atender", response_model=AlertaOut)
def atender_alerta(alerta_id: int, session: Session = Depends(get_session)):
    alerta = session.get(Alerta, alerta_id)
    if alerta is None:
        raise HTTPException(status_code=404, detail="Alerta no encontrada")
    alerta.atendida = True
    session.add(alerta)
    session.commit()
    session.refresh(alerta)
    return alerta
