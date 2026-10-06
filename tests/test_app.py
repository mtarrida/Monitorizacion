"""Prueba de humo: la app arranca con los datos demo y todas las pestañas se pintan sin errores."""
from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

APP = str(Path(__file__).resolve().parent.parent / "app.py")


def _app_con_demo():
    at = AppTest.from_file(APP, default_timeout=120)
    at.run()
    at.sidebar.selectbox(key="global_edificio").select("PGI-DEMO-001 - Edificio Demo")
    at.sidebar.number_input(key="global_anio").set_value(2026)
    at.sidebar.selectbox(key="global_mes").select(3)
    at.run()
    return at


def test_app_arranca_sin_edificios(db_temporal):
    at = AppTest.from_file(APP, default_timeout=120)
    at.run()
    assert not at.exception
    assert len(at.tabs) >= 8


def test_app_con_demo_sin_excepciones(db_demo):
    at = _app_con_demo()
    assert not at.exception
    assert not at.error


def test_app_con_demo_muestra_cifras_esperadas(db_demo):
    at = _app_con_demo()
    metricas = {}
    for m in at.metric:
        metricas.setdefault(m.label, []).append(m.value)

    assert "3/12" in metricas["Meses BMS"]
    # comparativa mensual de marzo: simulado 37.069 kWh frente a real 66.888 kWh
    assert "37,069 kWh" in metricas["Simulado"]
    assert "66,888 kWh" in metricas["Real BMS"]
    assert any("80.4" in v or "80.43" in v for v in metricas["Desviación"])


@pytest.mark.parametrize("anio", [2020, 2026])
def test_app_con_demo_otros_anios(db_demo, anio):
    at = AppTest.from_file(APP, default_timeout=120)
    at.run()
    at.sidebar.selectbox(key="global_edificio").select("PGI-DEMO-001 - Edificio Demo")
    at.sidebar.number_input(key="global_anio").set_value(anio)
    at.run()
    assert not at.exception
