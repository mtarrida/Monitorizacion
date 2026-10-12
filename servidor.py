"""Servidor local de la interfaz web (HTML) de PGI Energía.

Uso:  python servidor.py        ->  http://127.0.0.1:8504

Sirve la carpeta `web/` y una API JSON que reutiliza la lógica de `energia/` (sin Streamlit).
Escucha solo en 127.0.0.1 porque esta versión todavía no tiene acceso con usuario y contraseña.
"""
import json
import math
import os
import threading
import traceback
import webbrowser
from contextlib import asynccontextmanager

import plotly
from starlette.applications import Starlette
from starlette.concurrency import run_in_threadpool
from starlette.middleware import Middleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import FileResponse, JSONResponse
from starlette.routing import Mount, Route
from starlette.staticfiles import StaticFiles

from energia import servicios
from energia.db import inicializar_db

RAIZ = os.path.dirname(os.path.abspath(__file__))
PUERTO = int(os.environ.get("ENERGIA_PUERTO", "8504"))


# ---------------------------------------------------------------------------
# Utilidades de las rutas
# ---------------------------------------------------------------------------

def _sin_nan(valor):
    """Cambia NaN/inf por null: JSON estricto no los admite."""
    if isinstance(valor, float) and not math.isfinite(valor):
        return None
    if isinstance(valor, dict):
        return {k: _sin_nan(v) for k, v in valor.items()}
    if isinstance(valor, list):
        return [_sin_nan(v) for v in valor]
    return valor


def _parametro(request, nombre, tipo=str, defecto=None):
    bruto = request.query_params.get(nombre)
    if bruto is None or bruto == "":
        return defecto
    try:
        return tipo(bruto)
    except ValueError:
        raise ValueError(f"El parámetro {nombre} no es válido.")


def _anio_mes(request):
    return _parametro(request, "anio", int, servicios.config.ANIO_ACTUAL), _parametro(request, "mes", int, 1)


def api(funcion):
    """Convierte una función de ruta en endpoint JSON: ValueError -> 400, otro error -> 500."""
    async def endpoint(request):
        try:
            resultado = await funcion(request)
            return JSONResponse(_sin_nan(resultado))
        except ValueError as error:
            return JSONResponse({"error": str(error)}, status_code=400)
        except Exception as error:  # el detalle va a la consola del servidor
            traceback.print_exc()
            return JSONResponse({"error": f"Error interno: {error}"}, status_code=500)
    return endpoint


async def _cuerpo_json(request):
    try:
        datos = await request.json()
    except json.JSONDecodeError:
        raise ValueError("El cuerpo de la petición no es JSON válido.")
    if not isinstance(datos, dict):
        raise ValueError("El cuerpo de la petición tiene que ser un objeto JSON.")
    return datos


# ---------------------------------------------------------------------------
# Edificios
# ---------------------------------------------------------------------------

async def r_config(request):
    return servicios.config_app()


async def r_edificios(request):
    return {"edificios": await run_in_threadpool(servicios.lista_edificios, request.query_params.get("todos") == "1")}


async def r_edificio_crear(request):
    return await run_in_threadpool(servicios.crear_edificio, await _cuerpo_json(request))


async def r_edificio_editar(request):
    return await run_in_threadpool(servicios.editar_edificio, request.path_params["codigo"], await _cuerpo_json(request))


async def r_edificio_estado(request):
    datos = await _cuerpo_json(request)
    return await run_in_threadpool(servicios.cambiar_estado, request.path_params["codigo"], datos.get("estado"))


async def r_edificio_correo(request):
    datos = await _cuerpo_json(request)
    return await run_in_threadpool(
        servicios.guardar_correo, request.path_params["codigo"], datos.get("asunto"), datos.get("remitente"))


async def r_edificio_eliminacion(request):
    return await run_in_threadpool(servicios.resumen_eliminacion, request.path_params["codigo"])


async def r_edificio_eliminar(request):
    datos = await _cuerpo_json(request)
    return await run_in_threadpool(servicios.borrar_edificio, request.path_params["codigo"], datos.get("confirmacion"))


# ---------------------------------------------------------------------------
# Panel, simulaciones y BMS
# ---------------------------------------------------------------------------

async def r_panel(request):
    anio, mes = _anio_mes(request)
    return await run_in_threadpool(servicios.panel, request.query_params.get("codigo"), anio, mes)


async def r_simulaciones(request):
    return await run_in_threadpool(servicios.simulaciones, request.query_params.get("codigo"))


async def r_simulacion_detalle(request):
    return await run_in_threadpool(servicios.detalle_simulacion, int(request.path_params["sim_id"]))


async def r_simulacion_importar(request):
    form = await request.form()
    archivo = form.get("archivo")
    if archivo is None or not hasattr(archivo, "read"):
        raise ValueError("Sube un archivo .dat.")
    contenido = await archivo.read()
    try:
        anio = int(form.get("anio") or servicios.config.ANIO_ACTUAL)
    except ValueError:
        raise ValueError("El año no es válido.")
    return await run_in_threadpool(
        servicios.importar_simulacion,
        form.get("codigo"), form.get("nombre"), form.get("descripcion"), anio,
        form.get("activa") in ("1", "true", "on"), archivo.filename, contenido,
    )


async def r_simulacion_activar(request):
    datos = await _cuerpo_json(request)
    return await run_in_threadpool(servicios.activar_simulacion, datos.get("codigo"), int(request.path_params["sim_id"]))


async def r_bms(request):
    return await run_in_threadpool(servicios.bms, request.query_params.get("codigo"))


async def r_bms_detalle(request):
    return await run_in_threadpool(servicios.detalle_bms, int(request.path_params["bms_id"]))


async def r_bms_importar(request):
    form = await request.form()
    archivos = [a for a in form.getlist("archivos") if hasattr(a, "read")]
    try:
        meses = json.loads(form.get("meses") or "[]")
        anio = int(form.get("anio") or servicios.config.ANIO_ACTUAL)
    except (json.JSONDecodeError, ValueError):
        raise ValueError("Los datos de la importación no son válidos.")
    if len(meses) != len(archivos):
        raise ValueError("Cada archivo necesita su mes.")

    entradas = []
    for archivo, mes in zip(archivos, meses):
        entradas.append({
            "mes": mes,
            "archivo": archivo.filename,
            "contenido": await archivo.read(),
            "nombre": form.get("nombre") if len(archivos) == 1 else None,
            "descripcion": form.get("descripcion") if len(archivos) == 1 else "Carga múltiple",
        })
    return await run_in_threadpool(servicios.importar_bms, form.get("codigo"), anio, entradas)


# ---------------------------------------------------------------------------
# Comparativa, informe, costes y CO2
# ---------------------------------------------------------------------------

async def r_comparativa_mes(request):
    anio, mes = _anio_mes(request)
    return await run_in_threadpool(servicios.comparativa_mes, request.query_params.get("codigo"), anio, mes)


async def r_comparativa_acumulada(request):
    anio, _ = _anio_mes(request)
    return await run_in_threadpool(servicios.comparativa_acumulada, request.query_params.get("codigo"), anio)


async def r_comparativa_base(request):
    anio, _ = _anio_mes(request)
    bruto = request.query_params.get("categorias")
    categorias = [c for c in bruto.split("|") if c] if bruto else None
    return await run_in_threadpool(servicios.base_comparable, anio, categorias)


async def r_alertas(request):
    anio, _ = _anio_mes(request)
    return await run_in_threadpool(servicios.alertas, request.query_params.get("codigo"), anio)


async def r_datos_mensuales(request):
    anio, _ = _anio_mes(request)
    return await run_in_threadpool(servicios.datos_mensuales, request.query_params.get("codigo"), anio)


async def r_informe(request):
    anio, mes = _anio_mes(request)
    return await run_in_threadpool(servicios.informe, request.query_params.get("codigo"), anio, mes)


async def r_costes(request):
    anio, _ = _anio_mes(request)
    return await run_in_threadpool(
        servicios.costes, request.query_params.get("codigo"), anio,
        _parametro(request, "precio_elec", float, 0.18), _parametro(request, "precio_gas", float, 0.07),
    )


async def r_co2(request):
    anio, _ = _anio_mes(request)
    return await run_in_threadpool(
        servicios.co2, request.query_params.get("codigo"), anio,
        _parametro(request, "factor_elec", float, 0.18), _parametro(request, "factor_gas", float, 0.20),
    )


# ---------------------------------------------------------------------------
# Aplicación
# ---------------------------------------------------------------------------

async def plotly_js(request):
    """El plotly.js que trae el paquete de Python: misma versión que genera las figuras."""
    return FileResponse(os.path.join(os.path.dirname(plotly.__file__), "package_data", "plotly.min.js"),
                        media_type="application/javascript")


class SinCache(BaseHTTPMiddleware):
    """Evita ver una versión vieja de la interfaz tras editarla."""

    async def dispatch(self, request, call_next):
        respuesta = await call_next(request)
        respuesta.headers["Cache-Control"] = "no-cache"
        return respuesta


@asynccontextmanager
async def lifespan(app):
    inicializar_db()
    yield


RUTAS = [
    Route("/api/config", api(r_config)),
    Route("/api/edificios", api(r_edificios)),
    Route("/api/edificios", api(r_edificio_crear), methods=["POST"]),
    Route("/api/edificios/{codigo}", api(r_edificio_editar), methods=["PUT"]),
    Route("/api/edificios/{codigo}/estado", api(r_edificio_estado), methods=["POST"]),
    Route("/api/edificios/{codigo}/correo", api(r_edificio_correo), methods=["POST"]),
    Route("/api/edificios/{codigo}/eliminacion", api(r_edificio_eliminacion)),
    Route("/api/edificios/{codigo}/eliminar", api(r_edificio_eliminar), methods=["POST"]),
    Route("/api/panel", api(r_panel)),
    Route("/api/simulaciones", api(r_simulaciones)),
    Route("/api/simulaciones", api(r_simulacion_importar), methods=["POST"]),
    Route("/api/simulaciones/{sim_id:int}/detalle", api(r_simulacion_detalle)),
    Route("/api/simulaciones/{sim_id:int}/activar", api(r_simulacion_activar), methods=["POST"]),
    Route("/api/bms", api(r_bms)),
    Route("/api/bms", api(r_bms_importar), methods=["POST"]),
    Route("/api/bms/{bms_id:int}/detalle", api(r_bms_detalle)),
    Route("/api/comparativa/mes", api(r_comparativa_mes)),
    Route("/api/comparativa/acumulada", api(r_comparativa_acumulada)),
    Route("/api/comparativa/base", api(r_comparativa_base)),
    Route("/api/alertas", api(r_alertas)),
    Route("/api/datos", api(r_datos_mensuales)),
    Route("/api/informe", api(r_informe)),
    Route("/api/costes", api(r_costes)),
    Route("/api/co2", api(r_co2)),
    Route("/vendor/plotly.min.js", plotly_js),
    Mount("/assets", StaticFiles(directory=os.path.join(RAIZ, "assets")), name="assets"),
    Mount("/", StaticFiles(directory=os.path.join(RAIZ, "web"), html=True), name="web"),
]

app = Starlette(routes=RUTAS, lifespan=lifespan, middleware=[Middleware(SinCache)])


def main():
    import uvicorn

    # La base de datos y las carpetas de datos se resuelven respecto a la carpeta de la app.
    os.chdir(RAIZ)
    url = f"http://127.0.0.1:{PUERTO}"
    print(f"PGI Energía (web) en {url}  ·  Ctrl+C para parar")
    if os.environ.get("ENERGIA_NO_ABRIR") != "1":
        threading.Timer(1.5, webbrowser.open, args=(url,)).start()
    uvicorn.run(app, host="127.0.0.1", port=PUERTO, log_level="warning")


if __name__ == "__main__":
    main()
