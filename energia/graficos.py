"""Graficos Plotly de la comparativa."""

import streamlit as st

from energia.config import COLOR_CORPORATIVO, MESES

try:
    import plotly.express as px
    import plotly.graph_objects as go
except Exception:
    px = None
    go = None


def plotly_disponible():
    if px is None or go is None:
        st.info("Para activar los gráficos avanzados instala Plotly: pip install plotly")
        return False
    return True


def grafico_barras_comparativa(df, titulo):
    if not plotly_disponible() or df.empty:
        return
    datos = df.copy().sort_values("real_kwh", ascending=True)
    fig = go.Figure()
    fig.add_bar(
        y=datos["categoria"],
        x=datos["simulado_kwh"],
        name="Simulado",
        orientation="h",
        marker_color="#A7B0BE",
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
        height=max(420, 32 * len(datos)),
        xaxis_title="kWh",
        yaxis_title="",
        legend_title="",
        margin=dict(l=10, r=10, t=55, b=10),
    )
    st.plotly_chart(fig, use_container_width=True)


def grafico_desviacion(df, titulo):
    if not plotly_disponible() or df.empty:
        return
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
        color_discrete_map={"Mayor consumo": COLOR_CORPORATIVO, "Menor consumo": "#4B5563"},
    )
    fig.update_traces(texttemplate="%{text:.1f}%", textposition="outside", cliponaxis=False)
    fig.update_layout(height=max(420, 32 * len(datos)), margin=dict(l=10, r=40, t=55, b=10))
    st.plotly_chart(fig, use_container_width=True)


def grafico_pareto_desviaciones(df, titulo):
    if not plotly_disponible() or df.empty:
        return
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
        line=dict(color="#23272F", width=3),
    )
    fig.update_layout(
        title=titulo,
        yaxis=dict(title="kWh de desviación absoluta"),
        yaxis2=dict(title="Impacto acumulado %", overlaying="y", side="right", range=[0, 105]),
        xaxis=dict(title="", tickangle=-30),
        legend_title="",
        height=460,
        margin=dict(l=10, r=10, t=55, b=80),
    )
    st.plotly_chart(fig, use_container_width=True)


def grafico_evolucion_mensual(df_meses, titulo):
    if not plotly_disponible() or df_meses.empty:
        return
    datos = df_meses.copy()
    datos["mes_nombre"] = datos["mes"].map(lambda m: MESES.get(int(m), str(m)))
    fig = go.Figure()
    fig.add_scatter(x=datos["mes_nombre"], y=datos["simulado_kwh"], name="Simulado", mode="lines+markers", line=dict(width=3, color="#A7B0BE"))
    fig.add_scatter(x=datos["mes_nombre"], y=datos["real_kwh"], name="Real BMS", mode="lines+markers", line=dict(width=3, color=COLOR_CORPORATIVO))
    fig.add_bar(x=datos["mes_nombre"], y=datos["desviacion_kwh"], name="Desviación", marker_color="#4B5563", opacity=0.35)
    fig.update_layout(
        title=titulo,
        yaxis_title="kWh",
        xaxis_title="",
        legend_title="",
        height=460,
        margin=dict(l=10, r=10, t=55, b=10),
    )
    st.plotly_chart(fig, use_container_width=True)


def grafico_ranking_indicadores(df, titulo):
    if not plotly_disponible() or df.empty:
        return
    fig = px.bar(
        df.sort_values("indicador_especifico", ascending=True),
        x="indicador_especifico",
        y="nombre",
        color="categoria_edificio",
        orientation="h",
        title=titulo,
        labels={"indicador_especifico": "Indicador específico", "nombre": "", "categoria_edificio": "Categoría"},
    )
    fig.update_layout(height=max(420, 32 * len(df)), margin=dict(l=10, r=10, t=55, b=10))
    st.plotly_chart(fig, use_container_width=True)
