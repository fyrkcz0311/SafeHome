"""Tests de la logica pura de evaluacion de umbrales (sin base de datos)."""

from app.services.alertas import Umbrales, evaluar_lectura


UMBRALES = Umbrales(gas_alerta=400, gas_emergencia=800, temp_warning=55, temp_max=70)


def test_lectura_normal_no_genera_alertas():
    res = evaluar_lectura(gas_ppm=120, temperatura=25, presencia=True, umbrales=UMBRALES)
    assert res.nivel == "normal"
    assert res.alertas == []
    assert res.comando.valvula == "mantener"
    assert res.comando.buzzer is False


def test_gas_en_umbral_de_alerta():
    res = evaluar_lectura(gas_ppm=450, temperatura=25, presencia=True, umbrales=UMBRALES)
    assert res.nivel == "alerta"
    assert len(res.alertas) == 1
    assert res.alertas[0].tipo == "gas"
    assert res.alertas[0].nivel == "alerta"
    # En alerta NO se corta el gas automaticamente.
    assert res.comando.valvula == "mantener"
    assert res.comando.buzzer is False


def test_gas_en_umbral_de_emergencia_cierra_valvula():
    res = evaluar_lectura(gas_ppm=850, temperatura=25, presencia=True, umbrales=UMBRALES)
    assert res.nivel == "emergencia"
    assert any(a.tipo == "gas" and a.nivel == "emergencia" for a in res.alertas)
    assert res.comando.valvula == "cerrar"
    assert res.comando.buzzer is True


def test_temperatura_alta_sin_presencia_genera_alerta():
    res = evaluar_lectura(gas_ppm=100, temperatura=65, presencia=False, umbrales=UMBRALES)
    assert res.nivel == "alerta"
    assert any(a.tipo == "temperatura" for a in res.alertas)


def test_temperatura_alta_con_presencia_no_alerta():
    res = evaluar_lectura(gas_ppm=100, temperatura=65, presencia=True, umbrales=UMBRALES)
    assert res.nivel == "normal"
    assert res.alertas == []


def test_temperatura_muy_alta_sin_presencia_cierra_valvula():
    res = evaluar_lectura(gas_ppm=100, temperatura=75, presencia=False, umbrales=UMBRALES)
    assert res.nivel == "emergencia"
    assert any(a.tipo == "temperatura" and a.nivel == "emergencia" for a in res.alertas)
    assert res.comando.valvula == "cerrar"
    assert res.comando.buzzer is True


def test_limite_exacto_de_emergencia_es_emergencia():
    res = evaluar_lectura(gas_ppm=800, temperatura=25, presencia=False, umbrales=UMBRALES)
    assert res.nivel == "emergencia"
    assert res.comando.valvula == "cerrar"


def test_limite_exacto_de_alerta_es_alerta():
    res = evaluar_lectura(gas_ppm=400, temperatura=25, presencia=False, umbrales=UMBRALES)
    assert res.nivel == "alerta"


def test_gas_emergencia_tiene_prioridad_sobre_temperatura():
    res = evaluar_lectura(gas_ppm=900, temperatura=75, presencia=False, umbrales=UMBRALES)
    assert res.nivel == "emergencia"
    assert res.comando.valvula == "cerrar"
    # Debe registrar ambas alertas.
    assert any(a.tipo == "gas" for a in res.alertas)
    assert any(a.tipo == "temperatura" for a in res.alertas)
