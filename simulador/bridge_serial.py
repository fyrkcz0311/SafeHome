"""Bridge serie -> HTTP para conectar la simulacion de Proteus con la API.

Proteus tiene soporte limitado para que un ESP32 simulado haga peticiones HTTP
reales. El patron fiable es: el firmware (Arduino/ESP32) imprime las lecturas por
el puerto serie (UART). En el PC se crea un par de puertos COM virtuales con
com0com; Proteus escribe en un extremo y este script lee del otro y reenvia cada
lectura a la API por HTTP.

Formato esperado de cada linea serie (CSV):
    gas_ppm,temperatura,presencia
por ejemplo:
    850.0,31.2,1
Tambien acepta JSON por linea: {"gas_ppm":850,"temperatura":31.2,"presencia":1}

Uso:
    python simulador/bridge_serial.py --port COM5 --baud 9600 --device 1
"""

import argparse
import json
import sys

import httpx

try:
    import serial  # pyserial
except ImportError:  # pragma: no cover
    serial = None


def parsear_linea(linea: str) -> dict | None:
    linea = linea.strip()
    if not linea:
        return None
    # Intento JSON.
    if linea.startswith("{"):
        try:
            d = json.loads(linea)
            return {
                "gas_ppm": float(d["gas_ppm"]),
                "temperatura": float(d["temperatura"]),
                "presencia": bool(int(d.get("presencia", 0))),
            }
        except (ValueError, KeyError):
            return None
    # CSV: gas,temp,presencia
    partes = linea.split(",")
    if len(partes) < 2:
        return None
    try:
        gas = float(partes[0])
        temp = float(partes[1])
        presencia = bool(int(partes[2])) if len(partes) > 2 else False
        return {"gas_ppm": gas, "temperatura": temp, "presencia": presencia}
    except ValueError:
        return None


def main() -> int:
    parser = argparse.ArgumentParser(description="Bridge serie->HTTP para Proteus")
    parser.add_argument("--port", required=True, help="Puerto serie virtual (ej. COM5)")
    parser.add_argument("--baud", type=int, default=9600)
    parser.add_argument("--api", default="http://localhost:8000")
    parser.add_argument("--device", type=int, default=1)
    args = parser.parse_args()

    if serial is None:
        print("[bridge] Falta pyserial. Instale con: pip install pyserial")
        return 1

    try:
        ser = serial.Serial(args.port, args.baud, timeout=1)
    except serial.SerialException as e:
        print(f"[bridge] No se pudo abrir {args.port}: {e}")
        return 1

    print(f"[bridge] Leyendo de {args.port} @ {args.baud} -> {args.api} (device {args.device}).")
    try:
        while True:
            raw = ser.readline().decode("utf-8", errors="ignore")
            lectura = parsear_linea(raw)
            if lectura is None:
                continue
            payload = {"device_id": args.device, **lectura}
            try:
                r = httpx.post(f"{args.api}/api/telemetria", json=payload, timeout=5)
                r.raise_for_status()
                body = r.json()
                print(
                    f"[bridge] gas={lectura['gas_ppm']} temp={lectura['temperatura']} "
                    f"-> nivel={body['nivel_alerta']} cmd={body['comando']['valvula']}"
                )
            except httpx.HTTPError as e:
                print(f"[bridge] Error HTTP: {e}")
    except KeyboardInterrupt:
        print("\n[bridge] Detenido.")
        return 0
    finally:
        ser.close()


if __name__ == "__main__":
    sys.exit(main())
