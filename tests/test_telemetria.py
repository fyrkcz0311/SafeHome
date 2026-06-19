"""Tests del endpoint de ingesta de telemetria."""


def _post(client, device_id, gas, temp, presencia=True):
    return client.post(
        "/api/telemetria",
        json={
            "device_id": device_id,
            "gas_ppm": gas,
            "temperatura": temp,
            "presencia": presencia,
        },
    )


def test_telemetria_dispositivo_inexistente_da_404(client):
    r = _post(client, 999, 100, 25)
    assert r.status_code == 404


def test_lectura_normal_se_persiste_y_no_alerta(client, dispositivo):
    r = _post(client, dispositivo, 120, 25)
    assert r.status_code == 200
    body = r.json()
    assert body["nivel_alerta"] == "normal"
    assert body["alertas_generadas"] == 0
    assert body["comando"]["valvula"] == "mantener"
    assert body["estado_valvula"] == "abierta"

    # La lectura quedo guardada.
    lecturas = client.get("/api/lecturas", params={"device_id": dispositivo}).json()
    assert len(lecturas) == 1
    assert lecturas[0]["gas_ppm"] == 120


def test_emergencia_cierra_valvula_y_crea_alerta(client, dispositivo):
    r = _post(client, dispositivo, 2500, 30)
    assert r.status_code == 200
    body = r.json()
    assert body["nivel_alerta"] == "emergencia"
    assert body["comando"]["valvula"] == "cerrar"
    assert body["comando"]["buzzer"] is True
    assert body["estado_valvula"] == "cerrada"
    assert body["alertas_generadas"] >= 1

    alertas = client.get("/api/alertas", params={"device_id": dispositivo}).json()
    assert any(a["nivel"] == "emergencia" and a["tipo"] == "gas" for a in alertas)


def test_alerta_de_gas_no_cierra_valvula(client, dispositivo):
    r = _post(client, dispositivo, 1500, 25)
    body = r.json()
    assert body["nivel_alerta"] == "alerta"
    assert body["estado_valvula"] == "abierta"
    assert body["comando"]["valvula"] == "mantener"


def test_estado_refleja_ultima_lectura(client, dispositivo):
    _post(client, dispositivo, 120, 22)
    _post(client, dispositivo, 2500, 28)
    estado = client.get(f"/api/dispositivos/{dispositivo}/estado").json()
    assert estado["nivel_alerta"] == "emergencia"
    assert estado["estado_valvula"] == "cerrada"
    assert estado["ultima_lectura"]["gas_ppm"] == 2500
