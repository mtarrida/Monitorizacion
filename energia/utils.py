"""Utilidades de lectura de archivos, limpieza de texto/numeros y carpetas de proyecto."""

from io import StringIO
import os
import re

import pandas as pd

from energia import config


def limpiar_nombre(texto):
    texto = str(texto).lower().strip()
    texto = re.sub(r"[^a-zA-Z0-9_-]", "_", texto)
    texto = re.sub(r"_+", "_", texto)
    return texto


def crear_carpetas_edificio(codigo, nombre):
    carpeta = os.path.join(config.CARPETA_BASE, f"{codigo}_{limpiar_nombre(nombre)}")
    os.makedirs(os.path.join(carpeta, "simulaciones"), exist_ok=True)
    os.makedirs(os.path.join(carpeta, "consumos_bms"), exist_ok=True)
    os.makedirs(os.path.join(carpeta, "informes"), exist_ok=True)
    return carpeta


def leer_texto_archivo(archivo):
    contenido = archivo.getvalue()

    # UTF-16 solo si el archivo lo declara (BOM) o tiene bytes nulos. Si se probara siempre,
    # un CSV en UTF-8 con número par de bytes se decodificaría como UTF-16 y saldría texto basura.
    if contenido.startswith((b"\xff\xfe", b"\xfe\xff")) or b"\x00" in contenido[:200]:
        try:
            return contenido.decode("utf-16")
        except Exception:
            pass

    for cod in ["utf-8-sig", "utf-8", "latin-1", "cp1252"]:
        try:
            return contenido.decode(cod)
        except Exception:
            pass
    return contenido.decode("latin-1", errors="ignore")


def limpiar_numero(valor):
    if pd.isna(valor):
        return 0.0

    valor = str(valor).strip().replace(" ", "")

    if valor == "":
        return 0.0

    if "," in valor:
        valor = valor.replace(".", "").replace(",", ".")

    try:
        return float(valor)
    except Exception:
        return 0.0


def normalizar(texto):
    texto = str(texto).lower().strip()
    texto = texto.replace("\ufeff", "").replace("\xa0", " ")
    texto = texto.replace("á", "a").replace("é", "e").replace("í", "i")
    texto = texto.replace("ó", "o").replace("ú", "u")
    texto = re.sub(r"\s+", " ", texto)
    return texto


def leer_csv_flexible(archivo):
    texto = leer_texto_archivo(archivo)

    for sep in [",", ";", "\t"]:
        try:
            df = pd.read_csv(StringIO(texto), sep=sep, engine="python")
            if len(df.columns) > 1:
                return df
        except Exception:
            pass

    return pd.read_csv(StringIO(texto), sep=None, engine="python")
