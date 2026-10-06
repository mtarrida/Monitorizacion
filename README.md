# PGI Energía

Aplicación web para **comprobar si un edificio consume lo que se calculó en proyecto**.

Cuando se diseña un edificio se hace una simulación energética (DesignBuilder) que predice cuánta
energía gastará cada mes en calefacción, refrigeración, iluminación, ventilación, etc. Cuando el
edificio ya funciona, su sistema de gestión (BMS) mide lo que consume de verdad. Esta aplicación
pone ambas cifras una al lado de la otra, detecta dónde y cuánto se desvía el consumo real y
ayuda a explicar por qué.

## Para qué sirve

- **Detectar desviaciones**: compara, mes a mes y por categoría, el consumo simulado con el real
  del BMS y las clasifica con un semáforo (🟢 hasta ±10 %, 🟡 hasta ±20 %, 🔴 más de ±20 %).
- **Tener todos los edificios en un sitio**: ficha de cada proyecto (cliente, ubicación, uso,
  superficie, sistema de climatización), con su simulación y sus consumos mensuales.
- **Redactar el informe mensual**: resumen ejecutivo, alertas y observaciones técnicas listas
  para descargar.
- **Calcular costes y emisiones**: a partir del consumo de electricidad y gas, con precios y
  factores de CO₂ editables, y proyección anual.
- **Comparar edificios entre sí**: ranking de consumo específico (kWh/m², kWh/habitación,
  kWh/puesto, kWh/cama…) entre edificios de la misma categoría.

## Cómo se usa

1. **Edificios** → crear el proyecto (código, nombre, cliente, superficie, unidad de referencia…).
2. **Simulaciones** → subir el archivo `.dat` exportado de DesignBuilder y marcarlo como activo.
3. **BMS** → subir cada mes el CSV de consumos del sistema de gestión (uno o varios meses a la vez).
4. **Comparativa / Informe mensual** → elegir edificio, año y mes en la barra lateral y revisar
   desviaciones, gráficos y observaciones.
5. **Costes / CO₂** → ajustar precios y factores de emisión y ver el acumulado y la proyección anual.

Si un mes se importa más de una vez, **cuenta la última importación**.

### Formatos de archivo

| Archivo | Qué debe contener |
|---|---|
| CSV del BMS | Columnas `Tipologia`, `Electricidad [kWh]` y `Gas Natural [kWh]`, una fila por categoría. Se ignoran las filas "Total". Acepta separador `,` `;` o tabulador, y decimales con punto o coma. |
| `.dat` de DesignBuilder | Tabla separada por tabuladores con una fila por categoría y 12 columnas mensuales (UTF-16 o UTF-8). Las categorías no reconocidas se ignoran y se avisan. |

Hay archivos de ejemplo en [`ejemplos/`](ejemplos/) y datos de demostración en `ejemplos/demo/`.

## Ejecutarla en local

```bash
pip install -r requirements.txt
streamlit run app.py
```

En Windows, `PGI Energia.bat` hace lo mismo desde `C:\PGI_APP_ENERGIA`.

Para probarla con datos ficticios (edificio `PGI-DEMO-001`, con simulación y 3 meses de BMS):

```bash
python -m energia.demo
```

## Pruebas

```bash
pip install -r requirements-dev.txt
pytest
```

Las pruebas usan una base de datos temporal; nunca tocan la real.

## Estructura del código

```
app.py                 Punto de entrada: barra lateral y las 8 pestañas
energia/
  config.py            Rutas, colores y constantes
  db.py                Acceso a datos (SQLite)
  parsers.py           Lectura de .dat (DesignBuilder) y CSV (BMS)
  analisis.py          Comparativas, alertas e indicadores específicos
  graficos.py          Gráficos Plotly
  ui.py                Estilos, cabecera, barra lateral y tablas
  utils.py             Lectura de archivos y limpieza de texto/números
  demo.py              Datos de demostración
  tabs/                Una pestaña por archivo: panel, edificios, simulaciones,
                       bms, comparativa, informe, costes, co2
tests/                 Pruebas automáticas
ejemplos/              Plantillas y datos de demostración
```

## Configuración

| Variable de entorno | Por defecto | Qué hace |
|---|---|---|
| `ENERGIA_DB` | `database.db` | Ruta de la base de datos SQLite |
| `ENERGIA_DATOS` | `datos_edificios` | Carpeta donde se guardan copias de los archivos importados |

## Datos de clientes

`database.db` y `datos_edificios/` contienen información de proyectos y clientes y **no se suben
al repositorio** (están en `.gitignore`). Haz copias de seguridad de ambos por separado.
