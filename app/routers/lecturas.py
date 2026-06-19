"""Consulta del historial de lecturas (telemetria)."""

from fastapi import APIRouter, Depends, Query
from sqlmodel import Session, desc, select

from app.database import get_session
from app.models import Lectura
from app.schemas import LecturaOut

router = APIRouter(prefix="/api/lecturas", tags=["lecturas"])


@router.get("", response_model=list[LecturaOut])
def listar_lecturas(
    device_id: int | None = None,
    limit: int = Query(default=100, le=1000),
    session: Session = Depends(get_session),
):
    consulta = select(Lectura)
    if device_id is not None:
        consulta = consulta.where(Lectura.dispositivo_id == device_id)
    consulta = consulta.order_by(desc(Lectura.timestamp)).limit(limit)
    return session.exec(consulta).all()
