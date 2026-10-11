"""Copia los datos de una base SQLite local (database.db) a PostgreSQL.

Uso:  python -m energia.migrar [ruta/a/database.db]

Pide la URL de PostgreSQL (o la toma de la variable DATABASE_URL). No modifica el archivo
original y se niega a copiar si la base de destino ya tiene datos.
"""
import getpass
import os
import sqlite3
import sys

from energia import config
from energia.db import conectar_db, es_postgres, inicializar_db

# Orden de copia: primero las tablas de las que dependen las demás.
TABLAS = ["edificios", "simulaciones", "simulacion_detalle", "consumos_bms", "consumo_bms_detalle"]
TABLAS_CON_ID = ["simulaciones", "simulacion_detalle", "consumos_bms", "consumo_bms_detalle"]


def migrar(origen):
    """Copia todas las tablas de la base SQLite `origen` a la base PostgreSQL configurada
    (DATABASE_URL). Devuelve las filas copiadas por tabla."""
    if not es_postgres():
        raise ValueError("Falta DATABASE_URL: no hay base de datos PostgreSQL de destino.")
    if not os.path.isfile(origen):
        raise FileNotFoundError(f"No existe el archivo de origen: {origen}")

    inicializar_db()

    destino = conectar_db()
    try:
        c = destino.cursor()

        for tabla in TABLAS:
            c.execute(f"SELECT COUNT(*) FROM {tabla}")
            if c.fetchone()[0] > 0:
                raise ValueError(
                    f"La base de destino ya tiene datos en '{tabla}'. "
                    "Para no duplicar nada, la migración solo se hace sobre una base vacía."
                )

        origen_conn = sqlite3.connect(origen)
        copiadas = {}
        try:
            for tabla in TABLAS:
                columnas_origen = [f[1] for f in origen_conn.execute(f"PRAGMA table_info({tabla})")]
                if not columnas_origen:
                    copiadas[tabla] = 0  # tabla inexistente en una base antigua
                    continue

                c.execute(f"SELECT * FROM {tabla} LIMIT 0")
                columnas_destino = {d[0] for d in c.description}
                columnas = [col for col in columnas_origen if col in columnas_destino]

                filas = origen_conn.execute(f"SELECT {', '.join(columnas)} FROM {tabla}").fetchall()
                if filas:
                    marcadores = ", ".join("?" for _ in columnas)
                    c.executemany(
                        f"INSERT INTO {tabla} ({', '.join(columnas)}) VALUES ({marcadores})",
                        filas,
                    )
                copiadas[tabla] = len(filas)
        finally:
            origen_conn.close()

        # Los identificadores se copian tal cual; el contador de PostgreSQL debe seguir a partir del último.
        for tabla in TABLAS_CON_ID:
            c.execute(
                f"SELECT setval(pg_get_serial_sequence('{tabla}', 'id'), "
                f"COALESCE(MAX(id), 1), MAX(id) IS NOT NULL) FROM {tabla}"
            )

        destino.commit()
    except Exception:
        destino.rollback()
        raise
    finally:
        destino.close()

    return copiadas


def main(argumentos):
    origen = argumentos[0] if argumentos else config.DB

    if not config.url_postgres():
        url = getpass.getpass("Pega la URL de la base de datos PostgreSQL (no se verá al escribir): ").strip()
        if not url:
            print("No se ha indicado ninguna URL. No se ha copiado nada.")
            return 1
        os.environ["DATABASE_URL"] = url

    try:
        copiadas = migrar(origen)
    except (ValueError, FileNotFoundError) as error:
        print(f"No se ha copiado nada. {error}")
        return 1

    print(f"Datos copiados desde {origen}:")
    for tabla, filas in copiadas.items():
        print(f"  {tabla}: {filas} filas")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
