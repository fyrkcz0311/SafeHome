"""Logica de negocio para evaluar lecturas contra umbrales de seguridad.

Funcion pura y testeable: no toca la base de datos. Recibe una lectura y los
umbrales del dispositivo, y devuelve el nivel de riesgo, las alertas a registrar
y el comando que debe ejecutar el dispositivo (electrovalvula + zumbador).

Umbrales segun circuit.md:
- Gas: alerta >= 1000 ppm, emergencia >= 2000 ppm.
- Temperatura (solo evaluada si no hay presencia):
    warning >= 55 C, danger >= 70 C.
"""

from dataclasses import dataclass, field


@dataclass
class Umbrales:
    gas_alerta: float = 1000
    gas_emergencia: float = 2000
    temp_warning: float = 55
    temp_max: float = 70


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
    """Evalua una lectura y devuelve nivel, alertas y comando para el dispositivo.

    La temperatura solo se evalua cuando no hay presencia (PIR sin deteccion).
    """
    alertas: list[AlertaEval] = []
    nivel = "normal"
    comando = Comando()

    # --- Gas (independiente de presencia) ---
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

    # --- Temperatura (solo cuando no hay presencia) ---
    if not presencia:
        if temperatura >= umbrales.temp_max:
            if nivel != "emergencia":
                nivel = "emergencia"
                comando = Comando(valvula="cerrar", buzzer=True)
            alertas.append(
                AlertaEval(
                    tipo="temperatura",
                    nivel="emergencia",
                    valor=temperatura,
                    mensaje=(
                        f"Temperatura peligrosa: {temperatura:.1f} C sin presencia "
                        f"(>= {umbrales.temp_max:.1f}). Cierre automatico."
                    ),
                )
            )
        elif temperatura >= umbrales.temp_warning:
            if nivel == "normal":
                nivel = "alerta"
            alertas.append(
                AlertaEval(
                    tipo="temperatura",
                    nivel="alerta",
                    valor=temperatura,
                    mensaje=(
                        f"Temperatura elevada: {temperatura:.1f} C sin presencia "
                        f"(>= {umbrales.temp_warning:.1f})."
                    ),
                )
            )

    return Resultado(nivel=nivel, alertas=alertas, comando=comando)
