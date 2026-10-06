"""Pestaña Informe mensual."""

import streamlit as st

from energia.analisis import comparativa_mensual, generar_observaciones, indicador_especifico
from energia.db import cargar_simulacion_activa
from energia.ui import mostrar_contexto, mostrar_dataframe


def mostrar(ctx):
    edificios_activos = ctx.edificios_activos
    codigo_global = ctx.codigo
    edificio_global = ctx.edificio
    anio_global = ctx.anio
    mes_global = ctx.mes

    st.header("Informe mensual")

    if edificios_activos.empty:
        st.warning("No hay edificios activos.")
    else:
        codigo = codigo_global
        edificio = edificio_global
        anio = anio_global
        mes = mes_global
        mostrar_contexto(codigo, edificio, anio, mes)

        sim_activa = cargar_simulacion_activa(codigo)

        if sim_activa.empty:
            st.warning("No hay simulación activa.")
        else:
            sim_id = int(sim_activa.iloc[0]["id"])
            comp = comparativa_mensual(codigo, sim_id, anio, mes)

            if comp.empty:
                st.warning("No hay BMS cargado para este mes.")
            else:
                total_sim = comp["simulado_kwh"].sum()
                total_real = comp["real_kwh"].sum()
                desv = total_real - total_sim
                pct = 0 if total_sim == 0 else desv / total_sim * 100
                etiqueta_indicador, valor_indicador, _ = indicador_especifico(total_real, edificio)

                alertas = comp[abs(comp["desviacion_pct"]) > 10].copy()
                observaciones = generar_observaciones(comp)

                c1, c2, c3, c4 = st.columns(4)
                c1.metric("Simulado", f"{total_sim:,.0f} kWh")
                c2.metric("Real BMS", f"{total_real:,.0f} kWh")
                c3.metric("Desviación", f"{pct:.2f}%")
                c4.metric(f"{etiqueta_indicador} mes", f"{valor_indicador:.2f}")

                st.subheader("Alertas")
                if alertas.empty:
                    st.success("No se detectan desviaciones relevantes superiores al 10%.")
                else:
                    mostrar_dataframe(alertas[["categoria", "simulado_kwh", "real_kwh", "desviacion_pct", "estado"]])

                st.subheader("Comparativa")
                mostrar_dataframe(comp)

                st.subheader("Observaciones")
                st.markdown(observaciones)

                alertas_txt = "No se detectan alertas relevantes."
                if not alertas.empty:
                    alertas_txt = "\n".join(
                        f"{r['estado']} {r['categoria']}: {r['desviacion_pct']:.2f}%"
                        for _, r in alertas.iterrows()
                    )

                texto = f"""
INFORME MENSUAL ENERGÉTICO

Proyecto: {edificio['nombre']}
Código: {edificio['codigo_proyecto']}
Cliente: {edificio['cliente']}
Ubicación: {edificio['ubicacion']}
Periodo analizado: {mes}/{anio}

RESUMEN EJECUTIVO

Consumo simulado: {total_sim:,.0f} kWh
Consumo real BMS: {total_real:,.0f} kWh
Desviación: {desv:,.0f} kWh
Desviación porcentual: {pct:.2f} %
Indicador específico mensual: {valor_indicador:.2f} {etiqueta_indicador} mes

ALERTAS DETECTADAS

{alertas_txt}

OBSERVACIONES TÉCNICAS

{observaciones}
"""

                st.text_area("Texto base del informe", texto, height=350)

                st.download_button(
                    "Descargar TXT",
                    data=texto,
                    file_name=f"informe_{codigo}_{anio}_{mes:02d}.txt",
                    mime="text/plain"
                )
