"""Servicios de la interfaz web: reúnen datos y figuras listos para enviar como JSON.

Sin Streamlit. Cada función recibe valores simples y devuelve diccionarios o listas
serializables. Si falta un dato previo (edificio, simulación activa, BMS) devuelve
`{"aviso": "..."}` para que la interfaz lo muestre en el canvas en lugar de un error. Los
errores de validación se lanzan como `ValueError` con un mensaje apto para el usuario.
"""

import json
import os

import pandas as pd

from energia import config, figuras
from energia.analisis import (
    comparativa_mensual,
    comparativa_parcial_anual,
    generar_observaciones,
    indicador_especifico,
    obtener_valor_referencia,
)
from energia.config import COLOR_CORPORATIVO, MESES, TIPOS_EDIFICIO, UNIDADES_REFERENCIA
from energia.db import (
    actualizar_edificio,
    cambiar_estado_edificio,
    cargar_consumos_bms,
    cargar_detalle_bms,
    cargar_detalle_simulacion,
    cargar_edificios,
    cargar_simulacion_activa,
    cargar_simulaciones,
    consumos_bms_anio,
    crear_consumo_bms,
    crear_simulacion,
    eliminar_edificio,
    guardar_detalle_bms,
    guardar_correo_edificio,
    guardar_detalle_simulacion,
    guardar_edificio,
    marcar_simulacion_activa,
    meses_bms,
    resumen_datos_edificio,
)
from energia.parsers import transformar_csv_bms, transformar_dat_designbuilder
from energia.utils import crear_carpetas_edificio

COLOR_GAS = "#6B7280"
MAX_FILAS_VISTA_PREVIA = 50


# ---------------------------------------------------------------------------
# Conversión a JSON
# ---------------------------------------------------------------------------

def registros(df):
    """DataFrame -> lista de diccionarios (NaN pasa a null)."""
    if df is None or df.empty:
        return []
    return json.loads(df.to_json(orient="records", force_ascii=False))


def ficha(serie):
    """Fila de pandas -> diccionario."""
    return json.loads(serie.to_json(force_ascii=False))


def figura(fig):
    return None if fig is None else json.loads(fig.to_json())


def _aviso(mensaje):
    return {"aviso": mensaje}


class _Archivo:
    """Imita el archivo subido de Streamlit (los lectores solo usan getvalue)."""

    def __init__(self, contenido, nombre="archivo"):
        self.contenido = contenido
        self.name = nombre

    def getvalue(self):
        return self.contenido


def _edificio(codigo):
    if not codigo:
        return None
    df = cargar_edificios(True)
    fila = df[df["codigo_proyecto"] == codigo]
    return None if fila.empty else fila.iloc[0]


def _sim_activa(codigo):
    sim = cargar_simulacion_activa(codigo)
    if sim.empty:
        return None, None
    return int(sim.iloc[0]["id"]), str(sim.iloc[0]["nombre_simulacion"])


def _superficie(edificio):
    valor = edificio.get("superficie_m2", 0)
    return 0.0 if pd.isna(valor) else float(valor)


# ---------------------------------------------------------------------------
# Configuración y edificios
# ---------------------------------------------------------------------------

def config_app():
    return {
        "meses": [{"num": n, "nombre": nombre} for n, nombre in MESES.items()],
        "tipos_edificio": TIPOS_EDIFICIO,
        "unidades_referencia": UNIDADES_REFERENCIA,
        "anio_actual": config.ANIO_ACTUAL,
    }


def lista_edificios(todos=False):
    return registros(cargar_edificios(bool(todos)))


_CAMPOS_TEXTO = [
    "nombre", "cliente", "ubicacion", "uso", "categoria_edificio", "unidad_referencia",
    "horario_uso", "sistema_climatizacion", "observaciones",
]
_CAMPOS_NUMERO = ["superficie_m2", "valor_unidad_referencia", "habitaciones", "puestos_trabajo", "camas"]


def _datos_edificio(datos):
    salida = {campo: str(datos.get(campo) or "").strip() for campo in _CAMPOS_TEXTO}
    for campo in _CAMPOS_NUMERO:
        try:
            salida[campo] = float(datos.get(campo) or 0)
        except (TypeError, ValueError):
            raise ValueError(f"El campo {campo} tiene que ser un número.")
        if salida[campo] < 0:
            raise ValueError(f"El campo {campo} no puede ser negativo.")
    if not salida["categoria_edificio"]:
        salida["categoria_edificio"] = TIPOS_EDIFICIO[0]
    if not salida["uso"]:
        salida["uso"] = salida["categoria_edificio"]
    if not salida["unidad_referencia"]:
        salida["unidad_referencia"] = UNIDADES_REFERENCIA[0]
    return salida


def crear_edificio(datos):
    codigo = str(datos.get("codigo_proyecto") or "").strip().upper()
    nombre = str(datos.get("nombre") or "").strip()
    if not codigo or not nombre:
        raise ValueError("Código y nombre son obligatorios.")
    if codigo in cargar_edificios(True)["codigo_proyecto"].values:
        raise ValueError("Ya existe ese código.")

    campos = _datos_edificio(datos)
    campos["codigo_proyecto"] = codigo
    guardar_edificio(campos)
    carpeta = crear_carpetas_edificio(codigo, campos["nombre"])
    return {"codigo": codigo, "carpeta": carpeta}


def editar_edificio(codigo, datos):
    if _edificio(codigo) is None:
        raise ValueError("No existe ese edificio.")
    if not str(datos.get("nombre") or "").strip():
        raise ValueError("El nombre es obligatorio.")
    campos = _datos_edificio(datos)
    actualizar_edificio(codigo, campos)
    crear_carpetas_edificio(codigo, campos["nombre"])
    return {"codigo": codigo}


def cambiar_estado(codigo, estado):
    if estado not in ("ACTIVO", "ARCHIVADO"):
        raise ValueError("Estado no válido.")
    if _edificio(codigo) is None:
        raise ValueError("No existe ese edificio.")
    cambiar_estado_edificio(codigo, estado)
    return {"codigo": codigo, "estado": estado}


def guardar_correo(codigo, asunto, remitente):
    """Guarda las palabras clave del correo que trae los CSV de este edificio."""
    if _edificio(codigo) is None:
        raise ValueError("No existe ese edificio.")
    asunto = " ".join(str(asunto or "").split())
    remitente = str(remitente or "").strip()
    guardar_correo_edificio(codigo, asunto, remitente)
    return {"codigo": codigo, "correo_asunto": asunto, "correo_remitente": remitente}


def resumen_eliminacion(codigo):
    edificio = _edificio(codigo)
    if edificio is None:
        return _aviso("No existe ese edificio.")
    return {"edificio": ficha(edificio), "resumen": resumen_datos_edificio(codigo)}


def borrar_edificio(codigo, confirmacion):
    if _edificio(codigo) is None:
        raise ValueError("No existe ese edificio.")
    if str(confirmacion or "").strip().upper() != str(codigo).upper():
        raise ValueError(f"Escribe {codigo} para confirmar.")
    return eliminar_edificio(codigo)


# ---------------------------------------------------------------------------
# Panel
# ---------------------------------------------------------------------------

def panel(codigo, anio, mes):
    edificio = _edificio(codigo)
    if edificio is None:
        return _aviso("No hay edificios activos. Crea uno en Edificios.")

    sim_id, sim_nombre = _sim_activa(codigo)
    meses = meses_bms(codigo, anio)
    df_anio = consumos_bms_anio(codigo, anio)

    total_real = 0.0 if df_anio.empty else float(df_anio["consumo_kwh"].sum())
    etiqueta, valor, _ = indicador_especifico(total_real, edificio)
    unidad_ref, valor_ref = obtener_valor_referencia(edificio)

    desviacion_mes_pct = None
    alertas_mes = 0
    if sim_id is not None:
        comp = comparativa_mensual(codigo, sim_id, anio, mes)
        if not comp.empty:
            total_sim = float(comp["simulado_kwh"].sum())
            total_real_mes = float(comp["real_kwh"].sum())
            desviacion_mes_pct = 0.0 if total_sim == 0 else (total_real_mes - total_sim) / total_sim * 100
            alertas_mes = int((comp["desviacion_pct"].abs() > 10).sum())

    resumen_mes = pd.DataFrame()
    fig = None
    if not df_anio.empty:
        resumen_mes = df_anio.groupby("mes").agg({
            "electricidad_kwh": "sum",
            "gas_kwh": "sum",
            "consumo_kwh": "sum",
        }).reset_index()
        fig = figuras.fig_apilada_mensual(
            resumen_mes,
            [("electricidad_kwh", "Electricidad", COLOR_CORPORATIVO), ("gas_kwh", "Gas natural", COLOR_GAS)],
            "Consumo BMS acumulado",
            "kWh",
        )

    return {
        "edificio": ficha(edificio),
        "referencia": {"unidad": unidad_ref, "valor": valor_ref},
        "simulacion_activa": sim_nombre,
        "kpis": {
            "meses_bms": len(meses),
            "consumo_acumulado_kwh": total_real,
            "indicador_etiqueta": etiqueta,
            "indicador_valor": float(valor),
            "desviacion_mes_pct": desviacion_mes_pct,
            "alertas_mes": alertas_mes,
            "cobertura_pct": len(meses) / 12 * 100,
        },
        "resumen_mes": registros(resumen_mes),
        "fig_consumo": figura(fig),
    }


# ---------------------------------------------------------------------------
# Simulaciones
# ---------------------------------------------------------------------------

def simulaciones(codigo):
    return {"simulaciones": registros(cargar_simulaciones(codigo))}


def detalle_simulacion(sim_id):
    detalle = cargar_detalle_simulacion(sim_id)
    if detalle.empty:
        return _aviso("Esta simulación no tiene detalle.")
    resumen = detalle.groupby("categoria")["consumo_kwh"].sum().reset_index()
    fig = figuras.fig_barras_categoria(resumen, "consumo_kwh", "Consumo simulado por categoría", "kWh")
    return {"detalle": registros(detalle), "resumen": registros(resumen), "figura": figura(fig)}


def importar_simulacion(codigo, nombre, descripcion, anio, activa, nombre_archivo, contenido):
    edificio = _edificio(codigo)
    if edificio is None:
        raise ValueError("Elige un edificio.")
    if not contenido:
        raise ValueError("Sube un archivo .dat.")

    df, ignoradas, errores = transformar_dat_designbuilder(_Archivo(contenido, nombre_archivo), int(anio))
    if errores:
        raise ValueError(" · ".join(errores))

    sim_id = crear_simulacion(codigo, nombre or "Simulación DesignBuilder", descripcion or "", bool(activa))
    guardar_detalle_simulacion(sim_id, df)

    carpeta = crear_carpetas_edificio(codigo, edificio["nombre"])
    with open(os.path.join(carpeta, "simulaciones", f"simulacion_{sim_id}.dat"), "wb") as f:
        f.write(contenido)

    return {
        "sim_id": sim_id,
        "filas": len(df),
        "ignoradas": ignoradas,
        "vista_previa": registros(df.head(MAX_FILAS_VISTA_PREVIA)),
    }


def activar_simulacion(codigo, sim_id):
    marcar_simulacion_activa(int(sim_id), codigo)
    return {"sim_id": int(sim_id)}


# ---------------------------------------------------------------------------
# BMS
# ---------------------------------------------------------------------------

def bms(codigo):
    return {"bms": registros(cargar_consumos_bms(codigo))}


def detalle_bms(bms_id):
    detalle = cargar_detalle_bms(bms_id)
    if detalle.empty:
        return _aviso("Esta importación no tiene detalle.")
    return {"detalle": registros(detalle)}


def importar_bms(codigo, anio, entradas):
    """`entradas`: lista de dicts con mes, nombre, descripcion, archivo y contenido (bytes)."""
    edificio = _edificio(codigo)
    if edificio is None:
        raise ValueError("Elige un edificio.")
    if not entradas:
        raise ValueError("Sube al menos un CSV.")

    resultados = []
    for entrada in entradas:
        archivo = entrada.get("archivo", "archivo.csv")
        mes = int(entrada["mes"])
        if mes not in MESES:
            raise ValueError(f"Mes no válido: {mes}")

        df, errores = transformar_csv_bms(_Archivo(entrada["contenido"], archivo))
        if errores:
            resultados.append({"archivo": archivo, "ok": False, "errores": errores})
            continue

        nombre = entrada.get("nombre") or f"BMS {anio}-{mes:02d} - {archivo}"
        bms_id = crear_consumo_bms(codigo, anio, mes, nombre, entrada.get("descripcion", ""))
        guardar_detalle_bms(bms_id, df)

        carpeta = crear_carpetas_edificio(codigo, edificio["nombre"])
        ruta = os.path.join(carpeta, "consumos_bms", f"bms_{anio}_{mes:02d}_{bms_id}_{os.path.basename(archivo)}")
        with open(ruta, "wb") as f:
            f.write(entrada["contenido"])

        resultados.append({"archivo": archivo, "ok": True, "bms_id": bms_id, "mes": mes, "filas": len(df)})

    return {"resultados": resultados, "importados": sum(1 for r in resultados if r["ok"])}


# ---------------------------------------------------------------------------
# Comparativa
# ---------------------------------------------------------------------------

def _desviacion_total(simulado, real):
    desv = real - simulado
    return desv, 0.0 if simulado == 0 else desv / simulado * 100


def comparativa_mes(codigo, anio, mes):
    edificio = _edificio(codigo)
    if edificio is None:
        return _aviso("No hay edificios activos.")
    sim_id, sim_nombre = _sim_activa(codigo)
    if sim_id is None:
        return _aviso("No hay simulación activa.")
    comp = comparativa_mensual(codigo, sim_id, anio, mes)
    if comp.empty:
        return _aviso("No hay BMS cargado para este mes.")

    total_sim = float(comp["simulado_kwh"].sum())
    total_real = float(comp["real_kwh"].sum())
    desv, pct = _desviacion_total(total_sim, total_real)
    etiqueta, valor, _ = indicador_especifico(total_real, edificio)

    return {
        "simulacion": sim_nombre,
        "kpis": {
            "simulado_kwh": total_sim,
            "real_kwh": total_real,
            "desviacion_kwh": desv,
            "desviacion_pct": pct,
            "indicador_etiqueta": etiqueta,
            "indicador_valor": float(valor),
        },
        "tabla": registros(comp),
        "fig_barras": figura(figuras.fig_barras_comparativa(comp, "Simulado frente a real por categoría")),
        "fig_desviacion": figura(figuras.fig_desviacion(comp, "Desviación por categoría")),
        "fig_pareto": figura(figuras.fig_pareto_desviaciones(comp, "Qué categorías explican la desviación")),
    }


def comparativa_acumulada(codigo, anio):
    edificio = _edificio(codigo)
    if edificio is None:
        return _aviso("No hay edificios activos.")
    sim_id, sim_nombre = _sim_activa(codigo)
    if sim_id is None:
        return _aviso("No hay simulación activa.")
    df_meses, df_cat = comparativa_parcial_anual(codigo, sim_id, anio)
    if df_meses.empty:
        return _aviso("No hay BMS cargado para este año.")

    meses_cargados = len(df_meses)
    total_sim = float(df_meses["simulado_kwh"].sum())
    total_real = float(df_meses["real_kwh"].sum())
    desv, pct = _desviacion_total(total_sim, total_real)
    etiqueta, valor, _ = indicador_especifico(total_real, edificio)

    return {
        "simulacion": sim_nombre,
        "kpis": {
            "meses_bms": meses_cargados,
            "cobertura_pct": meses_cargados / 12 * 100,
            "desviacion_kwh": desv,
            "desviacion_pct": pct,
            "proyeccion_anual_kwh": total_real / meses_cargados * 12,
            "indicador_etiqueta": etiqueta,
            "indicador_valor": float(valor),
        },
        "tabla_meses": registros(df_meses),
        "tabla_categorias": registros(df_cat),
        "fig_evolucion": figura(figuras.fig_evolucion_mensual(df_meses, "Evolución mensual: simulado, real y desviación")),
        "fig_barras": figura(figuras.fig_barras_comparativa(df_cat, "Acumulado por categoría")),
        "fig_desviacion": figura(figuras.fig_desviacion(df_cat, "Desviación acumulada por categoría")),
    }


def base_comparable(anio, categorias=None):
    filas = []
    for _, edif in cargar_edificios(True).iterrows():
        df_edif = consumos_bms_anio(edif["codigo_proyecto"], anio)
        total = 0.0 if df_edif.empty else float(df_edif["consumo_kwh"].sum())
        etiqueta, indicador, _ = indicador_especifico(total, edif)
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
    if df_base.empty or (df_base["consumo_kwh"] > 0).sum() == 0:
        return _aviso("Todavía no hay consumos anuales suficientes para comparar edificios.")
    df_base = df_base[df_base["consumo_kwh"] > 0].copy()

    todas = sorted(df_base["categoria_edificio"].dropna().unique().tolist())
    seleccion = [c for c in (categorias or todas) if c in todas] or todas
    df_filtrado = df_base[df_base["categoria_edificio"].isin(seleccion)]

    fig = figuras.fig_ranking_indicadores(df_filtrado, "Ranking de consumo específico para edificios comparables")
    tabla = df_filtrado.sort_values(["categoria_edificio", "indicador_especifico"])
    return {
        "categorias": todas,
        "seleccion": seleccion,
        "tabla": registros(tabla),
        "figura": figura(fig),
    }


# ---------------------------------------------------------------------------
# Datos mensuales, mapa de alertas y constructor de gráficos
# ---------------------------------------------------------------------------

def _tabla_mensual(codigo, anio):
    """Simulado y real por mes y categoría (todos los meses con simulación).

    `real_kwh` es None en los meses sin BMS. Devuelve (DataFrame, nombre_simulacion) o
    (None, mensaje) si falta algo.
    """
    sim_id, sim_nombre = _sim_activa(codigo)
    if sim_id is None:
        return None, "No hay simulación activa."

    sim = cargar_detalle_simulacion(sim_id)
    sim = sim[sim["anio"] == int(anio)][["mes", "categoria", "consumo_kwh"]].rename(columns={"consumo_kwh": "simulado_kwh"})
    bms_anio = consumos_bms_anio(codigo, anio)
    if bms_anio.empty:
        return None, "No hay BMS cargado para este año."

    real = bms_anio.rename(columns={"consumo_kwh": "real_kwh"})
    tabla = pd.merge(sim, real, on=["mes", "categoria"], how="outer")
    tabla["simulado_kwh"] = tabla["simulado_kwh"].fillna(0.0)

    # En un mes con BMS, una categoría que el BMS no trae consume 0; en un mes sin BMS no hay dato.
    con_bms = tabla["mes"].isin(set(real["mes"].unique()))
    faltan = con_bms & tabla["real_kwh"].isna()
    tabla.loc[faltan, ["real_kwh", "electricidad_kwh", "gas_kwh"]] = 0.0
    return tabla.sort_values(["categoria", "mes"]).reset_index(drop=True), sim_nombre


def _nivel(simulado, real):
    """Gravedad de una desviación: ok (≤10 %), atencion (≤20 %), revisar (>20 %) o sin_dato.

    Consumo real sin nada simulado se marca "revisar": comparar un % contra 0 no tiene sentido.
    """
    if simulado == 0 and real == 0:
        return "sin_dato"
    if simulado == 0:
        return "revisar"
    pct = abs((real - simulado) / simulado * 100)
    return "ok" if pct <= 10 else "atencion" if pct <= 20 else "revisar"


def _celda(simulado, real, electricidad=0.0, gas=0.0):
    simulado, real = float(simulado), float(real)
    desv = real - simulado
    return {
        "simulado_kwh": simulado,
        "real_kwh": real,
        "electricidad_kwh": float(electricidad),
        "gas_kwh": float(gas),
        "desviacion_kwh": desv,
        "desviacion_pct": None if simulado == 0 else desv / simulado * 100,
        "nivel": _nivel(simulado, real),
    }


def datos_mensuales(codigo, anio):
    """Datos en bruto (mes × categoría) para el constructor de gráficos."""
    if _edificio(codigo) is None:
        return _aviso("No hay edificios activos.")
    tabla, resto = _tabla_mensual(codigo, anio)
    if tabla is None:
        return _aviso(resto)
    return {
        "simulacion": resto,
        "filas": registros(tabla),
        "categorias": sorted(tabla["categoria"].unique().tolist()),
        "meses_con_bms": sorted(int(m) for m in tabla.loc[tabla["real_kwh"].notna(), "mes"].unique()),
    }


def alertas(codigo, anio):
    """Mapa de calor de desviaciones: categorías × meses, con acumulados por fila y por columna."""
    if _edificio(codigo) is None:
        return _aviso("No hay edificios activos.")
    tabla, resto = _tabla_mensual(codigo, anio)
    if tabla is None:
        return _aviso(resto)

    con_datos = tabla[tabla["real_kwh"].notna()].copy()
    meses_bms = sorted(int(m) for m in con_datos["mes"].unique())

    celdas = []
    for _, r in con_datos.iterrows():
        if r["simulado_kwh"] == 0 and r["real_kwh"] == 0:
            continue
        celda = _celda(r["simulado_kwh"], r["real_kwh"], r["electricidad_kwh"], r["gas_kwh"])
        celda.update({"categoria": r["categoria"], "mes": int(r["mes"])})
        celdas.append(celda)

    def acumular(df):
        return _celda(df["simulado_kwh"].sum(), df["real_kwh"].sum(), df["electricidad_kwh"].sum(), df["gas_kwh"].sum())

    por_categoria = []
    for categoria, df in con_datos.groupby("categoria"):
        if df["simulado_kwh"].sum() == 0 and df["real_kwh"].sum() == 0:
            continue
        acumulado = acumular(df)
        acumulado["categoria"] = categoria
        por_categoria.append(acumulado)
    por_categoria.sort(key=lambda c: max(c["simulado_kwh"], c["real_kwh"]), reverse=True)

    por_mes = []
    for mes, df in con_datos.groupby("mes"):
        total = acumular(df)
        total["mes"] = int(mes)
        por_mes.append(total)

    return {
        "simulacion": resto,
        "meses": [{"mes": m, "con_bms": m in meses_bms} for m in range(1, 13)],
        "categorias": por_categoria,
        "celdas": celdas,
        "totales_mes": por_mes,
        "total": acumular(con_datos),
    }


# ---------------------------------------------------------------------------
# Informe mensual
# ---------------------------------------------------------------------------

def _texto_informe(edificio, codigo, anio, mes, kpis, alertas, observaciones):
    if alertas.empty:
        alertas_txt = "No se detectan alertas relevantes."
    else:
        alertas_txt = "\n".join(
            f"{r['estado']} {r['categoria']}: {r['desviacion_pct']:.2f}%"
            for _, r in alertas.iterrows()
        )

    return f"""
INFORME MENSUAL ENERGÉTICO

Proyecto: {edificio['nombre']}
Código: {edificio['codigo_proyecto']}
Cliente: {edificio['cliente']}
Ubicación: {edificio['ubicacion']}
Periodo analizado: {mes}/{anio}

RESUMEN EJECUTIVO

Consumo simulado: {kpis['simulado_kwh']:,.0f} kWh
Consumo real BMS: {kpis['real_kwh']:,.0f} kWh
Desviación: {kpis['desviacion_kwh']:,.0f} kWh
Desviación porcentual: {kpis['desviacion_pct']:.2f} %
Indicador específico mensual: {kpis['indicador_valor']:.2f} {kpis['indicador_etiqueta']} mes

ALERTAS DETECTADAS

{alertas_txt}

OBSERVACIONES TÉCNICAS

{observaciones}
"""


def informe(codigo, anio, mes):
    edificio = _edificio(codigo)
    if edificio is None:
        return _aviso("No hay edificios activos.")
    sim_id, _ = _sim_activa(codigo)
    if sim_id is None:
        return _aviso("No hay simulación activa.")
    comp = comparativa_mensual(codigo, sim_id, anio, mes)
    if comp.empty:
        return _aviso("No hay BMS cargado para este mes.")

    total_sim = float(comp["simulado_kwh"].sum())
    total_real = float(comp["real_kwh"].sum())
    desv, pct = _desviacion_total(total_sim, total_real)
    etiqueta, valor, _ = indicador_especifico(total_real, edificio)
    kpis = {
        "simulado_kwh": total_sim,
        "real_kwh": total_real,
        "desviacion_kwh": desv,
        "desviacion_pct": pct,
        "indicador_etiqueta": etiqueta,
        "indicador_valor": float(valor),
    }

    alertas = comp[comp["desviacion_pct"].abs() > 10].copy()
    observaciones = generar_observaciones(comp)
    return {
        "kpis": kpis,
        "alertas": registros(alertas[["categoria", "simulado_kwh", "real_kwh", "desviacion_pct", "estado"]]),
        "tabla": registros(comp),
        "observaciones": observaciones,
        "texto": _texto_informe(edificio, codigo, anio, mes, kpis, alertas, observaciones),
        "archivo": f"informe_{codigo}_{anio}_{int(mes):02d}.txt",
    }


# ---------------------------------------------------------------------------
# Costes y emisiones
# ---------------------------------------------------------------------------

def _resumenes(df, columnas_mes, columnas_cat, orden_cat):
    resumen_mes = df.groupby("mes").agg(columnas_mes).reset_index()
    resumen_cat = df.groupby("categoria").agg(columnas_cat).reset_index().sort_values(orden_cat, ascending=False)
    return resumen_mes, resumen_cat


def costes(codigo, anio, precio_elec, precio_gas):
    edificio = _edificio(codigo)
    if edificio is None:
        return _aviso("No hay edificios activos.")
    df = consumos_bms_anio(codigo, anio)
    if df.empty:
        return _aviso("No hay BMS cargado para este año.")

    df = df.copy()
    df["coste_electricidad_eur"] = df["electricidad_kwh"] * float(precio_elec)
    df["coste_gas_eur"] = df["gas_kwh"] * float(precio_gas)
    df["coste_total_eur"] = df["coste_electricidad_eur"] + df["coste_gas_eur"]

    resumen_mes, resumen_cat = _resumenes(
        df,
        {
            "electricidad_kwh": "sum", "gas_kwh": "sum", "consumo_kwh": "sum",
            "coste_electricidad_eur": "sum", "coste_gas_eur": "sum", "coste_total_eur": "sum",
        },
        {"electricidad_kwh": "sum", "gas_kwh": "sum", "consumo_kwh": "sum", "coste_total_eur": "sum"},
        "coste_total_eur",
    )

    meses_cargados = int(resumen_mes["mes"].nunique())
    coste_total = float(resumen_mes["coste_total_eur"].sum())
    superficie = _superficie(edificio)

    return {
        "kpis": {
            "meses_bms": meses_cargados,
            "coste_total_eur": coste_total,
            "coste_m2": 0.0 if superficie == 0 else coste_total / superficie,
            "proyeccion_anual_eur": 0.0 if meses_cargados == 0 else coste_total / meses_cargados * 12,
        },
        "tabla_mes": registros(resumen_mes),
        "tabla_categoria": registros(resumen_cat),
        "fig_mes": figura(figuras.fig_apilada_mensual(
            resumen_mes,
            [("coste_electricidad_eur", "Electricidad", COLOR_CORPORATIVO), ("coste_gas_eur", "Gas natural", COLOR_GAS)],
            "Coste mensual", "€",
        )),
        "fig_categoria": figura(figuras.fig_barras_categoria(resumen_cat, "coste_total_eur", "Coste por categoría", "€")),
    }


def co2(codigo, anio, factor_elec, factor_gas):
    edificio = _edificio(codigo)
    if edificio is None:
        return _aviso("No hay edificios activos.")
    df = consumos_bms_anio(codigo, anio)
    if df.empty:
        return _aviso("No hay BMS cargado para este año.")

    df = df.copy()
    df["co2_electricidad_kg"] = df["electricidad_kwh"] * float(factor_elec)
    df["co2_gas_kg"] = df["gas_kwh"] * float(factor_gas)
    df["co2_total_kg"] = df["co2_electricidad_kg"] + df["co2_gas_kg"]

    resumen_mes, resumen_cat = _resumenes(
        df,
        {
            "electricidad_kwh": "sum", "gas_kwh": "sum", "co2_electricidad_kg": "sum",
            "co2_gas_kg": "sum", "co2_total_kg": "sum",
        },
        {"co2_total_kg": "sum", "electricidad_kwh": "sum", "gas_kwh": "sum"},
        "co2_total_kg",
    )

    meses_cargados = int(resumen_mes["mes"].nunique())
    co2_kg = float(resumen_mes["co2_total_kg"].sum())
    co2_tn = co2_kg / 1000
    superficie = _superficie(edificio)

    return {
        "kpis": {
            "meses_bms": meses_cargados,
            "co2_acumulado_tn": co2_tn,
            "co2_m2_kg": 0.0 if superficie == 0 else co2_kg / superficie,
            "proyeccion_anual_tn": 0.0 if meses_cargados == 0 else co2_tn / meses_cargados * 12,
        },
        "tabla_mes": registros(resumen_mes),
        "tabla_categoria": registros(resumen_cat),
        "fig_mes": figura(figuras.fig_apilada_mensual(
            resumen_mes,
            [("co2_electricidad_kg", "Electricidad", COLOR_CORPORATIVO), ("co2_gas_kg", "Gas natural", COLOR_GAS)],
            "CO₂ mensual", "kgCO₂",
        )),
        "fig_categoria": figura(figuras.fig_barras_categoria(resumen_cat, "co2_total_kg", "CO₂ por categoría", "kgCO₂")),
    }
