"""Funciones de acceso a datos reutilizadas por varios routers."""

from sqlmodel import Session, select

from app.config import settings
from app.models import Dispositivo, Umbral
from app.services.alertas import Umbrales


def get_dispositivo(session: Session, dispositivo_id: int) -> Dispositivo | None:
    return session.get(Dispositivo, dispositivo_id)


def get_or_create_umbral(session: Session, dispositivo_id: int) -> Umbral:
    """Devuelve el umbral del dispositivo, creandolo con valores por defecto si no existe."""
    umbral = session.exec(
        select(Umbral).where(Umbral.dispositivo_id == dispositivo_id)
    ).first()
    if umbral is None:
        umbral = Umbral(
            dispositivo_id=dispositivo_id,
            gas_alerta=settings.gas_alerta_default,
            gas_emergencia=settings.gas_emergencia_default,
            temp_warning=settings.temp_warning_default,
            temp_max=settings.temp_max_default,
        )
        session.add(umbral)
        session.commit()
        session.refresh(umbral)
    return umbral


def umbral_a_dataclass(umbral: Umbral) -> Umbrales:
    return Umbrales(
        gas_alerta=umbral.gas_alerta,
        gas_emergencia=umbral.gas_emergencia,
        temp_warning=umbral.temp_warning,
        temp_max=umbral.temp_max,
    )
