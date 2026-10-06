import os

import pandas as pd
import pytest

from energia.utils import (
    crear_carpetas_edificio,
    leer_csv_flexible,
    leer_texto_archivo,
    limpiar_nombre,
    limpiar_numero,
    normalizar,
)
from tests.conftest import ArchivoFalso


@pytest.mark.parametrize("entrada, esperado", [
    ("1.234,56", 1234.56),
    ("15957.85", 15957.85),
    ("0,5", 0.5),
    ("12", 12.0),
    (" 1 234,5 ", 1234.5),
    ("", 0.0),
    ("   ", 0.0),
    (None, 0.0),
    (float("nan"), 0.0),
    ("abc", 0.0),
])
def test_limpiar_numero(entrada, esperado):
    assert limpiar_numero(entrada) == pytest.approx(esperado)


def test_normalizar_quita_tildes_bom_y_espacios():
    assert normalizar("\ufeffTipología ") == "tipologia"
    assert normalizar("Electricidad   [kWh]") == "electricidad [kwh]"


def test_limpiar_nombre():
    assert limpiar_nombre(" Edificio Demo! ") == "edificio_demo_"


def test_crear_carpetas_edificio(db_temporal):
    carpeta = crear_carpetas_edificio("X-1", "Mi Edificio")
    assert carpeta.startswith(str(db_temporal))
    for sub in ["simulaciones", "consumos_bms", "informes"]:
        assert os.path.isdir(os.path.join(carpeta, sub))


@pytest.mark.parametrize("n_extra", [0, 1])
def test_utf8_con_bom_no_se_lee_como_utf16(n_extra):
    """Regresión: un CSV UTF-8 de longitud par se decodificaba como UTF-16 (texto basura)."""
    texto = "Tipologia,Electricidad [kWh]" + "x" * n_extra + "\nHeating,1.5\n"
    for relleno in range(4):  # cubre longitudes pares e impares
        contenido = ("\ufeff" + texto + "\n" * relleno).encode("utf-8")
        assert leer_texto_archivo(ArchivoFalso(contenido)).lstrip("\ufeff").startswith("Tipologia")


def test_utf16_con_bom_se_lee():
    contenido = "a\tb\n1\t2\n".encode("utf-16")
    assert leer_texto_archivo(ArchivoFalso(contenido)) == "a\tb\n1\t2\n"


def test_latin1_con_tildes():
    contenido = "Tipología;Gas\nX;1\n".encode("latin-1")
    assert "Tipología" in leer_texto_archivo(ArchivoFalso(contenido))


@pytest.mark.parametrize("sep", [",", ";", "\t"])
def test_leer_csv_flexible_separadores(sep):
    texto = sep.join(["Tipologia", "Electricidad"]) + "\n" + sep.join(["Heating", "10"]) + "\n"
    df = leer_csv_flexible(ArchivoFalso(texto))
    assert list(df.columns) == ["Tipologia", "Electricidad"]
    assert isinstance(df, pd.DataFrame) and len(df) == 1
