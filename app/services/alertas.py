"""Logica de negocio para evaluar lecturas contra umbrales de seguridad.

Funcion pura y testeable: no toca la base de datos. Recibe una lectura y los
umbrales del dispositivo, y devuelve el nivel de riesgo, las alertas a registrar
y el comando que debe ejecutar el dispositivo (electrovalvula + zumbador).

Umbrales por defecto segun el documento del proyecto (seccion 9.3, Modulo 1):
alerta a 400 ppm, emergencia a 800 ppm.
"""

from dataclasses import dataclass, field


@dataclass
class Umbrales:
    gas_alerta: float = 400
    gas_emergencia: float = 800
    temp_max: float = 60


@dataclass
class AlertaEval:
    tipo: str          # "gas" | "temperatura"
    nivel: str         # "alerta" | "emergencia"
    valor: float
    mensaje: str


@dataclass
class Comando:
    valvula: str = "mantener"   # "cerrar" | "abrir" | "mantener"
    buzzer: bool = False


@dataclass
class Resultado:
    nivel: str                          # "normal" | "alerta" | "emergencia"
    alertas: list[AlertaEval] = field(default_factory=list)
    comando: Comando = field(default_factory=Comando)


def evaluar_lectura(
    gas_ppm: float,
    temperatura: float,
    presencia: bool,
    umbrales: Umbrales,
) -> Resultado:
    """Evalua una lectura y devuelve nivel, alertas y comando para el dispositivo."""
    alertas: list[AlertaEval] = []
    nivel = "normal"
    comando = Comando()

    # --- Gas ---
    if gas_ppm >= umbrales.gas_emergencia:
        nivel = "emergencia"
        comando = Comando(valvula="cerrar", buzzer=True)
        alertas.append(
            AlertaEval(
                tipo="gas",
                nivel="emergencia",
                valor=gas_ppm,
                mensaje=(
                    f"Concentracion de gas peligrosa: {gas_ppm:.0f} ppm "
                    f"(>= {umbrales.gas_emergencia:.0f}). Cierre automatico de electrovalvula."
                ),
            )
        )
    elif gas_ppm >= umbrales.gas_alerta:
        nivel = "alerta"
        alertas.append(
            AlertaEval(
                tipo="gas",
                nivel="alerta",
                valor=gas_ppm,
                mensaje=f"Concentracion de gas elevada: {gas_ppm:.0f} ppm (>= {umbrales.gas_alerta:.0f}).",
            )
        )

    # --- Temperatura ---
    if temperatura >= umbrales.temp_max:
        if nivel == "normal":
            nivel = "alerta"
        alertas.append(
            AlertaEval(
                tipo="temperatura",
                nivel="alerta",
                valor=temperatura,
                mensaje=f"Temperatura elevada: {temperatura:.1f} C (>= {umbrales.temp_max:.1f}).",
            )
        )

    return Resultado(nivel=nivel, alertas=alertas, comando=comando)
