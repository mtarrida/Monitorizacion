import pandas as pd
import pytest

from energia.analisis import (
    clasificar_alerta,
    comparativa_mensual,
    comparativa_parcial_anual,
    generar_observaciones,
    indicador_especifico,
    obtener_valor_referencia,
)
from energia.db import (
    cargar_simulacion_activa,
    consumos_bms_anio,
    crear_consumo_bms,
    guardar_detalle_bms,
    guardar_edificio,
    meses_bms,
)


@pytest.mark.parametrize("pct, esperado", [
    (0, "🟢 Correcto"),
    (10, "🟢 Correcto"),
    (-10, "🟢 Correcto"),
    (10.01, "🟡 Atención"),
    (20, "🟡 Atención"),
    (-20, "🟡 Atención"),
    (20.01, "🔴 Revisar"),
    (-45, "🔴 Revisar"),
])
def test_clasificar_alerta(pct, esperado):
    assert clasificar_alerta(pct) == esperado


def test_generar_observaciones():
    comp = pd.DataFrame({"categoria": ["A", "B", "C"], "desviacion_pct": [30.0, -20.0, 5.0]})
    texto = generar_observaciones(comp)
    assert "A: consumo real superior al simulado en 30.0%" in texto
    assert "B: consumo real inferior al simulado en 20.0%" in texto
    assert "C" not in texto

    sin_desvios = generar_observaciones(comp[comp["categoria"] == "C"])
    assert "No se detectan desviaciones significativas" in sin_desvios


def test_valor_referencia_por_defecto_es_superficie():
    ed = pd.Series({"superficie_m2": 2500.0, "unidad_referencia": "m²", "valor_unidad_referencia": 0.0})
    assert obtener_valor_referencia(ed) == ("m²", 2500.0)


def test_valor_referencia_usa_la_unidad_elegida():
    ed = pd.Series({
        "superficie_m2": 2500.0, "unidad_referencia": "habitaciones",
        "valor_unidad_referencia": 80.0, "habitaciones": 0.0,
    })
    assert obtener_valor_referencia(ed) == ("habitaciones", 80.0)


def test_valor_referencia_cae_a_los_campos_especificos_y_luego_a_superficie():
    ed = pd.Series({
        "superficie_m2": 2500.0, "unidad_referencia": "camas",
        "valor_unidad_referencia": 0.0, "camas": 120.0,
    })
    assert obtener_valor_referencia(ed) == ("camas", 120.0)

    sin_camas = pd.Series({
        "superficie_m2": 2500.0, "unidad_referencia": "camas",
        "valor_unidad_referencia": 0.0, "camas": 0.0,
    })
    assert obtener_valor_referencia(sin_camas) == ("m²", 2500.0)


def test_indicador_especifico():
    ed = pd.Series({"superficie_m2": 1000.0, "unidad_referencia": "m²", "valor_unidad_referencia": 0.0})
    etiqueta, valor, unidad = indicador_especifico(50000.0, ed)
    assert (etiqueta, valor, unidad) == ("kWh/m²", 50.0, "m²")

    sin_dato = pd.Series({"superficie_m2": 0.0, "unidad_referencia": "m²", "valor_unidad_referencia": 0.0})
    assert indicador_especifico(50000.0, sin_dato)[:2] == ("Sin dato", 0)


def test_comparativa_mensual_usa_la_ultima_importacion_del_mes(db_demo):
    sim_id = int(cargar_simulacion_activa("PGI-DEMO-001").iloc[0]["id"])
    comp = comparativa_mensual("PGI-DEMO-001", sim_id, 2026, 3)

    # Marzo se importó 3 veces (ids 3, 4 y 5): solo cuenta la última (66.887,70 kWh)
    assert comp["real_kwh"].sum() == pytest.approx(66887.70, abs=0.01)
    assert comp["simulado_kwh"].sum() == pytest.approx(37069.03, abs=0.01)
    assert set(comp.columns) >= {"categoria", "simulado_kwh", "real_kwh", "desviacion_kwh", "desviacion_pct", "estado"}
    # la desviación es real - simulado, y el % se calcula sobre lo simulado
    fila = comp[comp["categoria"] == "Interior Lighting"].iloc[0]
    assert fila["desviacion_kwh"] == pytest.approx(fila["real_kwh"] - fila["simulado_kwh"])
    assert fila["desviacion_pct"] == pytest.approx(fila["desviacion_kwh"] / fila["simulado_kwh"] * 100, abs=0.01)
    # categorías solo en BMS (sin simulado) no dividen por cero
    assert (comp.loc[comp["simulado_kwh"] == 0, "desviacion_pct"] == 0).all()
    # ordenado de mayor a menor desviación absoluta en kWh
    assert list(comp["desviacion_kwh"]) == sorted(comp["desviacion_kwh"], reverse=True)


def test_comparativa_mensual_sin_bms_devuelve_vacio(db_demo):
    sim_id = int(cargar_simulacion_activa("PGI-DEMO-001").iloc[0]["id"])
    assert comparativa_mensual("PGI-DEMO-001", sim_id, 2026, 7).empty


def test_comparativa_parcial_anual(db_demo):
    sim_id = int(cargar_simulacion_activa("PGI-DEMO-001").iloc[0]["id"])
    df_meses, df_cat = comparativa_parcial_anual("PGI-DEMO-001", sim_id, 2026)

    assert list(df_meses["mes"]) == [1, 2, 3]
    reales = dict(zip(df_meses["mes"], df_meses["real_kwh"]))
    assert reales[1] == pytest.approx(71094.93, abs=0.01)
    assert reales[3] == pytest.approx(66887.70, abs=0.01)  # no suma las 3 importaciones de marzo
    assert df_cat["real_kwh"].sum() == pytest.approx(sum(reales.values()), abs=0.01)


def test_comparativa_parcial_anual_sin_bms(db_demo):
    sim_id = int(cargar_simulacion_activa("PGI-DEMO-001").iloc[0]["id"])
    df_meses, df_cat = comparativa_parcial_anual("PGI-DEMO-001", sim_id, 2020)
    assert df_meses.empty and df_cat.empty


def test_meses_bms_toma_el_id_mas_alto_de_cada_mes(db_demo):
    meses = meses_bms("PGI-DEMO-001", 2026)
    assert dict(zip(meses["mes"], meses["bms_id"])) == {1: 1, 2: 2, 3: 5}


def test_consumos_bms_anio_vacio(db_demo):
    assert consumos_bms_anio("PGI-DEMO-001", 2020).empty


def test_consumos_bms_anio_importacion_antigua_sin_desglose(db_temporal):
    """Importaciones antiguas solo tenían consumo total: se asignan a electricidad."""
    guardar_edificio({
        "codigo_proyecto": "OLD-1", "nombre": "Antiguo", "cliente": "", "ubicacion": "",
        "uso": "Oficinas", "superficie_m2": 100.0, "sistema_climatizacion": "", "observaciones": "",
    })
    bms = crear_consumo_bms("OLD-1", 2026, 1, "BMS", "")
    guardar_detalle_bms(bms, pd.DataFrame([{
        "categoria": "Heating", "consumo_kwh": 100.0, "nombre_original_bms": "Heating",
        "electricidad_kwh": 0.0, "gas_kwh": 0.0,
    }]))
    df = consumos_bms_anio("OLD-1", 2026)
    assert df.iloc[0]["electricidad_kwh"] == 100.0
    assert df.iloc[0]["gas_kwh"] == 0
