"""Lectores de archivos de entrada: .dat de DesignBuilder y CSV del BMS."""

from io import StringIO

import pandas as pd

from energia.utils import leer_csv_flexible, leer_texto_archivo, limpiar_numero, normalizar


MAPEO_DAT = {
    "Lighting": "Interior Lighting",
    "Interior Lighting": "Interior Lighting",
    "Exterior lighting": "Exterior Lighting",
    "Exterior Lighting": "Exterior Lighting",
    "System Fans": "Fans",
    "Fans": "Fans",
    "System Pumps": "Pumps",
    "Pumps": "Pumps",
    "Heating (Electricity)": "Heating",
    "Heating": "Heating",
    "Cooling (Electricity)": "Cooling",
    "Cooling": "Cooling",
    "Interior Equipment": "Interior Equipment",
    "Exterior Equipment": "Exterior Equipment",
    "Water Systems": "Water Systems",
    "Refrigeration": "Refrigeration",
    "Generators": "Generators",
    "Heat Rejection": "Heat Rejection",
    "Humidification": "Humidification",
    "Heat Recovery": "Heat Recovery",
}


def transformar_dat_designbuilder(archivo, anio):
    texto = leer_texto_archivo(archivo)

    try:
        df = pd.read_csv(
            StringIO(texto),
            sep="\t",
            decimal=",",
            header=0,
            engine="python"
        )
    except Exception as e:
        return None, [], [f"No se pudo leer el .dat: {e}"]

    if df.empty:
        return None, [], ["El archivo .dat está vacío."]

    primera_columna = df.columns[0]
    datos = []
    ignoradas = []

    for _, fila in df.iterrows():
        categoria_original = str(fila[primera_columna]).strip()

        if categoria_original == "" or categoria_original.lower() == "nan":
            continue

        if categoria_original not in MAPEO_DAT:
            ignoradas.append(categoria_original)
            continue

        categoria = MAPEO_DAT[categoria_original]

        for mes in range(1, 13):
            valor = fila.iloc[mes] if mes < len(fila) else 0

            datos.append({
                "anio": int(anio),
                "mes": mes,
                "categoria": categoria,
                "consumo_kwh": limpiar_numero(valor),
            })

    df_final = pd.DataFrame(datos)

    if df_final.empty:
        return None, sorted(set(ignoradas)), ["No se encontraron categorías reconocidas."]

    return df_final, sorted(set(ignoradas)), []


def transformar_csv_bms(archivo):
    df = leer_csv_flexible(archivo)

    df.columns = [
        str(c).replace("\ufeff", "").replace("\xa0", " ").strip()
        for c in df.columns
    ]

    columnas = {normalizar(c): c for c in df.columns}

    col_tipologia = None
    col_elec = None
    col_gas = None

    for k, v in columnas.items():
        if k in ["tipologia", "tipología", "categoria", "category"]:
            col_tipologia = v
        if k in ["electricidad [kwh]", "electricidad", "electricity [kwh]", "electricity"]:
            col_elec = v
        if k in ["gas natural [kwh]", "gas natural", "gas [kwh]", "gas"]:
            col_gas = v

    errores = []

    if col_tipologia is None:
        errores.append(f"No encuentro columna Tipologia. Detectadas: {list(df.columns)}")
    if col_elec is None:
        errores.append(f"No encuentro columna Electricidad [kWh]. Detectadas: {list(df.columns)}")
    if col_gas is None:
        errores.append(f"No encuentro columna Gas Natural [kWh]. Detectadas: {list(df.columns)}")

    if errores:
        return None, errores

    datos = []

    for _, fila in df.iterrows():
        categoria = str(fila[col_tipologia]).strip()

        if categoria == "" or categoria.lower() == "nan":
            continue

        if normalizar(categoria) in ["total mes", "total", "totales"]:
            continue

        electricidad = limpiar_numero(fila[col_elec])
        gas = limpiar_numero(fila[col_gas])

        datos.append({
            "categoria": categoria,
            "electricidad_kwh": electricidad,
            "gas_kwh": gas,
            "consumo_kwh": electricidad + gas,
            "nombre_original_bms": categoria,
        })

    resultado = pd.DataFrame(datos)

    if resultado.empty:
        return None, ["No se encontraron consumos válidos en el CSV BMS."]

    return resultado, []
