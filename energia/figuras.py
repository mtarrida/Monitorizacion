"""Figuras Plotly de la aplicación, sin Streamlit.

Las usan `graficos.py` (interfaz Streamlit) y `servicios.py` (interfaz web). Cada función
devuelve una `go.Figure`, o `None` si no hay datos que dibujar. `altura=None` deja que el
contenedor decida el alto (la interfaz web las dibuja a todo el canvas).
"""

import plotly.express as px
import plotly.graph_objects as go

from energia.config import COLOR_CORPORATIVO, MESES

COLOR_SIMULADO = "#A7B0BE"
COLOR_GRIS_OSCURO = "#4B5563"
COLOR_TEXTO = "#23272F"


def _vacio(df):
    return df is None or df.empty


def fig_barras_comparativa(df, titulo, altura=None):
    if _vacio(df):
        return None
    datos = df.copy().sort_values("real_kwh", ascending=True)
    fig = go.Figure()
    fig.add_bar(
        y=datos["categoria"],
        x=datos["simulado_kwh"],
        name="Simulado",
        orientation="h",
        marker_color=COLOR_SIMULADO,
    )
    fig.add_bar(
        y=datos["categoria"],
        x=datos["real_kwh"],
        name="Real BMS",
        orientation="h",
        marker_color=COLOR_CORPORATIVO,
    )
    fig.update_layout(
        title=titulo,
        barmode="group",
        height=altura,
        xaxis_title="kWh",
        yaxis_title="",
        legend_title="",
        margin=dict(l=10, r=10, t=55, b=10),
    )
    return fig


def fig_desviacion(df, titulo, altura=None):
    if _vacio(df):
        return None
    datos = df.copy().sort_values("desviacion_kwh")
    datos["tipo_desviacion"] = datos["desviacion_kwh"].apply(lambda x: "Mayor consumo" if x >= 0 else "Menor consumo")
    fig = px.bar(
        datos,
        y="categoria",
        x="desviacion_kwh",
        color="tipo_desviacion",
        orientation="h",
        text="desviacion_pct",
        title=titulo,
        labels={"desviacion_kwh": "Desviación kWh", "categoria": "", "tipo_desviacion": ""},
        color_discrete_map={"Mayor consumo": COLOR_CORPORATIVO, "Menor consumo": COLOR_GRIS_OSCURO},
    )
    fig.update_traces(texttemplate="%{text:.1f}%", textposition="outside", cliponaxis=False)
    fig.update_layout(height=altura, margin=dict(l=10, r=40, t=55, b=10))
    return fig


def fig_pareto_desviaciones(df, titulo, altura=None):
    if _vacio(df):
        return None
    datos = df.copy()
    datos["impacto_abs"] = datos["desviacion_kwh"].abs()
    datos = datos.sort_values("impacto_abs", ascending=False)
    total = datos["impacto_abs"].sum()
    datos["impacto_acumulado_pct"] = 0 if total == 0 else datos["impacto_abs"].cumsum() / total * 100

    fig = go.Figure()
    fig.add_bar(
        x=datos["categoria"],
        y=datos["impacto_abs"],
        name="Impacto absoluto",
        marker_color=COLOR_CORPORATIVO,
    )
    fig.add_scatter(
        x=datos["categoria"],
        y=datos["impacto_acumulado_pct"],
        name="Acumulado",
        yaxis="y2",
        mode="lines+markers",
        line=dict(color=COLOR_TEXTO, width=3),
    )
    fig.update_layout(
        title=titulo,
        yaxis=dict(title="kWh de desviación absoluta"),
        yaxis2=dict(title="Impacto acumulado %", overlaying="y", side="right", range=[0, 105]),
        xaxis=dict(title="", tickangle=-30),
        legend_title="",
        height=altura,
        margin=dict(l=10, r=10, t=55, b=80),
    )
    return fig


def fig_evolucion_mensual(df_meses, titulo, altura=None):
    if _vacio(df_meses):
        return None
    datos = df_meses.copy()
    datos["mes_nombre"] = datos["mes"].map(lambda m: MESES.get(int(m), str(m)))
    fig = go.Figure()
    fig.add_scatter(x=datos["mes_nombre"], y=datos["simulado_kwh"], name="Simulado", mode="lines+markers", line=dict(width=3, color=COLOR_SIMULADO))
    fig.add_scatter(x=datos["mes_nombre"], y=datos["real_kwh"], name="Real BMS", mode="lines+markers", line=dict(width=3, color=COLOR_CORPORATIVO))
    fig.add_bar(x=datos["mes_nombre"], y=datos["desviacion_kwh"], name="Desviación", marker_color=COLOR_GRIS_OSCURO, opacity=0.35)
    fig.update_layout(
        title=titulo,
        yaxis_title="kWh",
        xaxis_title="",
        legend_title="",
        height=altura,
        margin=dict(l=10, r=10, t=55, b=10),
    )
    return fig


def fig_ranking_indicadores(df, titulo, altura=None):
    if _vacio(df):
        return None
    fig = px.bar(
        df.sort_values("indicador_especifico", ascending=True),
        x="indicador_especifico",
        y="nombre",
        color="categoria_edificio",
        orientation="h",
        title=titulo,
        labels={"indicador_especifico": "Indicador específico", "nombre": "", "categoria_edificio": "Categoría"},
    )
    fig.update_layout(height=altura, margin=dict(l=10, r=10, t=55, b=10))
    return fig


def fig_apilada_mensual(df_mes, series, titulo, eje_y, altura=None):
    """Barras apiladas por mes. `series` = [(columna, etiqueta, color), ...]."""
    if _vacio(df_mes):
        return None
    datos = df_mes.copy()
    datos["mes_nombre"] = datos["mes"].map(lambda m: MESES.get(int(m), str(m)))
    fig = go.Figure()
    for columna, etiqueta, color in series:
        fig.add_bar(x=datos["mes_nombre"], y=datos[columna], name=etiqueta, marker_color=color)
    fig.update_layout(
        title=titulo,
        barmode="stack",
        yaxis_title=eje_y,
        xaxis_title="",
        legend_title="",
        height=altura,
        margin=dict(l=10, r=10, t=55, b=10),
    )
    return fig


def fig_barras_categoria(df, columna, titulo, eje_x, altura=None, color=COLOR_CORPORATIVO):
    """Barras horizontales de un valor por categoría, de menor a mayor."""
    if _vacio(df):
        return None
    datos = df.copy().sort_values(columna, ascending=True)
    fig = go.Figure()
    fig.add_bar(y=datos["categoria"], x=datos[columna], orientation="h", marker_color=color, name=eje_x)
    fig.update_layout(
        title=titulo,
        xaxis_title=eje_x,
        yaxis_title="",
        showlegend=False,
        height=altura,
        margin=dict(l=10, r=10, t=55, b=10),
    )
    return fig
