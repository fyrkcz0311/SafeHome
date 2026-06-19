"""Modelos de datos (tablas SQLite) con SQLModel.

Basado en el diagrama de clases / entidad-relacion del documento, recortado al
alcance v1: dispositivo, umbral, lectura y alerta.
"""

from datetime import datetime, timezone

from sqlmodel import Field, SQLModel


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Dispositivo(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    nombre: str
    ubicacion: str = "Cocina"
    estado_valvula: str = "abierta"      # "abierta" | "cerrada"
    nivel_alerta: str = "normal"         # "normal" | "alerta" | "emergencia"
    comando_valvula: str = "mantener"    # comando pendiente para el firmware (polling)
    comando_buzzer: bool = False
    last_seen: datetime | None = None


class Umbral(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    dispositivo_id: int = Field(foreign_key="dispositivo.id", index=True, unique=True)
    gas_alerta: float = 400
    gas_emergencia: float = 800
    temp_max: float = 60


class Lectura(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    dispositivo_id: int = Field(foreign_key="dispositivo.id", index=True)
    gas_ppm: float
    temperatura: float
    presencia: bool = False
    timestamp: datetime = Field(default_factory=_utcnow, index=True)


class Alerta(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    dispositivo_id: int = Field(foreign_key="dispositivo.id", index=True)
    tipo: str                            # "gas" | "temperatura"
    nivel: str                           # "alerta" | "emergencia"
    valor: float
    mensaje: str
    atendida: bool = False
    timestamp: datetime = Field(default_factory=_utcnow, index=True)
