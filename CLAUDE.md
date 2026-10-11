# PGI Energía

App Streamlit que compara el consumo energético simulado (DesignBuilder `.dat`) con el real (CSV del
BMS) por edificio, mes y categoría. Datos en SQLite. Descripción completa en `README.md`.

## Comandos

- Ejecutar: `streamlit run app.py`
- Datos demo: `python -m energia.demo`
- Pruebas: `pytest` (usa una base de datos temporal). Con `TEST_DATABASE_URL` apuntando a una base
  PostgreSQL vacía de pruebas, se repiten también contra PostgreSQL (se borra su contenido).
- Análisis estático rápido: `python -m pyflakes app.py energia tests`

## Estructura

- `app.py` solo orquesta: barra lateral + una pestaña por módulo de `energia/tabs/`.
- Cada pestaña es `mostrar(ctx)` con `ctx` = `energia.contexto.Contexto` (edificios, código, edificio,
  año y mes elegidos en la barra lateral).
- Lógica sin Streamlit en `db.py`, `parsers.py`, `analisis.py`, `utils.py`, `migrar.py`. Streamlit solo en
  `ui.py`, `graficos.py`, `auth.py`, `secretos.py` y `tabs/`. Mantener esa separación para poder probar
  la lógica sin la interfaz.
- `db.py` funciona con SQLite (por defecto) o PostgreSQL (si `DATABASE_URL` está definida). Las consultas
  se escriben con marcadores `?`; con PostgreSQL se traducen a `%s`. Las lecturas van por `leer_sql`, los
  `INSERT` que necesitan el id por `_insertar_y_obtener_id`, y el SQL de tablas por `_ddl`. `psycopg` se
  importa solo si se usa PostgreSQL, para que el uso local no lo necesite.
- `auth.py`: el acceso solo se exige si hay `[usuarios]` en los secretos; se comprueba antes de leer
  ningún dato (`requerir_login()` + `st.stop()` en `app.py`).
- Constantes y rutas en `config.py`. `config.DB` y `config.CARPETA_BASE` se leen en cada llamada
  (no se copian a otra variable) para que las pruebas puedan redirigirlas.

## Convenciones

- Nombres de funciones, variables y textos de interfaz en español.
- Los lectores de archivos devuelven `(df, errores)` o `(df, ignoradas, errores)`; no lanzan excepciones
  por un archivo mal formado, devuelven la lista de errores para mostrarla en pantalla.
- Un mes puede tener varias importaciones BMS: se usa siempre la de `id` más alto.
- Las categorías de consumo son las de DesignBuilder en inglés (`Heating`, `Interior Lighting`…);
  `MAPEO_DAT` en `parsers.py` normaliza los nombres del `.dat`.

## Cuidado

- `database.db` y `datos_edificios/` tienen datos de clientes reales: nunca añadirlos a git. Tampoco
  `.streamlit/secrets.toml` ni ninguna dirección de base de datos o contraseña.
- No añadir lógica que lea datos antes de `requerir_login()` en `app.py`.
- `leer_texto_archivo` solo prueba UTF-16 si el archivo trae BOM o bytes nulos. Probarlo siempre
  rompe los CSV UTF-8 de longitud par (hay una prueba de regresión).
- `limpiar_numero`: sin coma en el texto, el punto se trata como decimal (`"1.234"` → 1.234).
  Un BMS que exporte miles con punto y sin decimales se leería mal.
