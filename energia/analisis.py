"""Comparativas simulado vs real, alertas e indicadores especificos."""

import pandas as pd

from energia.db import cargar_ultimo_bms_mes, conectar_db, meses_bms


def comparativa_mensual(codigo, sim_id, anio, mes):
    conn = conectar_db()

    sim = pd.read_sql_query("""
        SELECT categoria, consumo_kwh AS simulado_kwh
        FROM simulacion_detalle
        WHERE simulacion_id = ?
        AND anio = ?
        AND mes = ?
    """, conn, params=(int(sim_id), int(anio), int(mes)))

    conn.close()

    bms = cargar_ultimo_bms_mes(codigo, anio, mes)

    if bms.empty:
        return pd.DataFrame()

    bms_simple = bms[["categoria", "real_kwh"]].copy()

    comp = pd.merge(sim, bms_simple, on="categoria", how="outer").fillna(0)
    comp["desviacion_kwh"] = comp["real_kwh"] - comp["simulado_kwh"]
    comp["desviacion_pct"] = comp.apply(
        lambda r: 0 if r["simulado_kwh"] == 0 else round(r["desviacion_kwh"] / r["simulado_kwh"] * 100, 2),
        axis=1
    )
    comp["estado"] = comp["desviacion_pct"].apply(clasificar_alerta)

    return comp.sort_values("desviacion_kwh", ascending=False)


def comparativa_parcial_anual(codigo, sim_id, anio):
    meses = meses_bms(codigo, anio)

    if meses.empty:
        return pd.DataFrame(), pd.DataFrame()

    conn = conectar_db()
    datos_meses = []

    for _, row in meses.iterrows():
        mes = int(row["mes"])
        bms_id = int(row["bms_id"])

        sim = pd.read_sql_query("""
            SELECT SUM(consumo_kwh) AS total
            FROM simulacion_detalle
            WHERE simulacion_id = ?
            AND anio = ?
            AND mes = ?
        """, conn, params=(int(sim_id), int(anio), mes))

        total_sim = sim.iloc[0]["total"]
        total_sim = 0 if pd.isna(total_sim) else total_sim

        bms = pd.read_sql_query("""
            SELECT SUM(consumo_kwh) AS total
            FROM consumo_bms_detalle
            WHERE consumo_bms_id = ?
        """, conn, params=(bms_id,))

        total_real = bms.iloc[0]["total"]
        total_real = 0 if pd.isna(total_real) else total_real

        desviacion = total_real - total_sim
        desviacion_pct = 0 if total_sim == 0 else round(desviacion / total_sim * 100, 2)

        datos_meses.append({
            "mes": mes,
            "simulado_kwh": round(total_sim, 2),
            "real_kwh": round(total_real, 2),
            "desviacion_kwh": round(desviacion, 2),
            "desviacion_pct": desviacion_pct
        })

    df_meses = pd.DataFrame(datos_meses)

    meses_texto = ",".join(str(int(m)) for m in meses["mes"].tolist())
    ids_texto = ",".join(str(int(i)) for i in meses["bms_id"].tolist())

    sim_cat = pd.read_sql_query(f"""
        SELECT categoria, SUM(consumo_kwh) AS simulado_kwh
        FROM simulacion_detalle
        WHERE simulacion_id = ?
        AND anio = ?
        AND mes IN ({meses_texto})
        GROUP BY categoria
    """, conn, params=(int(sim_id), int(anio)))

    bms_cat = pd.read_sql_query(f"""
        SELECT categoria, SUM(consumo_kwh) AS real_kwh
        FROM consumo_bms_detalle
        WHERE consumo_bms_id IN ({ids_texto})
        GROUP BY categoria
    """, conn)

    conn.close()

    comp_cat = pd.merge(sim_cat, bms_cat, on="categoria", how="outer").fillna(0)
    comp_cat["desviacion_kwh"] = comp_cat["real_kwh"] - comp_cat["simulado_kwh"]
    comp_cat["desviacion_pct"] = comp_cat.apply(
        lambda r: 0 if r["simulado_kwh"] == 0 else round(r["desviacion_kwh"] / r["simulado_kwh"] * 100, 2),
        axis=1
    )

    return df_meses, comp_cat.sort_values("desviacion_kwh", ascending=False)


def clasificar_alerta(desviacion_pct):
    valor = abs(desviacion_pct)
    if valor <= 10:
        return "🟢 Correcto"
    elif valor <= 20:
        return "🟡 Atención"
    else:
        return "🔴 Revisar"


def generar_observaciones(comp):
    observaciones = []

    altas = comp[comp["desviacion_pct"] > 15]
    bajas = comp[comp["desviacion_pct"] < -15]

    for _, fila in altas.iterrows():
        observaciones.append(
            f"- {fila['categoria']}: consumo real superior al simulado en {fila['desviacion_pct']}%. "
            "Revisar horarios, consignas, ocupación o funcionamiento del BMS."
        )

    for _, fila in bajas.iterrows():
        observaciones.append(
            f"- {fila['categoria']}: consumo real inferior al simulado en "
            f"{abs(fila['desviacion_pct'])}%. Revisar menor uso, ocupación o condiciones favorables."
        )

    if not observaciones:
        observaciones.append("- No se detectan desviaciones significativas superiores al 15%.")

    return "\n".join(observaciones)


def obtener_valor_referencia(edificio):
    unidad = edificio.get("unidad_referencia", "m²") if hasattr(edificio, "get") else "m²"
    valor = edificio.get("valor_unidad_referencia", 0) if hasattr(edificio, "get") else 0

    if pd.isna(valor) or float(valor) <= 0:
        if unidad == "habitaciones":
            valor = edificio.get("habitaciones", 0) if hasattr(edificio, "get") else 0
        elif unidad == "puestos de trabajo":
            valor = edificio.get("puestos_trabajo", 0) if hasattr(edificio, "get") else 0
        elif unidad == "camas":
            valor = edificio.get("camas", 0) if hasattr(edificio, "get") else 0
        else:
            valor = edificio.get("superficie_m2", 0) if hasattr(edificio, "get") else 0

    try:
        valor = float(valor)
    except Exception:
        valor = 0

    if valor <= 0:
        superficie = edificio.get("superficie_m2", 0) if hasattr(edificio, "get") else 0
        try:
            valor = float(superficie)
            unidad = "m²"
        except Exception:
            valor = 0

    return unidad or "m²", valor


def indicador_especifico(consumo_kwh, edificio):
    unidad, valor = obtener_valor_referencia(edificio)
    if valor <= 0:
        return "Sin dato", 0, unidad
    return f"kWh/{unidad}", consumo_kwh / valor, unidad
