import os

import pytest

from energia.demo import CARPETA_DEMO, ArchivoLocal
from energia.parsers import transformar_csv_bms, transformar_dat_designbuilder
from tests.conftest import ArchivoFalso


def test_csv_bms_demo():
    df, errores = transformar_csv_bms(ArchivoLocal(os.path.join(CARPETA_DEMO, "bms_2026_01_1.csv")))
    assert errores == []
    assert len(df) == 14
    assert df["consumo_kwh"].sum() == pytest.approx(71094.93, abs=0.01)
    assert df["electricidad_kwh"].sum() == pytest.approx(56929.61, abs=0.01)
    assert df["gas_kwh"].sum() == pytest.approx(14165.32, abs=0.01)
    assert (df["consumo_kwh"] == df["electricidad_kwh"] + df["gas_kwh"]).all()


def test_csv_bms_con_coma_decimal_y_punto_y_coma_y_salta_totales():
    texto = (
        "Tipología;Electricidad [kWh];Gas Natural [kWh]\n"
        "Heating;1.234,50;10,5\n"
        "Cooling;0;0\n"
        "Total mes;1.234,50;10,5\n"
    )
    df, errores = transformar_csv_bms(ArchivoFalso(texto))
    assert errores == []
    assert list(df["categoria"]) == ["Heating", "Cooling"]
    assert df.iloc[0]["electricidad_kwh"] == pytest.approx(1234.5)
    assert df.iloc[0]["gas_kwh"] == pytest.approx(10.5)
    assert df.iloc[0]["consumo_kwh"] == pytest.approx(1245.0)


def test_csv_bms_sin_columnas_esperadas_da_errores():
    df, errores = transformar_csv_bms(ArchivoFalso("a,b\n1,2\n"))
    assert df is None
    assert len(errores) == 3


def test_csv_bms_sin_filas_validas():
    df, errores = transformar_csv_bms(ArchivoFalso("Tipologia,Electricidad,Gas\nTotal mes,1,1\n"))
    assert df is None
    assert errores


def test_dat_designbuilder_demo():
    df, ignoradas, errores = transformar_dat_designbuilder(
        ArchivoLocal(os.path.join(CARPETA_DEMO, "simulacion_demo.dat")), 2026
    )
    assert errores == []
    assert ignoradas == ["Room Electricity"]
    # 6 categorías reconocidas x 12 meses; "Lighting" se normaliza a "Interior Lighting"
    assert len(df) == 72
    assert "Interior Lighting" in set(df["categoria"])
    assert set(df["anio"]) == {2026}
    ilum_enero = df[(df["categoria"] == "Interior Lighting") & (df["mes"] == 1)]["consumo_kwh"]
    assert ilum_enero.iloc[0] == pytest.approx(12888.20)


def test_dat_designbuilder_sin_categorias_reconocidas():
    texto = "Concepto\t1/1/2002\nAlgo raro\t5\n"
    df, ignoradas, errores = transformar_dat_designbuilder(ArchivoFalso(texto), 2026)
    assert df is None
    assert ignoradas == ["Algo raro"]
    assert errores == ["No se encontraron categorías reconocidas."]
