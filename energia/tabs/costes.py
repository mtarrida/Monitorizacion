"""Pestaña Costes energeticos."""

import pandas as pd
import streamlit as st

from energia.db import consumos_bms_anio
from energia.ui import mostrar_contexto, mostrar_dataframe


def mostrar(ctx):
    edificios_activos = ctx.edificios_activos
    codigo_global = ctx.codigo
    edificio_global = ctx.edificio
    anio_global = ctx.anio

    st.header("Costes energéticos")

    if edificios_activos.empty:
        st.warning("No hay edificios activos.")
    else:
        codigo = codigo_global
        edificio = edificio_global
        anio = anio_global
        mostrar_contexto(codigo, edificio, anio)

        c1, c2 = st.columns(2)
        precio_elec = c1.number_input("Precio electricidad €/kWh", min_value=0.0, value=0.18, step=0.01)
        precio_gas = c2.number_input("Precio gas natural €/kWh", min_value=0.0, value=0.07, step=0.01)

        df = consumos_bms_anio(codigo, anio)

        if df.empty:
            st.warning("No hay BMS cargado para este año.")
        else:
            df["coste_electricidad_eur"] = df["electricidad_kwh"] * precio_elec
            df["coste_gas_eur"] = df["gas_kwh"] * precio_gas
            df["coste_total_eur"] = df["coste_electricidad_eur"] + df["coste_gas_eur"]

            resumen_mes = df.groupby("mes").agg({
                "electricidad_kwh": "sum",
                "gas_kwh": "sum",
                "consumo_kwh": "sum",
                "coste_electricidad_eur": "sum",
                "coste_gas_eur": "sum",
                "coste_total_eur": "sum",
            }).reset_index()

            resumen_cat = df.groupby("categoria").agg({
                "electricidad_kwh": "sum",
                "gas_kwh": "sum",
                "consumo_kwh": "sum",
                "coste_total_eur": "sum",
            }).reset_index().sort_values("coste_total_eur", ascending=False)

            meses_cargados = resumen_mes["mes"].nunique()
            coste_total = resumen_mes["coste_total_eur"].sum()
            superficie = edificio["superficie_m2"] if pd.notna(edificio["superficie_m2"]) else 0
            coste_m2 = 0 if superficie == 0 else coste_total / superficie
            proy = 0 if meses_cargados == 0 else coste_total / meses_cargados * 12

            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Meses BMS", f"{meses_cargados}/12")
            c2.metric("Coste acumulado", f"{coste_total:,.0f} €")
            c3.metric("Coste €/m²", f"{coste_m2:.2f} €/m²")
            c4.metric("Proyección anual", f"{proy:,.0f} €")

            st.subheader("Coste mensual")
            mostrar_dataframe(resumen_mes)
            st.bar_chart(resumen_mes.set_index("mes")[["coste_electricidad_eur", "coste_gas_eur"]])

            st.subheader("Coste por categoría")
            mostrar_dataframe(resumen_cat)
