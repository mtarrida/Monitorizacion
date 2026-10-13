# PGI Energía

App web (HTML + servidor Python) que compara el consumo energético simulado (DesignBuilder `.dat`) con el
real (CSV del BMS) por edificio, mes y categoría. Datos en SQLite. Descripción completa en `README.md`.

Esta rama (`html-ou`) ya no tiene Streamlit: la versión con Streamlit vive en `main` y en el historial de git.
No volver a añadirla ni dejar código que la espere.

## Comandos

- Ejecutar: `python servidor.py` (http://127.0.0.1:8504; con `PGI Energia.bat` en Windows)
- Datos demo: `python -m energia.demo` (o arrancar con `ENERGIA_DEMO=1`)
- Pruebas: `pytest` (usa una base de datos temporal; incluye el motor de tablas con Node). Con
  `TEST_DATABASE_URL` apuntando a una base PostgreSQL vacía de pruebas, se repiten también contra PostgreSQL
  (se borra su contenido).
- Sintaxis del JavaScript: `node --check web/js/*.js` (uno por uno)

## Estructura

- `servidor.py` (Starlette, solo 127.0.0.1) sirve `web/` y una API JSON sobre `energia/servicios.py`. No hay
  acceso con usuario y contraseña: si algún día se abre a la red, hay que añadirlo antes de leer ningún dato.
- Lógica sin interfaz: `db.py`, `parsers.py`, `analisis.py`, `utils.py`, `migrar.py`, `correo.py`, `buzon.py`,
  `servicios.py`, `figuras.py`. `servicios.py` y `figuras.py` reúnen datos y figuras Plotly ya en JSON, y devuelven
  `{"aviso": ...}` si falta un dato previo o lanzan `ValueError` con un mensaje apto para el usuario (la ruta lo
  convierte en 400).
- `db.py` funciona con SQLite (por defecto) o PostgreSQL (si `DATABASE_URL` está definida). Las consultas
  se escriben con marcadores `?`; con PostgreSQL se traducen a `%s`. Las lecturas van por `leer_sql`, los
  `INSERT` que necesitan el id por `_insertar_y_obtener_id`, y el SQL de tablas por `_ddl`. `psycopg` se
  importa solo si se usa PostgreSQL, para que el uso local no lo necesite.
- Correo: `correo.py` decide a qué edificio corresponde un correo (palabras clave del asunto y remitente
  guardadas en cada edificio); `buzon.py` lee el buzón por IMAP (configuración solo por variables de entorno
  `ENERGIA_IMAP_*`), deja los CSV en `bandeja_correo/` de cada edificio y propone el mes. Nada se importa
  solo: el usuario importa o descarta desde BMS › Importar CSV. El buzón se abre en solo lectura. Las pruebas
  usan un buzón falso; no hay red en las pruebas.
- `web/` es HTML+CSS+JS sin dependencias (solo Plotly, servido desde el paquete de Python): `js/ui.js` (DOM,
  tablas, gráficos, formularios, paleta, API), `js/shell.js` (paneles, atajos, contexto, soltar archivos),
  `js/escenarios.js` (catálogo de escenarios y subescenarios; cada subescenario es `render(ctx)` que devuelve un
  nodo a pantalla completa). Estilo y atajos copiados de las apps OU (`ag_ou/docs/DESIGN_SYSTEM.md`): usar siempre
  las variables de `:root`.
  `js/alertas.js` (mapa de calor + detalle en el panel derecho `EN.detalle`) y `js/constructor.js` (datos mensuales
  y gráficos por comandos) registran sus escenarios en `EN.ESC_ALERTAS` y `EN.ESC_CONSTRUCTOR`, que
  `escenarios.js` ensambla en `EN.ESCENARIOS`. El motor de tablas del Constructor es puro (`js/tabla_motor.js`) y
  se prueba con Node (`tests/web/test_motor.js`). Resúmenes y formularios usan `EN.lista` (dos columnas,
  título · valor, avisos al final con punto de gravedad); los resúmenes con poco contenido llevan un gráfico en
  el hueco que sobra (`resumenConGrafico`).
  Nada de ventanas emergentes: la paleta de comandos (`Ctrl+/`, `EN.paleta` en `ui.js`) sustituye al canvas mientras
  está abierta y lo devuelve al cerrarse. `EN.abrirPaleta` (`shell.js`) junta los comandos de la vista, que ésta
  publica en `EN.comandosVista` (lista de `{id, titulo, desc, grupo, run}`), con los generales («Ir a», paneles).
  Los archivos se pueden soltar en cualquier parte de la ventana (`shell.js`): un `.csv` va a BMS › Importar y un
  `.dat` a Simulaciones › Importar; la vista de importación se registra en `EN.receptores` y recoge lo pendiente
  con `EN.recogerArchivos`.
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
- Constructor: el usuario irá pidiendo los comandos que necesite; no portar de golpe los de EnergyPlus HTML++.
  Los escenarios que se montan con él deben ser simples y legibles para quien los lea.

## Cuidado

- `database.db` y `datos_edificios/` tienen datos de clientes reales: nunca añadirlos a git. Tampoco
  `.env`, contraseñas del buzón ni ninguna dirección de base de datos.
- Las pruebas del navegador que importan archivos se hacen contra un servidor aparte con
  `ENERGIA_DB` y `ENERGIA_DATOS` apuntando a una carpeta temporal, nunca contra la base real.
- `leer_texto_archivo` solo prueba UTF-16 si el archivo trae BOM o bytes nulos. Probarlo siempre
  rompe los CSV UTF-8 de longitud par (hay una prueba de regresión).
- `limpiar_numero`: sin coma en el texto, el punto se trata como decimal (`"1.234"` → 1.234).
  Un BMS que exporte miles con punto y sin decimales se leería mal.
