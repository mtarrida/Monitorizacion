# PGI Energía

Aplicación web para **comprobar si un edificio consume lo que se calculó en proyecto**.

Cuando se diseña un edificio se hace una simulación energética (DesignBuilder) que predice cuánta
energía gastará cada mes en calefacción, refrigeración, iluminación, ventilación, etc. Cuando el
edificio ya funciona, su sistema de gestión (BMS) mide lo que consume de verdad. Esta aplicación
pone ambas cifras una al lado de la otra, detecta dónde y cuánto se desvía el consumo real y
ayuda a explicar por qué.

> Esta rama (`html-ou`) solo tiene la interfaz web HTML. La versión anterior con Streamlit sigue
> en `main` y en el historial de git.

## Para qué sirve

- **Detectar desviaciones**: compara, mes a mes y por categoría, el consumo simulado con el real
  del BMS y las clasifica con un semáforo (verde hasta ±10 %, amarillo hasta ±20 %, rojo más de ±20 %).
- **Tener todos los edificios en un sitio**: ficha de cada proyecto (cliente, ubicación, uso,
  superficie, sistema de climatización), con su simulación y sus consumos mensuales.
- **Redactar el informe mensual**: resumen ejecutivo, alertas y observaciones técnicas.
- **Calcular costes y emisiones**: a partir del consumo de electricidad y gas, con precios y
  factores de CO₂ editables, y proyección anual.
- **Comparar edificios entre sí**: ranking de consumo específico (kWh/m², kWh/habitación,
  kWh/puesto, kWh/cama…) entre edificios de la misma categoría.

## Cómo se usa

1. **Edificios** → crear el proyecto (código, nombre, cliente, superficie, unidad de referencia…).
2. **Simulaciones** → importar el `.dat` exportado de DesignBuilder y marcarlo como activo. Es material
   interno: se aporta a mano.
3. **BMS** → los CSV de consumos del sistema de gestión ("CSV monitorización") se arrastran a la lista
   (uno o varios a la vez) o llegan solos por correo (ver más abajo).
4. **Comparativa / Alertas / Informe mensual** → elegir edificio, año y mes en el panel de la izquierda
   y revisar desviaciones, gráficos y observaciones.
5. **Costes / CO₂** → ajustar precios y factores de emisión y ver el acumulado y la proyección anual.

Si un mes se importa más de una vez, **cuenta la última importación**.

### Formatos de archivo

| Archivo | Qué debe contener |
|---|---|
| CSV del BMS | Columnas `Tipologia`, `Electricidad [kWh]` y `Gas Natural [kWh]`, una fila por categoría. Se ignoran las filas "Total". Acepta separador `,` `;` o tabulador, y decimales con punto o coma. |
| `.dat` de DesignBuilder | Tabla separada por tabuladores con una fila por categoría y 12 columnas mensuales (UTF-16 o UTF-8). Las categorías no reconocidas se ignoran y se avisan. |

Hay archivos de ejemplo en [`ejemplos/`](ejemplos/) y datos de demostración en `ejemplos/demo/`.

### Soltar archivos en cualquier parte

Se puede soltar un archivo en cualquier parte de la ventana: un `.csv` lleva a BMS › Importar CSV y se
añade a la lista; un `.dat` lleva a Simulaciones › Importar y queda elegido en el formulario. Si ya se está
en esa pantalla, se añaden ahí. Otros tipos de archivo se avisan y se rechazan.

## Ejecutarla en local

```bash
pip install -r requirements.txt
python servidor.py        # abre http://127.0.0.1:8504
```

En Windows, `PGI Energia.bat` hace lo mismo desde la carpeta de la app (necesita un entorno `.venv`).
El servidor escucha solo en `127.0.0.1`: no hay acceso con usuario y contraseña, así que no está pensado
para abrirse a la red tal cual.

Para probarla con datos ficticios (edificio `PGI-DEMO-001`, con simulación y 3 meses de BMS):

```bash
python -m energia.demo
```

o arrancar el servidor con `ENERGIA_DEMO=1`, que lo crea si no existe.

## Manejo

Un panel con el contexto y los **escenarios**, un segundo panel con los **subescenarios** del escenario
elegido y un canvas limpio donde cada subescenario (un gráfico, una tabla o un formulario) ocupa toda la
pantalla, sin scroll de página. Con aspecto y atajos copiados de las apps OU.

| Atajo | Acción |
|---|---|
| `↑` `↓` | Subescenario anterior / siguiente |
| `Ctrl` + `↑` `↓` (o `Alt` + `1…9`, `0` el décimo) | Escenario anterior / siguiente (o directo) |
| `Ctrl` + `←` | Cicla los paneles de la izquierda: ninguno → escenarios → ambos → subescenarios |
| `Ctrl` + `⇧` + `←` | Pliega todos los paneles de la izquierda |
| `Ctrl` + `→` / `Ctrl` + `⇧` + `→` | Abre o cierra el panel de detalle de la derecha |
| `Ctrl` + `/` | Paleta de comandos: ocupa el canvas, se filtra al escribir y aplica el comando sobre la vista actual (comandos del Constructor, ir a cualquier escenario, paneles) |
| `Esc` | Saca el foco de un campo para volver a usar las flechas |

Los paneles también se redimensionan arrastrando el separador y se pliegan con su botón ◂/▸. El
estado (paneles, anchos, escenario, edificio, año, mes, precios y factores) se recuerda en el navegador.

Dos escenarios son propios de esta interfaz. **Alertas** muestra un mapa de calor de desviaciones
(categorías × meses, por gravedad); al pulsar un cuadrado, una categoría o un mes, el porqué (datos,
evolución, posibles causas y qué comprobar) aparece en el panel derecho, y hay un resumen ordenado de
menos a más graves. **Constructor** enseña los datos mensuales como una tabla que se edita con comandos
(ocultar y mover columnas, seleccionar y colorear filas, columnas con fórmulas, totales, ordenar…), cada
cambio queda en un registro de pasos que se puede deshacer, guardar como escenario o copiar, y sobre la tabla
se montan gráficos («paneles de escena»). Todo ocurre dentro del canvas, sin ventanas emergentes. De momento
lo ve todo el mundo; más adelante será solo para administradores.

## Correo con los CSV del BMS

Los CSV de monitorización llegan por correo. Para recogerlos solos:

1. En BMS › Importar CSV, cada edificio tiene **palabras clave del asunto** (y, si se quiere, un remitente).
   Un correo es de ese edificio si su asunto contiene todas las palabras.
2. En el equipo donde corre el servidor se definen las variables de entorno del buzón (nunca en el código
   ni en el repositorio):

   | Variable | Qué es |
   |---|---|
   | `ENERGIA_IMAP_SERVIDOR` | Servidor IMAP, p. ej. `imap.gmail.com` |
   | `ENERGIA_IMAP_USUARIO` | Dirección del buzón |
   | `ENERGIA_IMAP_CLAVE` | Contraseña o clave de aplicación |
   | `ENERGIA_IMAP_PUERTO` | 993 por defecto |
   | `ENERGIA_IMAP_CARPETA` | `INBOX` por defecto |
   | `ENERGIA_IMAP_DIAS` | Días hacia atrás que se miran, 45 por defecto |
   | `ENERGIA_IMAP_MINUTOS` | Cada cuántos minutos revisa el servidor por su cuenta (0 o vacío: solo a mano) |

3. El botón **Revisar correo ahora** (o la revisión automática) deja los CSV adjuntos en una bandeja
   por edificio (`datos_edificios/<edificio>/bandeja_correo/`) y aparecen en la lista con origen **Correo**,
   con el mes propuesto a partir del nombre del archivo (o, si no lo dice, el mes anterior al del correo).
   Se **importan o descartan con un clic**: nada se importa solo. El buzón se abre solo para leer; los
   correos no se marcan como leídos ni se borran.

Está probado con un buzón IMAP simulado; falta probarlo contra el buzón real. Ojo: Microsoft 365 suele tener
desactivada la contraseña simple por IMAP; en ese caso hará falta otra vía (OAuth o Microsoft Graph).

## Pruebas

```bash
pip install -r requirements-dev.txt
pytest
```

Las pruebas usan una base de datos temporal; nunca tocan la real. Incluyen el motor de tablas del
Constructor (se ejecuta con Node si está instalado). Si defines `TEST_DATABASE_URL` con la dirección de
una base PostgreSQL **vacía de pruebas** (se borra su contenido en cada prueba), se ejecutan también contra
PostgreSQL.

## Estructura del código

```
servidor.py            Servidor local (Starlette) y API JSON
web/                   Interfaz: index.html, styles.css y js/ (ui, shell, escenarios, alertas, constructor…)
energia/
  config.py            Rutas, colores y constantes
  db.py                Acceso a datos (SQLite o PostgreSQL)
  migrar.py            Copia database.db a PostgreSQL
  parsers.py           Lectura de .dat (DesignBuilder) y CSV (BMS)
  analisis.py          Comparativas, alertas e indicadores específicos
  servicios.py         Datos y figuras listos para la API
  figuras.py           Figuras Plotly
  correo.py            Qué correo corresponde a qué edificio (lógica pura)
  buzon.py             Lectura del buzón IMAP y bandeja de CSV recibidos
  utils.py             Lectura de archivos y limpieza de texto/números
  demo.py              Datos de demostración
tests/                 Pruebas automáticas (pytest y Node)
ejemplos/              Plantillas y datos de demostración
```

## Configuración

| Variable de entorno | Por defecto | Qué hace |
|---|---|---|
| `ENERGIA_DB` | `database.db` | Ruta de la base de datos SQLite |
| `ENERGIA_DATOS` | `datos_edificios` | Carpeta donde se guardan copias de los archivos importados |
| `ENERGIA_PUERTO` | `8504` | Puerto del servidor |
| `ENERGIA_NO_ABRIR` | *(vacía)* | Con `1`, no abre el navegador al arrancar |
| `ENERGIA_DEMO` | *(vacía)* | Con `1`, crea el edificio de demostración al arrancar si no existe |
| `DATABASE_URL` | *(vacía)* | Dirección de PostgreSQL. Si está definida se usa en lugar de SQLite |
| `ENERGIA_IMAP_*` | *(vacías)* | Buzón de correo; ver «Correo con los CSV del BMS» |

## Datos de clientes

`database.db` y `datos_edificios/` contienen información de proyectos y clientes y **no se suben
al repositorio** (están en `.gitignore`). Haz copias de seguridad de ambos por separado.
