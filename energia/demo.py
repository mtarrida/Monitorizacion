"""Crea el edificio de demostración (PGI-DEMO-001) a partir de los archivos de ejemplos/demo.

Uso:  python -m energia.demo
"""
import os

from energia.db import (
    cargar_edificios,
    crear_consumo_bms,
    crear_simulacion,
    guardar_detalle_bms,
    guardar_detalle_simulacion,
    guardar_edificio,
    inicializar_db,
)
from energia.parsers import transformar_csv_bms, transformar_dat_designbuilder

CODIGO_DEMO = "PGI-DEMO-001"
ANIO_DEMO = 2026
CARPETA_DEMO = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "ejemplos", "demo")

# Archivo y mes de cada importación BMS. Marzo se importó tres veces: cuenta la última.
BMS_DEMO = [
    ("bms_2026_01_1.csv", 1),
    ("bms_2026_02_2.csv", 2),
    ("bms_2026_03_3.csv", 3),
    ("bms_2026_03_4.csv", 3),
    ("bms_2026_03_5.csv", 3),
]


class ArchivoLocal:
    """Imita un archivo subido (los lectores solo usan getvalue)."""

    def __init__(self, ruta):
        self.ruta = ruta

    def getvalue(self):
        with open(self.ruta, "rb") as f:
            return f.read()


def crear_demo():
    """Crea el edificio demo con su simulación y sus consumos BMS. Devuelve False si ya existía."""
    inicializar_db()

    if CODIGO_DEMO in cargar_edificios(True)["codigo_proyecto"].values:
        return False

    guardar_edificio({
        "codigo_proyecto": CODIGO_DEMO,
        "nombre": "Edificio Demo",
        "cliente": "",
        "ubicacion": "Madrid",
        "uso": "Oficinas",
        "superficie_m2": 2500.0,
        "categoria_edificio": "Oficinas",
        "unidad_referencia": "m²",
        "sistema_climatizacion": "Bomba de calor",
        "observaciones": "Edificio de prueba",
    })

    df_sim, _, errores = transformar_dat_designbuilder(
        ArchivoLocal(os.path.join(CARPETA_DEMO, "simulacion_demo.dat")), ANIO_DEMO
    )
    if errores:
        raise ValueError(f"Simulación demo no válida: {errores}")
    sim_id = crear_simulacion(CODIGO_DEMO, "Fase de diseño", "", True)
    guardar_detalle_simulacion(sim_id, df_sim)

    for archivo, mes in BMS_DEMO:
        df_bms, errores = transformar_csv_bms(ArchivoLocal(os.path.join(CARPETA_DEMO, archivo)))
        if errores:
            raise ValueError(f"BMS demo {archivo} no válido: {errores}")
        bms_id = crear_consumo_bms(CODIGO_DEMO, ANIO_DEMO, mes, f"BMS {ANIO_DEMO}-{mes:02d}", "")
        guardar_detalle_bms(bms_id, df_bms)

    return True


if __name__ == "__main__":
    print("Demo creada." if crear_demo() else "La demo ya existía.")
