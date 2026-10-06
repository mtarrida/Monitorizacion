import pandas as pd
import pytest

from energia.db import (
    actualizar_edificio,
    cambiar_estado_edificio,
    cargar_edificios,
    cargar_simulacion_activa,
    cargar_simulaciones,
    crear_consumo_bms,
    crear_simulacion,
    eliminar_edificio,
    guardar_detalle_bms,
    guardar_detalle_simulacion,
    guardar_edificio,
    inicializar_db,
    marcar_simulacion_activa,
    resumen_datos_edificio,
)

EDIFICIO = {
    "codigo_proyecto": "T-001",
    "nombre": "Torre Test",
    "cliente": "Cliente SA",
    "ubicacion": "Barcelona",
    "uso": "Oficinas",
    "superficie_m2": 1000.0,
    "sistema_climatizacion": "VRV",
    "observaciones": "",
}


def test_inicializar_db_es_idempotente(db_temporal):
    inicializar_db()
    inicializar_db()
    assert cargar_edificios(True).empty


def test_crear_actualizar_y_archivar_edificio(db_temporal):
    guardar_edificio(EDIFICIO)
    df = cargar_edificios()
    assert list(df["codigo_proyecto"]) == ["T-001"]
    assert df.iloc[0]["estado"] == "ACTIVO"

    actualizar_edificio("T-001", {**EDIFICIO, "nombre": "Torre Nueva", "habitaciones": 12})
    fila = cargar_edificios().iloc[0]
    assert fila["nombre"] == "Torre Nueva"
    assert fila["habitaciones"] == 12

    cambiar_estado_edificio("T-001", "ARCHIVADO")
    assert cargar_edificios(False).empty
    assert len(cargar_edificios(True)) == 1


def test_codigo_duplicado_falla(db_temporal):
    guardar_edificio(EDIFICIO)
    with pytest.raises(Exception):
        guardar_edificio(EDIFICIO)


def test_solo_una_simulacion_activa(db_temporal):
    guardar_edificio(EDIFICIO)
    s1 = crear_simulacion("T-001", "Diseño", "", True)
    s2 = crear_simulacion("T-001", "Reforma", "", True)
    assert cargar_simulacion_activa("T-001").iloc[0]["id"] == s2

    marcar_simulacion_activa(s1, "T-001")
    activas = cargar_simulaciones("T-001")
    assert list(activas[activas["activa"] == 1]["id"]) == [s1]


def test_eliminar_edificio_borra_en_cascada(db_demo):
    antes = resumen_datos_edificio("PGI-DEMO-001")
    assert antes == {"simulaciones": 1, "detalle_simulaciones": 72, "consumos_bms": 5, "detalle_bms": 70}

    eliminados = eliminar_edificio("PGI-DEMO-001")
    assert eliminados["edificios"] == 1
    assert eliminados["simulaciones"] == 1
    assert eliminados["consumos_bms"] == 5
    assert resumen_datos_edificio("PGI-DEMO-001") == {
        "simulaciones": 0, "detalle_simulaciones": 0, "consumos_bms": 0, "detalle_bms": 0,
    }
    assert cargar_edificios(True).empty


def test_eliminar_edificio_no_toca_otros(db_demo):
    guardar_edificio(EDIFICIO)
    sim = crear_simulacion("T-001", "Diseño", "", True)
    guardar_detalle_simulacion(sim, pd.DataFrame([{"anio": 2026, "mes": 1, "categoria": "Heating", "consumo_kwh": 5.0}]))
    bms = crear_consumo_bms("T-001", 2026, 1, "BMS", "")
    guardar_detalle_bms(bms, pd.DataFrame([{
        "categoria": "Heating", "consumo_kwh": 5.0, "nombre_original_bms": "Heating",
        "electricidad_kwh": 5.0, "gas_kwh": 0.0,
    }]))

    eliminar_edificio("PGI-DEMO-001")
    assert resumen_datos_edificio("T-001") == {
        "simulaciones": 1, "detalle_simulaciones": 1, "consumos_bms": 1, "detalle_bms": 1,
    }
