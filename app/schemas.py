"""Esquemas Pydantic para entrada/salida de la API."""

from datetime import datetime

from pydantic import BaseModel, Field


class TelemetriaIn(BaseModel):
    device_id: int
    gas_ppm: float = Field(ge=0)
    temperatura: float
    presencia: bool = False


class ComandoOut(BaseModel):
    valvula: str = "mantener"   # "cerrar" | "abrir" | "mantener"
    buzzer: bool = False


class TelemetriaOut(BaseModel):
    """Respuesta del POST de telemetria: el firmware actua con este comando."""

    lectura_id: int
    nivel_alerta: str
    estado_valvula: str
    comando: ComandoOut
    alertas_generadas: int


class DispositivoIn(BaseModel):
    nombre: str
    ubicacion: str = "Cocina"


class DispositivoOut(BaseModel):
    model_config = {"from_attributes": True}

    id: int
    nombre: str
    ubicacion: str
    estado_valvula: str
    nivel_alerta: str
    comando_valvula: str
    comando_buzzer: bool
    last_seen: datetime | None


class EstadoOut(BaseModel):
    dispositivo_id: int
    nombre: str
    ubicacion: str
    estado_valvula: str
    nivel_alerta: str
    last_seen: datetime | None
    ultima_lectura: "LecturaOut | None" = None


class LecturaOut(BaseModel):
    id: int
    dispositivo_id: int
    gas_ppm: float
    temperatura: float
    presencia: bool
    timestamp: datetime


class AlertaOut(BaseModel):
    id: int
    dispositivo_id: int
    tipo: str
    nivel: str
    valor: float
    mensaje: str
    atendida: bool
    timestamp: datetime


class ValvulaIn(BaseModel):
    accion: str  # "cerrar" | "reactivar"


class UmbralIn(BaseModel):
    gas_alerta: float | None = None
    gas_emergencia: float | None = None
    temp_max: float | None = None


class UmbralOut(BaseModel):
    dispositivo_id: int
    gas_alerta: float
    gas_emergencia: float
    temp_max: float
