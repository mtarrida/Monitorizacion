"""Pestaña Comparativa simulacion vs BMS."""

import pandas as pd
import streamlit as st

from energia.analisis import (
    comparativa_mensual,
    comparativa_parcial_anual,
    indicador_especifico,
    obtener_valor_referencia,
)
from energia.db import cargar_simulacion_activa, consumos_bms_anio
from energia.graficos import (
    grafico_barras_comparativa,
    grafico_desviacion,
    grafico_evolucion_mensual,
    grafico_pareto_desviaciones,
    grafico_ranking_indicadores,
)
from energia.ui import mostrar_contexto, mostrar_dataframe


def mostrar(ctx):
    edificios_activos = ctx.edificios_activos
    edificios_todos = ctx.edificios_todos
    codigo_global = ctx.codigo
    edificio_global = ctx.edificio
    anio_global = ctx.anio
    mes_global = ctx.mes

    st.header("Comparativa Simulación vs BMS")

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
            st.success(f"Simulación activa: {sim_activa.iloc[0]['nombre_simulacion']}")

            subt1, subt2, subt3 = st.tabs(["Mensual", "Acumulada", "Base comparable"])

            with subt1:
                comp = comparativa_mensual(codigo, sim_id, anio, mes)

                if comp.empty:
                    st.warning("No hay BMS cargado para este mes.")
                else:
                    total_sim = comp["simulado_kwh"].sum()
                    total_real = comp["real_kwh"].sum()
                    desv = total_real - total_sim
                    pct = 0 if total_sim == 0 else desv / total_sim * 100
                    etiqueta_indicador, valor_indicador, _ = indicador_especifico(total_real, edificio)

                    c1, c2, c3, c4 = st.columns(4)
                    c1.metric("Simulado", f"{total_sim:,.0f} kWh")
                    c2.metric("Real BMS", f"{total_real:,.0f} kWh")
                    c3.metric("Desviación", f"{pct:.2f}%", f"{desv:,.0f} kWh")
                    c4.metric(etiqueta_indicador, f"{valor_indicador:.2f}")

                    st.subheader("Lectura rápida")
                    g1, g2 = st.columns([1, 1])
                    with g1:
                        grafico_barras_comparativa(comp, "Simulado frente a real por categoría")
                    with g2:
                        grafico_desviacion(comp, "Desviación por categoría")

                    grafico_pareto_desviaciones(comp, "Qué categorías explican la desviación")

                    st.subheader("Detalle")
                    mostrar_dataframe(comp)

            with subt2:
                df_meses, df_cat = comparativa_parcial_anual(codigo, sim_id, anio)

                if df_meses.empty:
                    st.warning("No hay BMS cargado para este año.")
                else:
                    meses_cargados = len(df_meses)
                    cobertura = meses_cargados / 12 * 100
                    total_sim = df_meses["simulado_kwh"].sum()
                    total_real = df_meses["real_kwh"].sum()
                    desv = total_real - total_sim
                    pct = 0 if total_sim == 0 else desv / total_sim * 100
                    proy = total_real / meses_cargados * 12
                    etiqueta_indicador, valor_indicador, _ = indicador_especifico(total_real, edificio)

                    c1, c2, c3, c4, c5 = st.columns(5)
                    c1.metric("Meses BMS", f"{meses_cargados}/12")
                    c2.metric("Cobertura", f"{cobertura:.0f}%")
                    c3.metric("Desviación acumulada", f"{pct:.2f}%", f"{desv:,.0f} kWh")
                    c4.metric("Proyección anual", f"{proy:,.0f} kWh")
                    c5.metric(f"{etiqueta_indicador} acum.", f"{valor_indicador:.2f}")

                    grafico_evolucion_mensual(df_meses, "Evolución mensual: simulado, real y desviación")

                    st.subheader("Categorías acumuladas")
                    g1, g2 = st.columns([1, 1])
                    with g1:
                        grafico_barras_comparativa(df_cat, "Acumulado por categoría")
                    with g2:
                        grafico_desviacion(df_cat, "Desviación acumulada por categoría")

                    st.subheader("Resumen mensual")
                    mostrar_dataframe(df_meses)

                    st.subheader("Detalle por categoría")
                    mostrar_dataframe(df_cat)

            with subt3:
                st.subheader("Base comparable de edificios")
                st.caption(
                    "Esta vista empieza a construir una base de datos útil para comparar edificios similares. "
                    "Cada edificio puede usar una unidad de referencia distinta: m², habitaciones, puestos, camas, usuarios u otra."
                )

                filas = []
                for _, edif in edificios_todos.iterrows():
                    df_edif = consumos_bms_anio(edif["codigo_proyecto"], anio)
                    total = 0 if df_edif.empty else df_edif["consumo_kwh"].sum()
                    etiqueta, indicador, unidad = indicador_especifico(total, edif)
                    unidad_ref, valor_ref = obtener_valor_referencia(edif)
                    filas.append({
                        "codigo_proyecto": edif["codigo_proyecto"],
                        "nombre": edif["nombre"],
                        "categoria_edificio": edif.get("categoria_edificio", edif.get("uso", "")),
                        "superficie_m2": edif.get("superficie_m2", 0),
                        "unidad_referencia": unidad_ref,
                        "valor_unidad_referencia": valor_ref,
                        "consumo_kwh": total,
                        "indicador_especifico": indicador,
                        "unidad_indicador": etiqueta,
                    })

                df_base = pd.DataFrame(filas)
                df_base = df_base[df_base["consumo_kwh"] > 0].copy()

                if df_base.empty:
                    st.warning("Todavía no hay consumos anuales suficientes para comparar edificios.")
                else:
                    categorias = sorted(df_base["categoria_edificio"].dropna().unique().tolist())
                    categoria_sel = st.multiselect("Filtrar por categoría", categorias, default=categorias)
                    df_filtrado = df_base[df_base["categoria_edificio"].isin(categoria_sel)] if categoria_sel else df_base

                    grafico_ranking_indicadores(
                        df_filtrado,
                        "Ranking de consumo específico para edificios comparables"
                    )
                    mostrar_dataframe(df_filtrado.sort_values(["categoria_edificio", "indicador_especifico"]))
