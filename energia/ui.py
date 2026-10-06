"""Componentes de interfaz: estilos, cabecera, barra lateral y tablas."""

import base64
import os

import pandas as pd
import streamlit as st

from energia.config import (
    ANIO_ACTUAL,
    COLOR_CORPORATIVO,
    COLOR_CORPORATIVO_OSCURO,
    COLOR_GRIS_BORDE,
    COLOR_GRIS_FONDO,
    LOGO_PATH,
    MESES,
)
from energia.analisis import obtener_valor_referencia
from energia.db import cargar_simulacion_activa


COLUMN_CONFIG = {
    "codigo_proyecto": st.column_config.TextColumn("Código"),
    "nombre": st.column_config.TextColumn("Nombre"),
    "cliente": st.column_config.TextColumn("Cliente"),
    "ubicacion": st.column_config.TextColumn("Ubicación"),
    "uso": st.column_config.TextColumn("Uso"),
    "categoria_edificio": st.column_config.TextColumn("Categoría edificio"),
    "unidad_referencia": st.column_config.TextColumn("Unidad referencia"),
    "valor_unidad_referencia": st.column_config.NumberColumn("Valor referencia", format="%.0f"),
    "habitaciones": st.column_config.NumberColumn("Habitaciones", format="%.0f"),
    "puestos_trabajo": st.column_config.NumberColumn("Puestos", format="%.0f"),
    "camas": st.column_config.NumberColumn("Camas", format="%.0f"),
    "horario_uso": st.column_config.TextColumn("Horario de uso"),
    "estado": st.column_config.TextColumn("Estado"),
    "superficie_m2": st.column_config.NumberColumn("Superficie", format="%.0f m²"),
    "anio": st.column_config.NumberColumn("Año", format="%d"),
    "mes": st.column_config.NumberColumn("Mes", format="%d"),
    "categoria": st.column_config.TextColumn("Categoría"),
    "consumo_kwh": st.column_config.NumberColumn("Consumo", format="%.0f kWh"),
    "simulado_kwh": st.column_config.NumberColumn("Simulado", format="%.0f kWh"),
    "real_kwh": st.column_config.NumberColumn("Real BMS", format="%.0f kWh"),
    "desviacion_kwh": st.column_config.NumberColumn("Desviación", format="%.0f kWh"),
    "desviacion_pct": st.column_config.NumberColumn("Desviación", format="%.2f %%"),
    "electricidad_kwh": st.column_config.NumberColumn("Electricidad", format="%.0f kWh"),
    "gas_kwh": st.column_config.NumberColumn("Gas", format="%.0f kWh"),
    "coste_electricidad_eur": st.column_config.NumberColumn("Electricidad", format="%.2f €"),
    "coste_gas_eur": st.column_config.NumberColumn("Gas", format="%.2f €"),
    "coste_total_eur": st.column_config.NumberColumn("Coste total", format="%.2f €"),
    "co2_electricidad_kg": st.column_config.NumberColumn("Electricidad", format="%.0f kgCO₂"),
    "co2_gas_kg": st.column_config.NumberColumn("Gas", format="%.0f kgCO₂"),
    "co2_total_kg": st.column_config.NumberColumn("CO₂ total", format="%.0f kgCO₂"),
    "indicador_especifico": st.column_config.NumberColumn("Indicador específico", format="%.2f"),
    "unidad_indicador": st.column_config.TextColumn("Unidad indicador"),
}


def aplicar_estilos():
    css = """
    <style>
        :root {
            --pgi-primary: __PGI_PRIMARY__;
            --pgi-primary-dark: __PGI_PRIMARY_DARK__;
            --pgi-bg: __PGI_BG__;
            --pgi-border: __PGI_BORDER__;
            --pgi-text: #23272f;
            --pgi-muted: #667085;
        }

        .stApp {
            background: linear-gradient(180deg, #ffffff 0%, var(--pgi-bg) 100%);
            color: var(--pgi-text);
        }

        .block-container {
            padding-top: 1rem;
            padding-bottom: 2.5rem;
        }

        [data-testid="stSidebar"] {
            background: #f8f9fa;
            border-right: 1px solid var(--pgi-border);
        }

        [data-testid="stSidebar"] h1,
        [data-testid="stSidebar"] h2,
        [data-testid="stSidebar"] h3 {
            color: var(--pgi-primary-dark);
        }

        .pgi-header {
            display: flex;
            align-items: center;
            gap: 1.4rem;
            border-bottom: 1px solid var(--pgi-border);
            padding: 0.35rem 0 1.1rem 0;
            margin-bottom: 1rem;
        }

        .pgi-header img {
            width: 310px;
            max-width: 42vw;
            height: auto;
        }

        .pgi-header h1 {
            color: var(--pgi-primary-dark);
            font-size: 2.05rem;
            line-height: 1.1;
            margin: 0 0 0.25rem 0;
            font-weight: 750;
        }

        .pgi-header p {
            color: var(--pgi-muted);
            margin: 0;
            font-size: 0.98rem;
        }

        [data-testid="stMetric"] {
            background: #ffffff;
            border: 1px solid var(--pgi-border);
            border-left: 4px solid var(--pgi-primary);
            border-radius: 8px;
            padding: 0.8rem 0.9rem;
            box-shadow: 0 1px 2px rgba(16, 24, 40, 0.04);
        }

        [data-testid="stMetricLabel"] {
            color: var(--pgi-muted);
        }

        [data-testid="stMetricValue"] {
            font-size: 1.35rem;
            color: var(--pgi-text);
        }

        div[data-testid="stTabs"] button {
            font-weight: 600;
        }

        div[data-testid="stTabs"] button[aria-selected="true"] {
            color: var(--pgi-primary);
            border-bottom-color: var(--pgi-primary);
        }

        .stButton > button,
        .stDownloadButton > button,
        [data-testid="stFormSubmitButton"] button {
            background: var(--pgi-primary);
            border: 1px solid var(--pgi-primary);
            color: #ffffff;
            border-radius: 7px;
            font-weight: 650;
        }

        .stButton > button:hover,
        .stDownloadButton > button:hover,
        [data-testid="stFormSubmitButton"] button:hover {
            background: var(--pgi-primary-dark);
            border-color: var(--pgi-primary-dark);
            color: #ffffff;
        }

        .stTextInput input:focus,
        .stNumberInput input:focus,
        .stTextArea textarea:focus,
        [data-baseweb="select"] > div:focus-within {
            border-color: var(--pgi-primary);
            box-shadow: 0 0 0 1px var(--pgi-primary);
        }

        [data-testid="stDataFrame"] {
            border: 1px solid var(--pgi-border);
            border-radius: 8px;
            overflow: hidden;
        }

        @media (max-width: 760px) {
            .pgi-header {
                display: block;
            }

            .pgi-header img {
                max-width: 92vw;
                margin-bottom: 0.8rem;
            }
        }
    </style>
    """

    css = (
        css
        .replace("__PGI_PRIMARY__", COLOR_CORPORATIVO)
        .replace("__PGI_PRIMARY_DARK__", COLOR_CORPORATIVO_OSCURO)
        .replace("__PGI_BG__", COLOR_GRIS_FONDO)
        .replace("__PGI_BORDER__", COLOR_GRIS_BORDE)
    )

    st.markdown(css, unsafe_allow_html=True)


def mostrar_cabecera_app():
    if os.path.exists(LOGO_PATH):
        st.logo(LOGO_PATH, size="large")
        with open(LOGO_PATH, "rb") as logo_file:
            logo_base64 = base64.b64encode(logo_file.read()).decode("utf-8")

        st.markdown(
            f"""
            <div class="pgi-header">
                <img src="data:image/png;base64,{logo_base64}" alt="Logo">
                <div>
                    <h1>Energía</h1>
                    <p>Seguimiento operativo de simulaciones, consumos BMS, desviaciones, costes y emisiones.</p>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    else:
        st.title("Energía")
        st.caption("Seguimiento operativo de simulaciones, consumos BMS, desviaciones, costes y emisiones.")


def etiqueta_mes(mes):
    return f"{int(mes):02d} - {MESES[int(mes)]}"


def opciones_edificios(df):
    return [
        f"{row['codigo_proyecto']} - {row['nombre']}"
        for _, row in df.iterrows()
    ]


def codigo_desde_opcion(opcion):
    return opcion.split(" - ")[0]


def seleccionar_fila_edificio(df, codigo):
    return df[df["codigo_proyecto"] == codigo].iloc[0]


def mostrar_dataframe(df, height=None):
    config = {
        columna: COLUMN_CONFIG[columna]
        for columna in df.columns
        if columna in COLUMN_CONFIG
    }

    opciones = {
        "width": "stretch",
        "hide_index": True,
        "column_config": config,
    }

    if height is not None:
        opciones["height"] = height

    st.dataframe(df, **opciones)


def mostrar_mensaje_estado():
    mensaje = st.session_state.pop("mensaje_estado", None)
    if mensaje:
        st.success(mensaje)


def guardar_mensaje_y_recargar(mensaje):
    st.session_state["mensaje_estado"] = mensaje
    st.rerun()


def mostrar_contexto(codigo, edificio, anio, mes=None):
    periodo = str(anio)
    if mes is not None:
        periodo = f"{MESES[int(mes)]} {anio}"

    st.caption(
        f"Contexto activo: {codigo} · {edificio['nombre']} · {periodo}"
    )


def configurar_sidebar(edificios_activos):
    st.sidebar.header("Contexto")

    if edificios_activos.empty:
        st.sidebar.warning("Crea un edificio activo para empezar.")
        return None, None, ANIO_ACTUAL, 1

    opciones = opciones_edificios(edificios_activos)
    opcion = st.sidebar.selectbox("Edificio activo", opciones, key="global_edificio")
    codigo = codigo_desde_opcion(opcion)
    edificio = seleccionar_fila_edificio(edificios_activos, codigo)

    anio = st.sidebar.number_input(
        "Año de análisis",
        2000,
        2100,
        ANIO_ACTUAL,
        key="global_anio"
    )
    mes = st.sidebar.selectbox(
        "Mes de análisis",
        list(MESES.keys()),
        key="global_mes",
        format_func=etiqueta_mes
    )

    st.sidebar.divider()
    st.sidebar.metric("Código", codigo)
    st.sidebar.metric(
        "Superficie",
        f"{edificio['superficie_m2']:,.0f} m²"
        if pd.notna(edificio["superficie_m2"])
        else "Sin dato"
    )

    unidad_ref, valor_ref = obtener_valor_referencia(edificio)
    st.sidebar.metric("Referencia", f"{valor_ref:,.0f} {unidad_ref}" if valor_ref > 0 else "Sin dato")

    sim_activa = cargar_simulacion_activa(codigo)
    if sim_activa.empty:
        st.sidebar.warning("Sin simulación activa.")
    else:
        st.sidebar.success(f"Sim activa: {sim_activa.iloc[0]['nombre_simulacion']}")

    return codigo, edificio, int(anio), int(mes)
