# PGI Energía

App Streamlit que compara el consumo energético simulado (DesignBuilder `.dat`) con el real (CSV del
BMS) por edificio, mes y categoría. Datos en SQLite. Descripción completa en `README.md`.

## Comandos

- Ejecutar: `streamlit run app.py` (interfaz Streamlit) o `python servidor.py` (interfaz web HTML, puerto 8504)
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
- Interfaz web (alternativa a Streamlit): `servidor.py` (Starlette, solo 127.0.0.1) sirve `web/` y una API JSON
  sobre `energia/servicios.py`. `servicios.py` y `figuras.py` no importan Streamlit: reúnen datos y figuras
  Plotly ya en JSON, y devuelven `{"aviso": ...}` si falta un dato previo o lanzan `ValueError` con un mensaje
  apto para el usuario (la ruta lo convierte en 400). `graficos.py` (Streamlit) reutiliza `figuras.py`.
- `web/` es HTML+CSS+JS sin dependencias (solo Plotly, servido desde el paquete de Python): `js/ui.js` (DOM,
  tablas, gráficos, formularios, API), `js/shell.js` (paneles, atajos, contexto), `js/escenarios.js` (catálogo
  de escenarios y subescenarios; cada subescenario es `render(ctx)` que devuelve un nodo a pantalla completa).
  Estilo y atajos copiados de las apps OU (`ag_ou/docs/DESIGN_SYSTEM.md`): usar siempre las variables de `:root`.
  `js/alertas.js` (mapa de calor + detalle en el panel derecho `EN.detalle`) y `js/constructor.js` (datos mensuales y
  gráficos por comandos) registran sus escenarios
  en `EN.ESC_ALERTAS` y `EN.ESC_CONSTRUCTOR`, que `escenarios.js` ensambla en `EN.ESCENARIOS`. Resúmenes y
  formularios usan `EN.lista` (dos columnas, título · valor, avisos al final con punto de gravedad).
  Nada de ventanas emergentes: la paleta de comandos (`Ctrl+/`, `EN.paleta` en `ui.js`) sustituye al canvas mientras
  está abierta y lo devuelve al cerrarse. `EN.abrirPaleta` (`shell.js`) junta los comandos de la vista, que ésta
  publica en `EN.comandosVista` (lista de `{id, titulo, desc, grupo, run}`), con los generales («Ir a», paneles).
  `replaceChildren` convierte `null` en el texto "null": usar `EN.llenar` si algún hijo puede ser nulo.
  Iconos: nada de emojis; SVG de Lucide (MIT, de iconbuddy: `https://files.svgcdn.io/lucide/<nombre>.svg`)
  guardados en `EN.ICONOS` (solo el interior del `<svg>`) y montados con `EN.icono(nombre, tam)`, en
  `currentColor` (acento `--color-icon-accent`). Se mantienen los glifos tipográficos (◂ ▸ ↑ ↓ ⇧).
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
