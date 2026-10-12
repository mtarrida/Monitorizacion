"""Graficos Plotly de la comparativa para la interfaz Streamlit.

Las figuras en sí viven en `figuras.py` (sin Streamlit); aquí solo se les fija el alto y se
dibujan con `st.plotly_chart`.
"""

import streamlit as st

from energia import figuras


def _dibujar(fig):
    st.plotly_chart(fig, use_container_width=True)


def grafico_barras_comparativa(df, titulo):
    if df.empty:
        return
    _dibujar(figuras.fig_barras_comparativa(df, titulo, altura=max(420, 32 * len(df))))


def grafico_desviacion(df, titulo):
    if df.empty:
        return
    _dibujar(figuras.fig_desviacion(df, titulo, altura=max(420, 32 * len(df))))


def grafico_pareto_desviaciones(df, titulo):
    if df.empty:
        return
    _dibujar(figuras.fig_pareto_desviaciones(df, titulo, altura=460))


def grafico_evolucion_mensual(df_meses, titulo):
    if df_meses.empty:
        return
    _dibujar(figuras.fig_evolucion_mensual(df_meses, titulo, altura=460))


def grafico_ranking_indicadores(df, titulo):
    if df.empty:
        return
    _dibujar(figuras.fig_ranking_indicadores(df, titulo, altura=max(420, 32 * len(df))))
