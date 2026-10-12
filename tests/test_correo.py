"""Pruebas de la coincidencia de correos con la regla de un edificio (lógica pura)."""
import pytest

from energia.correo import coincide, normalizar_texto, palabras_clave


def test_normalizar_texto_quita_tildes_mayusculas_y_espacios():
    assert normalizar_texto("  CSV   Monitorización ") == "csv monitorizacion"
    assert normalizar_texto(None) == ""


def test_palabras_clave_admite_espacios_comas_y_punto_y_coma():
    assert palabras_clave("CSV, Monitorización; Hotel  Sol") == ["csv", "monitorizacion", "hotel", "sol"]
    assert palabras_clave("") == []


@pytest.mark.parametrize("asunto, esperado", [
    ("CSV monitorización Hotel Sol marzo", True),
    ("Re: csv MONITORIZACION - hotel sol", True),   # sin tildes, otras mayúsculas y otro orden
    ("Monitorización hotel Sol", False),            # falta "csv"
    ("CSV monitorización Hotel Luna", False),       # falta "sol"
    ("", False),
])
def test_coincide_por_asunto(asunto, esperado):
    regla = {"asunto": "csv monitorización sol"}
    assert coincide(asunto, "alguien@cliente.com", regla) is esperado


def test_coincide_filtra_por_remitente_si_se_indica():
    regla = {"asunto": "csv", "remitente": "@cliente.com"}
    assert coincide("CSV marzo", "Ana <ana@Cliente.com>", regla)
    assert not coincide("CSV marzo", "ana@otra.com", regla)


def test_una_regla_sin_palabras_clave_no_recoge_nada():
    assert not coincide("CSV marzo", "ana@cliente.com", {"asunto": "", "remitente": ""})
    assert not coincide("CSV marzo", "ana@cliente.com", {})
    assert not coincide("CSV marzo", "ana@cliente.com", None)
