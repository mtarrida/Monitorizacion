"""Acceso a datos: edificios, simulaciones y consumos BMS.

Usa SQLite (un archivo local) por defecto, o PostgreSQL si la variable de entorno DATABASE_URL
está definida (despliegue online). Las consultas se escriben con marcadores `?`; con PostgreSQL
se traducen a `%s` en _CursorPG.
"""

import atexit
import re
import sqlite3
import threading

import pandas as pd

from energia import config

_pools = {}
_pools_lock = threading.Lock()
_inicializadas = set()


def es_postgres():
    return bool(config.url_postgres())


class _CursorPG:
    """Cursor de psycopg que acepta marcadores `?` como sqlite3."""

    def __init__(self, cursor):
        self._cursor = cursor

    @staticmethod
    def _traducir(sql):
        return sql.replace("%", "%%").replace("?", "%s")

    def execute(self, sql, params=()):
        self._cursor.execute(self._traducir(sql), params)
        return self

    def executemany(self, sql, secuencia):
        self._cursor.executemany(self._traducir(sql), secuencia)
        return self

    def fetchone(self):
        return self._cursor.fetchone()

    def fetchall(self):
        return self._cursor.fetchall()

    @property
    def rowcount(self):
        return self._cursor.rowcount

    @property
    def description(self):
        return self._cursor.description


class _ConexionPG:
    """Conexión de un grupo (pool) de psycopg que se usa igual que una de sqlite3."""

    def __init__(self, pool, conn):
        self._pool = pool
        self._conn = conn

    def cursor(self):
        return _CursorPG(self._conn.cursor())

    def commit(self):
        self._conn.commit()

    def rollback(self):
        self._conn.rollback()

    def close(self):
        # Como en sqlite3, lo no confirmado se descarta; después la conexión vuelve al grupo.
        self._conn.rollback()
        self._pool.putconn(self._conn)


def _pool_pg(url):
    with _pools_lock:
        pool = _pools.get(url)
        if pool is None:
            # Se importa aquí para que quien use solo SQLite no necesite instalar psycopg.
            from psycopg_pool import ConnectionPool

            pool = ConnectionPool(
                url,
                min_size=1,
                max_size=5,
                open=False,
                kwargs={"prepare_threshold": None},  # compatible con el pooler de Supabase
                check=ConnectionPool.check_connection,
            )
            pool.open(wait=True, timeout=30)
            _pools[url] = pool
        return pool


@atexit.register
def cerrar_pools():
    for pool in _pools.values():
        pool.close()
    _pools.clear()


def conectar_db():
    url = config.url_postgres()
    if url:
        pool = _pool_pg(url)
        return _ConexionPG(pool, pool.getconn())
    return sqlite3.connect(config.DB)


def leer_sql(sql, conn, params=None):
    """Como pd.read_sql_query, pero válido para SQLite y PostgreSQL."""
    if isinstance(conn, sqlite3.Connection):
        return pd.read_sql_query(sql, conn, params=params)

    cursor = conn.cursor()
    cursor.execute(sql, params or ())
    columnas = [d[0] for d in cursor.description]
    return pd.DataFrame.from_records(cursor.fetchall(), columns=columnas, coerce_float=True)


def _ddl(sql):
    """Adapta el SQL de creación de tablas a PostgreSQL."""
    if not es_postgres():
        return sql
    sql = sql.replace("INTEGER PRIMARY KEY AUTOINCREMENT", "SERIAL PRIMARY KEY")
    return re.sub(r"\bREAL\b", "DOUBLE PRECISION", sql)


def _agregar_columna(c, tabla, columna, definicion):
    if es_postgres():
        c.execute(_ddl(f"ALTER TABLE {tabla} ADD COLUMN IF NOT EXISTS {columna} {definicion}"))
        return

    try:
        c.execute(f"ALTER TABLE {tabla} ADD COLUMN {columna} {definicion}")
    except sqlite3.OperationalError:
        pass


def _insertar_y_obtener_id(c, sql, params):
    if es_postgres():
        c.execute(sql + " RETURNING id", params)
        return c.fetchone()[0]

    c.execute(sql, params)
    return c.lastrowid


def inicializar_db():
    url = config.url_postgres()
    if url and url in _inicializadas:
        return  # en PostgreSQL basta con crear las tablas una vez por proceso

    conn = conectar_db()
    c = conn.cursor()

    c.execute(_ddl("""
    CREATE TABLE IF NOT EXISTS edificios (
        codigo_proyecto TEXT PRIMARY KEY,
        nombre TEXT NOT NULL,
        cliente TEXT,
        ubicacion TEXT,
        uso TEXT,
        superficie_m2 REAL,
        sistema_climatizacion TEXT,
        estado TEXT DEFAULT 'ACTIVO',
        observaciones TEXT,
        fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """))

    c.execute(_ddl("""
    CREATE TABLE IF NOT EXISTS simulaciones (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        codigo_proyecto TEXT NOT NULL,
        nombre_simulacion TEXT NOT NULL,
        descripcion TEXT,
        activa INTEGER DEFAULT 0,
        fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """))

    c.execute(_ddl("""
    CREATE TABLE IF NOT EXISTS simulacion_detalle (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        simulacion_id INTEGER NOT NULL,
        anio INTEGER NOT NULL,
        mes INTEGER NOT NULL,
        categoria TEXT NOT NULL,
        consumo_kwh REAL NOT NULL
    )
    """))

    c.execute(_ddl("""
    CREATE TABLE IF NOT EXISTS consumos_bms (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        codigo_proyecto TEXT NOT NULL,
        anio INTEGER NOT NULL,
        mes INTEGER NOT NULL,
        nombre_importacion TEXT NOT NULL,
        descripcion TEXT,
        fecha_importacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """))

    c.execute(_ddl("""
    CREATE TABLE IF NOT EXISTS consumo_bms_detalle (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        consumo_bms_id INTEGER NOT NULL,
        categoria TEXT NOT NULL,
        consumo_kwh REAL NOT NULL,
        nombre_original_bms TEXT
    )
    """))

    for columna in ["electricidad_kwh", "gas_kwh"]:
        _agregar_columna(c, "consumo_bms_detalle", columna, "REAL DEFAULT 0")

    nuevas_columnas_edificios = {
        "categoria_edificio": "TEXT",
        "unidad_referencia": "TEXT DEFAULT 'm²'",
        "valor_unidad_referencia": "REAL DEFAULT 0",
        "habitaciones": "REAL DEFAULT 0",
        "puestos_trabajo": "REAL DEFAULT 0",
        "camas": "REAL DEFAULT 0",
        "horario_uso": "TEXT",
        # Cómo reconocer el correo que trae los CSV del BMS de este edificio
        "correo_asunto": "TEXT",
        "correo_remitente": "TEXT",
    }

    for columna, definicion in nuevas_columnas_edificios.items():
        _agregar_columna(c, "edificios", columna, definicion)

    conn.commit()
    conn.close()

    if url:
        _inicializadas.add(url)


def cargar_edificios(incluir_archivados=False):
    conn = conectar_db()
    query = "SELECT * FROM edificios ORDER BY nombre"

    if not incluir_archivados:
        query = "SELECT * FROM edificios WHERE estado='ACTIVO' ORDER BY nombre"

    df = leer_sql(query, conn)
    conn.close()
    return df


def guardar_edificio(datos):
    conn = conectar_db()
    c = conn.cursor()

    c.execute("""
        INSERT INTO edificios (
            codigo_proyecto, nombre, cliente, ubicacion, uso,
            superficie_m2, categoria_edificio, unidad_referencia,
            valor_unidad_referencia, habitaciones, puestos_trabajo, camas,
            horario_uso, sistema_climatizacion, estado, observaciones
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'ACTIVO', ?)
    """, (
        datos["codigo_proyecto"],
        datos["nombre"],
        datos["cliente"],
        datos["ubicacion"],
        datos["uso"],
        datos["superficie_m2"],
        datos.get("categoria_edificio", datos.get("uso", "")),
        datos.get("unidad_referencia", "m²"),
        datos.get("valor_unidad_referencia", 0),
        datos.get("habitaciones", 0),
        datos.get("puestos_trabajo", 0),
        datos.get("camas", 0),
        datos.get("horario_uso", ""),
        datos["sistema_climatizacion"],
        datos["observaciones"],
    ))

    conn.commit()
    conn.close()


def actualizar_edificio(codigo, datos):
    conn = conectar_db()
    c = conn.cursor()

    c.execute("""
        UPDATE edificios
        SET nombre=?, cliente=?, ubicacion=?, uso=?, superficie_m2=?,
            categoria_edificio=?, unidad_referencia=?, valor_unidad_referencia=?,
            habitaciones=?, puestos_trabajo=?, camas=?, horario_uso=?,
            sistema_climatizacion=?, observaciones=?
        WHERE codigo_proyecto=?
    """, (
        datos["nombre"],
        datos["cliente"],
        datos["ubicacion"],
        datos["uso"],
        datos["superficie_m2"],
        datos.get("categoria_edificio", datos.get("uso", "")),
        datos.get("unidad_referencia", "m²"),
        datos.get("valor_unidad_referencia", 0),
        datos.get("habitaciones", 0),
        datos.get("puestos_trabajo", 0),
        datos.get("camas", 0),
        datos.get("horario_uso", ""),
        datos["sistema_climatizacion"],
        datos["observaciones"],
        codigo,
    ))

    conn.commit()
    conn.close()


def guardar_correo_edificio(codigo, asunto, remitente):
    """Palabras clave con las que se reconoce el correo de este edificio (asunto y remitente)."""
    conn = conectar_db()
    c = conn.cursor()
    c.execute(
        "UPDATE edificios SET correo_asunto=?, correo_remitente=? WHERE codigo_proyecto=?",
        (asunto, remitente, codigo),
    )
    conn.commit()
    conn.close()


def cambiar_estado_edificio(codigo, estado):
    conn = conectar_db()
    c = conn.cursor()
    c.execute("UPDATE edificios SET estado=? WHERE codigo_proyecto=?", (estado, codigo))
    conn.commit()
    conn.close()


def resumen_datos_edificio(codigo):
    conn = conectar_db()
    c = conn.cursor()

    c.execute("SELECT COUNT(*) FROM simulaciones WHERE codigo_proyecto=?", (codigo,))
    simulaciones = c.fetchone()[0]

    c.execute("""
        SELECT COUNT(*)
        FROM simulacion_detalle
        WHERE simulacion_id IN (
            SELECT id FROM simulaciones WHERE codigo_proyecto=?
        )
    """, (codigo,))
    detalle_simulaciones = c.fetchone()[0]

    c.execute("SELECT COUNT(*) FROM consumos_bms WHERE codigo_proyecto=?", (codigo,))
    consumos_bms = c.fetchone()[0]

    c.execute("""
        SELECT COUNT(*)
        FROM consumo_bms_detalle
        WHERE consumo_bms_id IN (
            SELECT id FROM consumos_bms WHERE codigo_proyecto=?
        )
    """, (codigo,))
    detalle_bms = c.fetchone()[0]

    conn.close()

    return {
        "simulaciones": simulaciones,
        "detalle_simulaciones": detalle_simulaciones,
        "consumos_bms": consumos_bms,
        "detalle_bms": detalle_bms,
    }


def eliminar_edificio(codigo):
    conn = conectar_db()
    c = conn.cursor()

    try:
        c.execute("""
            DELETE FROM simulacion_detalle
            WHERE simulacion_id IN (
                SELECT id FROM simulaciones WHERE codigo_proyecto=?
            )
        """, (codigo,))
        detalle_simulaciones = c.rowcount

        c.execute("""
            DELETE FROM consumo_bms_detalle
            WHERE consumo_bms_id IN (
                SELECT id FROM consumos_bms WHERE codigo_proyecto=?
            )
        """, (codigo,))
        detalle_bms = c.rowcount

        c.execute("DELETE FROM simulaciones WHERE codigo_proyecto=?", (codigo,))
        simulaciones = c.rowcount

        c.execute("DELETE FROM consumos_bms WHERE codigo_proyecto=?", (codigo,))
        consumos_bms = c.rowcount

        c.execute("DELETE FROM edificios WHERE codigo_proyecto=?", (codigo,))
        edificios = c.rowcount

        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

    return {
        "edificios": edificios,
        "simulaciones": simulaciones,
        "detalle_simulaciones": detalle_simulaciones,
        "consumos_bms": consumos_bms,
        "detalle_bms": detalle_bms,
    }


def crear_simulacion(codigo, nombre, descripcion, activa):
    conn = conectar_db()
    c = conn.cursor()

    if activa:
        c.execute("UPDATE simulaciones SET activa=0 WHERE codigo_proyecto=?", (codigo,))

    sim_id = _insertar_y_obtener_id(c, """
        INSERT INTO simulaciones (codigo_proyecto, nombre_simulacion, descripcion, activa)
        VALUES (?, ?, ?, ?)
    """, (codigo, nombre, descripcion, 1 if activa else 0))

    conn.commit()
    conn.close()
    return sim_id


def guardar_detalle_simulacion(sim_id, df):
    conn = conectar_db()
    c = conn.cursor()

    filas = [
        (
            int(sim_id),
            int(fila["anio"]),
            int(fila["mes"]),
            fila["categoria"],
            float(fila["consumo_kwh"]),
        )
        for _, fila in df.iterrows()
    ]

    c.executemany("""
        INSERT INTO simulacion_detalle (simulacion_id, anio, mes, categoria, consumo_kwh)
        VALUES (?, ?, ?, ?, ?)
    """, filas)

    conn.commit()
    conn.close()


def cargar_simulaciones(codigo):
    conn = conectar_db()
    df = leer_sql(
        "SELECT * FROM simulaciones WHERE codigo_proyecto=? ORDER BY fecha_creacion DESC",
        conn,
        params=(codigo,)
    )
    conn.close()
    return df


def cargar_simulacion_activa(codigo):
    conn = conectar_db()
    df = leer_sql(
        "SELECT * FROM simulaciones WHERE codigo_proyecto=? AND activa=1 LIMIT 1",
        conn,
        params=(codigo,)
    )
    conn.close()
    return df


def cargar_detalle_simulacion(sim_id):
    conn = conectar_db()
    df = leer_sql(
        "SELECT * FROM simulacion_detalle WHERE simulacion_id=? ORDER BY anio, mes, categoria",
        conn,
        params=(int(sim_id),)
    )
    conn.close()
    return df


def marcar_simulacion_activa(sim_id, codigo):
    conn = conectar_db()
    c = conn.cursor()
    c.execute("UPDATE simulaciones SET activa=0 WHERE codigo_proyecto=?", (codigo,))
    c.execute("UPDATE simulaciones SET activa=1 WHERE id=?", (int(sim_id),))
    conn.commit()
    conn.close()


def crear_consumo_bms(codigo, anio, mes, nombre, descripcion):
    conn = conectar_db()
    c = conn.cursor()

    bms_id = _insertar_y_obtener_id(c, """
        INSERT INTO consumos_bms (codigo_proyecto, anio, mes, nombre_importacion, descripcion)
        VALUES (?, ?, ?, ?, ?)
    """, (codigo, int(anio), int(mes), nombre, descripcion))

    conn.commit()
    conn.close()
    return bms_id


def guardar_detalle_bms(bms_id, df):
    conn = conectar_db()
    c = conn.cursor()

    filas = [
        (
            int(bms_id),
            fila["categoria"],
            float(fila["consumo_kwh"]),
            fila["nombre_original_bms"],
            float(fila.get("electricidad_kwh", 0)),
            float(fila.get("gas_kwh", 0)),
        )
        for _, fila in df.iterrows()
    ]

    c.executemany("""
        INSERT INTO consumo_bms_detalle (
            consumo_bms_id, categoria, consumo_kwh, nombre_original_bms,
            electricidad_kwh, gas_kwh
        )
        VALUES (?, ?, ?, ?, ?, ?)
    """, filas)

    conn.commit()
    conn.close()


def cargar_consumos_bms(codigo):
    conn = conectar_db()
    df = leer_sql(
        "SELECT * FROM consumos_bms WHERE codigo_proyecto=? ORDER BY anio DESC, mes DESC, id DESC",
        conn,
        params=(codigo,)
    )
    conn.close()
    return df


def cargar_detalle_bms(bms_id):
    conn = conectar_db()
    df = leer_sql("""
        SELECT 
            categoria,
            consumo_kwh,
            COALESCE(electricidad_kwh, 0) AS electricidad_kwh,
            COALESCE(gas_kwh, 0) AS gas_kwh,
            nombre_original_bms
        FROM consumo_bms_detalle
        WHERE consumo_bms_id=?
        ORDER BY categoria
    """, conn, params=(int(bms_id),))
    conn.close()
    return df


def cargar_ultimo_bms_mes(codigo, anio, mes):
    conn = conectar_db()

    df = leer_sql("""
        SELECT 
            cbd.categoria,
            cbd.consumo_kwh AS real_kwh,
            COALESCE(cbd.electricidad_kwh, 0) AS electricidad_kwh,
            COALESCE(cbd.gas_kwh, 0) AS gas_kwh
        FROM consumo_bms_detalle cbd
        JOIN consumos_bms cb ON cb.id = cbd.consumo_bms_id
        WHERE cb.codigo_proyecto = ?
        AND cb.anio = ?
        AND cb.mes = ?
        AND cb.id = (
            SELECT MAX(id)
            FROM consumos_bms
            WHERE codigo_proyecto = ?
            AND anio = ?
            AND mes = ?
        )
    """, conn, params=(codigo, int(anio), int(mes), codigo, int(anio), int(mes)))

    conn.close()
    return df


def meses_bms(codigo, anio):
    conn = conectar_db()
    df = leer_sql("""
        SELECT mes, MAX(id) AS bms_id
        FROM consumos_bms
        WHERE codigo_proyecto = ?
        AND anio = ?
        GROUP BY mes
        ORDER BY mes
    """, conn, params=(codigo, int(anio)))
    conn.close()
    return df


def consumos_bms_anio(codigo, anio):
    meses = meses_bms(codigo, anio)

    if meses.empty:
        return pd.DataFrame()

    ids = ",".join(str(int(x)) for x in meses["bms_id"].tolist())

    conn = conectar_db()
    df = leer_sql(f"""
        SELECT 
            cb.mes,
            cbd.categoria,
            cbd.consumo_kwh,
            COALESCE(cbd.electricidad_kwh, 0) AS electricidad_kwh,
            COALESCE(cbd.gas_kwh, 0) AS gas_kwh
        FROM consumo_bms_detalle cbd
        JOIN consumos_bms cb ON cb.id = cbd.consumo_bms_id
        WHERE cbd.consumo_bms_id IN ({ids})
        ORDER BY cb.mes, cbd.categoria
    """, conn)
    conn.close()

    if (
        df["electricidad_kwh"].sum() == 0
        and df["gas_kwh"].sum() == 0
        and df["consumo_kwh"].sum() > 0
    ):
        df["electricidad_kwh"] = df["consumo_kwh"]
        df["gas_kwh"] = 0

    return df
