"""Lectura de los secretos de Streamlit (secrets.toml en local; «Secrets» en Streamlit Cloud)."""
import os

import streamlit as st


def leer_secreto(nombre, defecto=None):
    """Devuelve el secreto `nombre`, o `defecto` si no existe o no hay archivo de secretos."""
    try:
        return st.secrets.get(nombre, defecto)
    except Exception:
        return defecto


def cargar_url_base_datos():
    """Si la URL de la base de datos está en los secretos y no en el entorno, la pone en el entorno
    para que energia.config.url_postgres() la encuentre."""
    if not os.environ.get("DATABASE_URL"):
        url = leer_secreto("DATABASE_URL")
        if url:
            os.environ["DATABASE_URL"] = str(url)
