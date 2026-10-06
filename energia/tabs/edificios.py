"""Pestaña Edificios: crear, editar, archivar y eliminar."""

import pandas as pd
import streamlit as st

from energia.config import TIPOS_EDIFICIO, UNIDADES_REFERENCIA
from energia.db import (
    actualizar_edificio,
    cambiar_estado_edificio,
    eliminar_edificio,
    guardar_edificio,
    resumen_datos_edificio,
)
from energia.ui import guardar_mensaje_y_recargar, mostrar_dataframe
from energia.utils import crear_carpetas_edificio


def mostrar(ctx):
    edificios_todos = ctx.edificios_todos

    st.header("Gestión de edificios")

    sub1, sub2, sub3, sub4 = st.tabs(["Crear", "Editar", "Archivar / Reactivar", "Eliminar"])

    with sub1:
        with st.form("crear_edificio"):
            codigo = st.text_input("Código", placeholder="EDIF-2026-001")
            nombre = st.text_input("Nombre")
            cliente = st.text_input("Cliente")
            ubicacion = st.text_input("Ubicación")
            categoria_edificio = st.selectbox("Categoría de edificio", TIPOS_EDIFICIO, index=0)
            uso = st.text_input("Uso", value=categoria_edificio)
            superficie = st.number_input("Superficie m²", min_value=0.0, step=100.0)

            c_ref1, c_ref2 = st.columns(2)
            unidad_referencia = c_ref1.selectbox("Unidad principal para comparar", UNIDADES_REFERENCIA, index=0)
            valor_unidad_referencia = c_ref2.number_input("Valor de la unidad principal", min_value=0.0, step=1.0)

            c_car1, c_car2, c_car3 = st.columns(3)
            habitaciones = c_car1.number_input("Habitaciones", min_value=0.0, step=1.0)
            puestos_trabajo = c_car2.number_input("Puestos de trabajo", min_value=0.0, step=1.0)
            camas = c_car3.number_input("Camas", min_value=0.0, step=1.0)
            horario_uso = st.text_input("Horario de uso", placeholder="Ej. 24/7, laborables 8-20 h")
            sistema = st.text_input("Sistema climatización")
            obs = st.text_area("Observaciones")

            if st.form_submit_button("Crear edificio"):
                codigo = codigo.strip().upper()
                nombre = nombre.strip()

                if codigo == "" or nombre == "":
                    st.error("Código y nombre son obligatorios.")
                elif codigo in edificios_todos["codigo_proyecto"].values:
                    st.error("Ya existe ese código.")
                else:
                    guardar_edificio({
                        "codigo_proyecto": codigo,
                        "nombre": nombre,
                        "cliente": cliente,
                        "ubicacion": ubicacion,
                        "uso": uso,
                        "superficie_m2": superficie,
                        "categoria_edificio": categoria_edificio,
                        "unidad_referencia": unidad_referencia,
                        "valor_unidad_referencia": valor_unidad_referencia,
                        "habitaciones": habitaciones,
                        "puestos_trabajo": puestos_trabajo,
                        "camas": camas,
                        "horario_uso": horario_uso,
                        "sistema_climatizacion": sistema,
                        "observaciones": obs,
                    })
                    carpeta = crear_carpetas_edificio(codigo, nombre)
                    st.info(carpeta)
                    guardar_mensaje_y_recargar("Edificio creado.")

    with sub2:
        if edificios_todos.empty:
            st.warning("No hay edificios.")
        else:
            opcion = st.selectbox(
                "Edificio",
                edificios_todos["codigo_proyecto"] + " - " + edificios_todos["nombre"],
                key="editar_edificio"
            )
            codigo = opcion.split(" - ")[0]
            edificio = edificios_todos[edificios_todos["codigo_proyecto"] == codigo].iloc[0]

            with st.form("editar_edificio"):
                nombre = st.text_input("Nombre", value=edificio["nombre"])
                cliente = st.text_input("Cliente", value=edificio["cliente"] or "")
                ubicacion = st.text_input("Ubicación", value=edificio["ubicacion"] or "")
                categoria_actual = edificio.get("categoria_edificio", edificio["uso"] or "Oficinas")
                idx_categoria = TIPOS_EDIFICIO.index(categoria_actual) if categoria_actual in TIPOS_EDIFICIO else 0
                categoria_edificio = st.selectbox("Categoría de edificio", TIPOS_EDIFICIO, index=idx_categoria)
                uso = st.text_input("Uso", value=edificio["uso"] or categoria_edificio)
                superficie = st.number_input(
                    "Superficie m²",
                    min_value=0.0,
                    step=100.0,
                    value=float(edificio["superficie_m2"]) if pd.notna(edificio["superficie_m2"]) else 0.0
                )

                unidad_actual = edificio.get("unidad_referencia", "m²")
                idx_unidad = UNIDADES_REFERENCIA.index(unidad_actual) if unidad_actual in UNIDADES_REFERENCIA else 0
                c_ref1, c_ref2 = st.columns(2)
                unidad_referencia = c_ref1.selectbox("Unidad principal para comparar", UNIDADES_REFERENCIA, index=idx_unidad)
                valor_unidad_referencia = c_ref2.number_input(
                    "Valor de la unidad principal",
                    min_value=0.0,
                    step=1.0,
                    value=float(edificio.get("valor_unidad_referencia", 0) or 0),
                )

                c_car1, c_car2, c_car3 = st.columns(3)
                habitaciones = c_car1.number_input("Habitaciones", min_value=0.0, step=1.0, value=float(edificio.get("habitaciones", 0) or 0))
                puestos_trabajo = c_car2.number_input("Puestos de trabajo", min_value=0.0, step=1.0, value=float(edificio.get("puestos_trabajo", 0) or 0))
                camas = c_car3.number_input("Camas", min_value=0.0, step=1.0, value=float(edificio.get("camas", 0) or 0))
                horario_uso = st.text_input("Horario de uso", value=edificio.get("horario_uso", "") or "")
                sistema = st.text_input("Sistema climatización", value=edificio["sistema_climatizacion"] or "")
                obs = st.text_area("Observaciones", value=edificio["observaciones"] or "")

                if st.form_submit_button("Guardar cambios"):
                    actualizar_edificio(codigo, {
                        "nombre": nombre,
                        "cliente": cliente,
                        "ubicacion": ubicacion,
                        "uso": uso,
                        "superficie_m2": superficie,
                        "categoria_edificio": categoria_edificio,
                        "unidad_referencia": unidad_referencia,
                        "valor_unidad_referencia": valor_unidad_referencia,
                        "habitaciones": habitaciones,
                        "puestos_trabajo": puestos_trabajo,
                        "camas": camas,
                        "horario_uso": horario_uso,
                        "sistema_climatizacion": sistema,
                        "observaciones": obs,
                    })
                    crear_carpetas_edificio(codigo, nombre)
                    guardar_mensaje_y_recargar("Edificio actualizado.")

    with sub3:
        mostrar_dataframe(edificios_todos)

        if not edificios_todos.empty:
            opcion = st.selectbox(
                "Edificio",
                edificios_todos["codigo_proyecto"] + " - " + edificios_todos["nombre"],
                key="estado_edificio"
            )
            codigo = opcion.split(" - ")[0]

            c1, c2 = st.columns(2)

            with c1:
                if st.button("Archivar"):
                    cambiar_estado_edificio(codigo, "ARCHIVADO")
                    guardar_mensaje_y_recargar("Edificio archivado.")

            with c2:
                if st.button("Reactivar"):
                    cambiar_estado_edificio(codigo, "ACTIVO")
                    guardar_mensaje_y_recargar("Edificio reactivado.")

    with sub4:
        st.warning(
            "Eliminar un proyecto borra definitivamente el edificio y sus datos de "
            "simulaciones/BMS en la base de datos. Las carpetas y archivos guardados se conservan."
        )

        if edificios_todos.empty:
            st.warning("No hay edificios para eliminar.")
        else:
            opcion = st.selectbox(
                "Proyecto a eliminar",
                edificios_todos["codigo_proyecto"] + " - " + edificios_todos["nombre"],
                key="eliminar_edificio"
            )
            codigo = opcion.split(" - ")[0]
            edificio = edificios_todos[edificios_todos["codigo_proyecto"] == codigo].iloc[0]
            resumen = resumen_datos_edificio(codigo)

            st.write("**Proyecto:**", edificio["nombre"])
            st.write("**Cliente:**", edificio["cliente"])
            st.write("**Estado:**", edificio["estado"])

            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Simulaciones", resumen["simulaciones"])
            c2.metric("Filas simulación", resumen["detalle_simulaciones"])
            c3.metric("BMS importados", resumen["consumos_bms"])
            c4.metric("Filas BMS", resumen["detalle_bms"])

            confirmacion = st.text_input(
                f"Escribe {codigo} para confirmar",
                key="confirmar_eliminar_edificio"
            )
            acepta = st.checkbox(
                "Entiendo que esta acción no se puede deshacer.",
                key="aceptar_eliminar_edificio"
            )
            puede_eliminar = acepta and confirmacion.strip().upper() == codigo

            if st.button(
                "Eliminar proyecto definitivamente",
                disabled=not puede_eliminar,
                type="primary"
            ):
                eliminados = eliminar_edificio(codigo)
                guardar_mensaje_y_recargar(
                    "Proyecto eliminado. "
                    f"Se borraron {eliminados['simulaciones']} simulaciones y "
                    f"{eliminados['consumos_bms']} importaciones BMS."
                )
