"""Pestaña Emisiones de CO2."""

import pandas as pd
import streamlit as st

from energia.db import consumos_bms_anio
from energia.ui import mostrar_contexto, mostrar_dataframe


def mostrar(ctx):
    edificios_activos = ctx.edificios_activos
    codigo_global = ctx.codigo
    edificio_global = ctx.edificio
    anio_global = ctx.anio

    st.header("Emisiones CO₂")

    if edificios_activos.empty:
        st.warning("No hay edificios activos.")
    else:
        codigo = codigo_global
        edificio = edificio_global
        anio = anio_global
        mostrar_contexto(codigo, edificio, anio)

        c1, c2 = st.columns(2)
        factor_elec = c1.number_input("Electricidad kgCO₂/kWh", min_value=0.0, value=0.18, step=0.01)
        factor_gas = c2.number_input("Gas natural kgCO₂/kWh", min_value=0.0, value=0.20, step=0.01)

        df = consumos_bms_anio(codigo, anio)

        if df.empty:
            st.warning("No hay BMS cargado para este año.")
        else:
            df["co2_electricidad_kg"] = df["electricidad_kwh"] * factor_elec
            df["co2_gas_kg"] = df["gas_kwh"] * factor_gas
            df["co2_total_kg"] = df["co2_electricidad_kg"] + df["co2_gas_kg"]

            resumen_mes = df.groupby("mes").agg({
                "electricidad_kwh": "sum",
                "gas_kwh": "sum",
                "co2_electricidad_kg": "sum",
                "co2_gas_kg": "sum",
                "co2_total_kg": "sum",
            }).reset_index()

            resumen_cat = df.groupby("categoria").agg({
                "co2_total_kg": "sum",
                "electricidad_kwh": "sum",
                "gas_kwh": "sum",
            }).reset_index().sort_values("co2_total_kg", ascending=False)

            meses_cargados = resumen_mes["mes"].nunique()
            co2_total_kg = resumen_mes["co2_total_kg"].sum()
            co2_tn = co2_total_kg / 1000
            superficie = edificio["superficie_m2"] if pd.notna(edificio["superficie_m2"]) else 0
            co2_m2 = 0 if superficie == 0 else co2_total_kg / superficie
            proy_tn = 0 if meses_cargados == 0 else co2_tn / meses_cargados * 12

            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Meses BMS", f"{meses_cargados}/12")
            c2.metric("CO₂ acumulado", f"{co2_tn:,.2f} tCO₂")
            c3.metric("kgCO₂/m²", f"{co2_m2:.2f}")
            c4.metric("Proyección anual", f"{proy_tn:,.2f} tCO₂")

            st.subheader("CO₂ mensual")
            mostrar_dataframe(resumen_mes)
            st.bar_chart(resumen_mes.set_index("mes")[["co2_electricidad_kg", "co2_gas_kg"]])

            st.subheader("CO₂ por categoría")
            mostrar_dataframe(resumen_cat)
