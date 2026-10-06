"""Pestaña Panel general."""

import streamlit as st

from energia.analisis import comparativa_mensual, indicador_especifico, obtener_valor_referencia
from energia.db import cargar_simulacion_activa, consumos_bms_anio, meses_bms
from energia.ui import mostrar_contexto, mostrar_dataframe


def mostrar(ctx):
    edificios_activos = ctx.edificios_activos
    codigo_global = ctx.codigo
    edificio_global = ctx.edificio
    anio_global = ctx.anio
    mes_global = ctx.mes

    st.header("Panel general")

    if edificios_activos.empty:
        st.warning("No hay edificios activos.")
    else:
        codigo = codigo_global
        edificio = edificio_global
        anio = anio_global
        mes = mes_global

        mostrar_contexto(codigo, edificio, anio, mes)

        sim_activa = cargar_simulacion_activa(codigo)
        meses = meses_bms(codigo, anio)
        df_anio = consumos_bms_anio(codigo, anio)

        total_real = 0 if df_anio.empty else df_anio["consumo_kwh"].sum()
        etiqueta_indicador, valor_indicador, unidad_indicador = indicador_especifico(total_real, edificio)

        desviacion_mes = "Sin dato"
        alertas_mes = 0

        if not sim_activa.empty:
            sim_id = int(sim_activa.iloc[0]["id"])
            comp_mes = comparativa_mensual(codigo, sim_id, anio, mes)

            if not comp_mes.empty:
                total_sim_mes = comp_mes["simulado_kwh"].sum()
                total_real_mes = comp_mes["real_kwh"].sum()
                desv_mes = total_real_mes - total_sim_mes
                pct_mes = 0 if total_sim_mes == 0 else desv_mes / total_sim_mes * 100
                desviacion_mes = f"{pct_mes:.2f}%"
                alertas_mes = len(comp_mes[abs(comp_mes["desviacion_pct"]) > 10])

        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Meses BMS", f"{len(meses)}/12")
        c2.metric("Consumo acumulado", f"{total_real:,.0f} kWh")
        c3.metric(f"{etiqueta_indicador} acumulado", f"{valor_indicador:.2f}")
        c4.metric("Desviación mes", desviacion_mes)

        info1, info2 = st.columns([1, 1])

        with info1:
            st.subheader("Edificio")
            st.write("**Nombre:**", edificio["nombre"])
            st.write("**Cliente:**", edificio["cliente"])
            st.write("**Ubicación:**", edificio["ubicacion"])
            st.write("**Uso:**", edificio["uso"])
            st.write("**Categoría:**", edificio.get("categoria_edificio", ""))
            st.write("**Referencia:**", f"{obtener_valor_referencia(edificio)[1]:,.0f} {obtener_valor_referencia(edificio)[0]}")
            st.write("**Sistema:**", edificio["sistema_climatizacion"])

        with info2:
            st.subheader("Estado operativo")
            if sim_activa.empty:
                st.warning("No hay simulación activa.")
            else:
                st.success(f"Simulación activa: {sim_activa.iloc[0]['nombre_simulacion']}")

            if alertas_mes == 0:
                st.success("Sin alertas relevantes en el mes activo.")
            else:
                st.warning(f"{alertas_mes} categorías superan el 10% de desviación.")

            st.metric("Cobertura anual", f"{len(meses) / 12 * 100:.0f}%")

        if not df_anio.empty:
            resumen_mes = df_anio.groupby("mes").agg({
                "electricidad_kwh": "sum",
                "gas_kwh": "sum",
                "consumo_kwh": "sum",
            }).reset_index()

            st.subheader("Consumo BMS acumulado")
            st.bar_chart(resumen_mes.set_index("mes")[["electricidad_kwh", "gas_kwh"]])
            mostrar_dataframe(resumen_mes)
