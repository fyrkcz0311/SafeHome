"""Tests de gestion de dispositivos: control de valvula y umbrales."""


def test_crear_y_listar_dispositivo(client):
    r = client.post("/api/dispositivos", json={"nombre": "Cocina 1", "ubicacion": "Piso 2"})
    assert r.status_code == 201
    assert r.json()["estado_valvula"] == "abierta"

    lista = client.get("/api/dispositivos").json()
    assert len(lista) == 1
    assert lista[0]["nombre"] == "Cocina 1"


def test_umbrales_por_defecto(client, dispositivo):
    u = client.get(f"/api/dispositivos/{dispositivo}/umbrales").json()
    assert u["gas_alerta"] == 400
    assert u["gas_emergencia"] == 800


def test_configurar_umbrales_cambia_comportamiento(client, dispositivo):
    # Bajar el umbral de emergencia a 200 ppm.
    client.post(
        f"/api/dispositivos/{dispositivo}/umbrales",
        json={"gas_emergencia": 200, "gas_alerta": 100},
    )
    r = client.post(
        "/api/telemetria",
        json={"device_id": dispositivo, "gas_ppm": 250, "temperatura": 25, "presencia": True},
    )
    assert r.json()["nivel_alerta"] == "emergencia"


def test_cerrar_y_reactivar_valvula(client, dispositivo):
    # Forzar emergencia -> valvula cerrada.
    client.post(
        "/api/telemetria",
        json={"device_id": dispositivo, "gas_ppm": 900, "temperatura": 25, "presencia": True},
    )
    estado = client.get(f"/api/dispositivos/{dispositivo}/estado").json()
    assert estado["estado_valvula"] == "cerrada"

    # Reactivar manualmente.
    r = client.post(f"/api/dispositivos/{dispositivo}/valvula", json={"accion": "reactivar"})
    assert r.status_code == 200
    assert r.json()["estado_valvula"] == "abierta"
    assert r.json()["nivel_alerta"] == "normal"


def test_accion_valvula_invalida(client, dispositivo):
    r = client.post(f"/api/dispositivos/{dispositivo}/valvula", json={"accion": "explotar"})
    assert r.status_code == 400


def test_comando_polling(client, dispositivo):
    client.post(
        "/api/telemetria",
        json={"device_id": dispositivo, "gas_ppm": 900, "temperatura": 25, "presencia": True},
    )
    cmd = client.get(f"/api/dispositivos/{dispositivo}/comando").json()
    assert cmd["valvula"] == "cerrar"
    assert cmd["buzzer"] is True
