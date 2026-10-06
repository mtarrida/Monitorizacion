"""Pestaña Simulaciones DesignBuilder."""

import os

import streamlit as st

from energia.db import (
    cargar_detalle_simulacion,
    cargar_simulaciones,
    crear_simulacion,
    guardar_detalle_simulacion,
    marcar_simulacion_activa,
)
from energia.parsers import transformar_dat_designbuilder
from energia.ui import guardar_mensaje_y_recargar, mostrar_contexto, mostrar_dataframe
from energia.utils import crear_carpetas_edificio


def mostrar(ctx):
    edificios_activos = ctx.edificios_activos
    codigo_global = ctx.codigo
    edificio_global = ctx.edificio
    anio_global = ctx.anio

    st.header("Simulaciones DesignBuilder")

    if edificios_activos.empty:
        st.warning("No hay edificios activos.")
    else:
        codigo = codigo_global
        edificio = edificio_global
        mostrar_contexto(codigo, edificio, anio_global)

        with st.form("importar_sim"):
            nombre = st.text_input("Nombre simulación", value="Simulación DesignBuilder")
            desc = st.text_area("Descripción")
            anio = st.number_input("Año", 2000, 2100, anio_global, key="sim_anio")
            activa = st.checkbox("Marcar como activa", value=True)
            archivo = st.file_uploader("Archivo .dat", type=["dat", "txt"])

            if st.form_submit_button("Importar simulación"):
                if archivo is None:
                    st.error("Sube un archivo .dat.")
                else:
                    df, ignoradas, errores = transformar_dat_designbuilder(archivo, anio)

                    if errores:
                        for e in errores:
                            st.error(e)
                        st.write(ignoradas)
                    else:
                        sim_id = crear_simulacion(codigo, nombre, desc, activa)
                        guardar_detalle_simulacion(sim_id, df)

                        carpeta = crear_carpetas_edificio(codigo, edificio["nombre"])
                        ruta = os.path.join(carpeta, "simulaciones", f"simulacion_{sim_id}.dat")

                        with open(ruta, "wb") as f:
                            f.write(archivo.getbuffer())

                        st.success("Simulación importada.")
                        mostrar_dataframe(df)

                        if ignoradas:
                            st.warning("Categorías ignoradas:")
                            st.write(ignoradas)

        sims = cargar_simulaciones(codigo)

        st.subheader("Simulaciones existentes")

        if sims.empty:
            st.warning("No hay simulaciones.")
        else:
            mostrar_dataframe(sims)

            opcion_sim = st.selectbox(
                "Ver detalle",
                [f"{r['id']} - {r['nombre_simulacion']}" for _, r in sims.iterrows()]
            )
            sim_id = int(opcion_sim.split(" - ")[0])
            detalle = cargar_detalle_simulacion(sim_id)

            mostrar_dataframe(detalle)

            if not detalle.empty:
                resumen = detalle.groupby("categoria")["consumo_kwh"].sum().reset_index()
                st.bar_chart(resumen.set_index("categoria")["consumo_kwh"])

            if st.button("Marcar como activa"):
                marcar_simulacion_activa(sim_id, codigo)
                guardar_mensaje_y_recargar("Simulación marcada como activa.")
