"""Simulador del circuito: genera lecturas y las envia por HTTP a la API.

Permite probar toda la API end-to-end sin Proteus ni hardware. Cada ~2 segundos
genera valores de gas, temperatura y presencia (con picos ocasionales que disparan
alerta y emergencia) y hace POST a /api/telemetria, mostrando el comando recibido.

Uso:
    python simulador/simulador.py [--api http://localhost:8000] [--device 1] [--intervalo 2]
"""

import argparse
import random
import sys
import time

import httpx


def asegurar_dispositivo(api: str, device_id: int) -> int:
    """Crea un dispositivo si el indicado no existe; devuelve el id a usar."""
    r = httpx.get(f"{api}/api/dispositivos/{device_id}")
    if r.status_code == 200:
        return device_id
    nuevo = httpx.post(f"{api}/api/dispositivos", json={"nombre": "Cocina Simulada"})
    nuevo.raise_for_status()
    nid = nuevo.json()["id"]
    print(f"[sim] Dispositivo {device_id} no existia; creado dispositivo {nid}.")
    return nid


def generar_lectura(t: int) -> dict:
    """Genera una lectura. Cada ~15 ciclos provoca un pico de gas."""
    gas = random.uniform(80, 250)
    temp = random.uniform(22, 35)
    presencia = random.random() < 0.6

    if t % 15 == 0 and t > 0:
        gas = random.uniform(820, 1200)   # emergencia
        print("[sim] >> Inyectando pico de EMERGENCIA de gas")
    elif t % 7 == 0 and t > 0:
        gas = random.uniform(420, 600)    # alerta
        print("[sim] >> Inyectando nivel de ALERTA de gas")

    return {"gas_ppm": round(gas, 1), "temperatura": round(temp, 1), "presencia": presencia}


def main() -> int:
    parser = argparse.ArgumentParser(description="Simulador de circuito SafeHome")
    parser.add_argument("--api", default="http://localhost:8000")
    parser.add_argument("--device", type=int, default=1)
    parser.add_argument("--intervalo", type=float, default=2.0)
    args = parser.parse_args()

    try:
        device_id = asegurar_dispositivo(args.api, args.device)
    except httpx.HTTPError as e:
        print(f"[sim] No se pudo conectar a la API en {args.api}: {e}")
        return 1

    print(f"[sim] Enviando telemetria a {args.api} (device {device_id}). Ctrl+C para parar.")
    t = 0
    try:
        while True:
            lectura = generar_lectura(t)
            payload = {"device_id": device_id, **lectura}
            try:
                r = httpx.post(f"{args.api}/api/telemetria", json=payload, timeout=5)
                r.raise_for_status()
                body = r.json()
                cmd = body["comando"]
                print(
                    f"[sim] gas={lectura['gas_ppm']:>6} ppm  temp={lectura['temperatura']:>4} C  "
                    f"-> nivel={body['nivel_alerta']:<10} valvula={body['estado_valvula']:<8} "
                    f"cmd={cmd['valvula']}/buzzer={cmd['buzzer']}"
                )
            except httpx.HTTPError as e:
                print(f"[sim] Error enviando telemetria: {e}")
            t += 1
            time.sleep(args.intervalo)
    except KeyboardInterrupt:
        print("\n[sim] Detenido.")
        return 0


if __name__ == "__main__":
    sys.exit(main())
