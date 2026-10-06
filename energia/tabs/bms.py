"""Pestaña de consumos reales BMS."""

import os

import streamlit as st

from energia.db import (
    cargar_consumos_bms,
    cargar_detalle_bms,
    crear_consumo_bms,
    guardar_detalle_bms,
)
from energia.parsers import transformar_csv_bms
from energia.ui import mostrar_contexto, mostrar_dataframe
from energia.utils import crear_carpetas_edificio


def mostrar(ctx):
    edificios_activos = ctx.edificios_activos
    codigo_global = ctx.codigo
    edificio_global = ctx.edificio
    anio_global = ctx.anio
    mes_global = ctx.mes

    st.header("Consumos reales BMS")

    if edificios_activos.empty:
        st.warning("No hay edificios activos.")
    else:
        codigo = codigo_global
        edificio = edificio_global
        anio = anio_global
        mes = mes_global
        mostrar_contexto(codigo, edificio, anio, mes)

        modo = st.radio("Modo", ["Un mes", "Varios meses"], horizontal=True)

        if modo == "Un mes":
            with st.form("bms_un_mes"):
                nombre = st.text_input("Nombre importación", value=f"BMS {anio}-{mes:02d}")
                desc = st.text_area("Descripción")
                archivo = st.file_uploader("CSV BMS", type=["csv"])

                if st.form_submit_button("Importar BMS"):
                    if archivo is None:
                        st.error("Sube un CSV.")
                    else:
                        df, errores = transformar_csv_bms(archivo)

                        if errores:
                            for e in errores:
                                st.error(e)
                        else:
                            bms_id = crear_consumo_bms(codigo, anio, mes, nombre, desc)
                            guardar_detalle_bms(bms_id, df)

                            carpeta = crear_carpetas_edificio(codigo, edificio["nombre"])
                            ruta = os.path.join(carpeta, "consumos_bms", f"bms_{anio}_{mes:02d}_{bms_id}.csv")

                            with open(ruta, "wb") as f:
                                f.write(archivo.getbuffer())

                            st.success("BMS importado.")
                            mostrar_dataframe(df)

        else:
            archivos = st.file_uploader("CSV BMS", type=["csv"], accept_multiple_files=True)

            if archivos:
                asignaciones = []

                for i, archivo in enumerate(archivos):
                    c1, c2 = st.columns([3, 1])
                    c1.write(archivo.name)
                    mes = c2.selectbox("Mes", list(range(1, 13)), key=f"mes_bms_{i}")
                    asignaciones.append((archivo, mes))

                if st.button("Importar todos"):
                    importados = 0

                    for archivo, mes in asignaciones:
                        df, errores = transformar_csv_bms(archivo)

                        if errores:
                            st.error(f"{archivo.name}: {errores}")
                            continue

                        bms_id = crear_consumo_bms(
                            codigo,
                            anio,
                            mes,
                            f"BMS {anio}-{mes:02d} - {archivo.name}",
                            "Carga múltiple"
                        )
                        guardar_detalle_bms(bms_id, df)

                        carpeta = crear_carpetas_edificio(codigo, edificio["nombre"])
                        ruta = os.path.join(carpeta, "consumos_bms", f"bms_{anio}_{mes:02d}_{bms_id}_{archivo.name}")

                        with open(ruta, "wb") as f:
                            f.write(archivo.getbuffer())

                        importados += 1

                    st.success(f"Importados: {importados}")

        st.subheader("BMS existentes")

        bms = cargar_consumos_bms(codigo)

        if bms.empty:
            st.warning("No hay consumos BMS.")
        else:
            mostrar_dataframe(bms)

            opcion_bms = st.selectbox(
                "Ver detalle",
                [f"{r['id']} - {r['anio']}-{int(r['mes']):02d} - {r['nombre_importacion']}" for _, r in bms.iterrows()]
            )

            bms_id = int(opcion_bms.split(" - ")[0])
            detalle = cargar_detalle_bms(bms_id)

            mostrar_dataframe(detalle)
