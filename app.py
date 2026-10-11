import os

import streamlit as st

from energia.auth import mostrar_sesion_en_barra_lateral, requerir_login
from energia.contexto import Contexto
from energia.db import cargar_edificios, inicializar_db
from energia.demo import crear_demo
from energia.secretos import cargar_url_base_datos, leer_secreto
from energia.tabs import bms, co2, comparativa, costes, edificios, informe, panel, simulaciones
from energia.ui import (
    aplicar_estilos,
    configurar_sidebar,
    mostrar_cabecera_app,
    mostrar_mensaje_estado,
)

st.set_page_config(page_title="Energía", layout="wide")

# Antes de leer ningún dato: si hay usuarios configurados, hay que entrar primero.
if not requerir_login():
    st.stop()

cargar_url_base_datos()
inicializar_db()

# Para una primera prueba online: con ENERGIA_DEMO=1 se crea el edificio de demostración si no existe.
if os.environ.get("ENERGIA_DEMO") == "1" or leer_secreto("ENERGIA_DEMO") == "1":
    crear_demo()

edificios_activos = cargar_edificios(False)
edificios_todos = cargar_edificios(True)

aplicar_estilos()
codigo, edificio, anio, mes = configurar_sidebar(edificios_activos)
mostrar_sesion_en_barra_lateral()

mostrar_cabecera_app()
mostrar_mensaje_estado()

ctx = Contexto(edificios_activos, edificios_todos, codigo, edificio, anio, mes)

tab_inicio, tab_edificios, tab_sim, tab_bms, tab_comp, tab_informe, tab_costes, tab_co2 = st.tabs([
    "📊 Panel",
    "🏢 Edificios",
    "📈 Simulaciones",
    "📥 BMS",
    "📊 Comparativa",
    "📄 Informe mensual",
    "💰 Costes",
    "🌍 CO₂",
])

with tab_inicio:
    panel.mostrar(ctx)

with tab_edificios:
    edificios.mostrar(ctx)

with tab_sim:
    simulaciones.mostrar(ctx)

with tab_bms:
    bms.mostrar(ctx)

with tab_comp:
    comparativa.mostrar(ctx)

with tab_informe:
    informe.mostrar(ctx)

with tab_costes:
    costes.mostrar(ctx)

with tab_co2:
    co2.mostrar(ctx)
