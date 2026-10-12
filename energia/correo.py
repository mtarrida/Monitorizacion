"""Reconocer qué correos traen los CSV del BMS de cada edificio.

Solo lógica pura (sin red ni Streamlit): decide si un correo concreto corresponde a la regla de
un edificio. La lectura del buzón se montará encima de esto. Una regla tiene dos campos:

- `asunto`: palabras clave que deben aparecer TODAS en el asunto (da igual el orden, las
  mayúsculas o las tildes).
- `remitente`: texto que debe aparecer en la dirección del remitente (opcional).

Una regla sin palabras clave en el asunto no coincide con nada: así un edificio sin configurar
nunca recoge correos que no le tocan.
"""

import re
import unicodedata


def normalizar_texto(texto):
    """Minúsculas, sin tildes y con los espacios colapsados."""
    texto = unicodedata.normalize("NFKD", str(texto or ""))
    texto = "".join(c for c in texto if not unicodedata.combining(c))
    return re.sub(r"\s+", " ", texto).strip().lower()


def palabras_clave(texto):
    """Lista de palabras clave de un campo (separadas por espacios, comas o punto y coma)."""
    return [p for p in re.split(r"[\s,;]+", normalizar_texto(texto)) if p]


def coincide(asunto, remitente, regla):
    """¿Corresponde este correo a la regla {'asunto': ..., 'remitente': ...} de un edificio?"""
    palabras = palabras_clave((regla or {}).get("asunto"))
    if not palabras:
        return False

    asunto_normalizado = normalizar_texto(asunto)
    if not all(p in asunto_normalizado for p in palabras):
        return False

    filtro_remitente = normalizar_texto((regla or {}).get("remitente"))
    return not filtro_remitente or filtro_remitente in normalizar_texto(remitente)
