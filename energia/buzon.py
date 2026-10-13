"""Buzón de correo que recibe los CSV del BMS ("CSV monitorización").

Revisa el buzón por IMAP y deja los CSV adjuntos en una bandeja por edificio, sin importarlos: en
BMS › Importar CSV aparecen con origen «Correo» y se importan (o se descartan) con un clic, con el mes
propuesto a partir del nombre del archivo o, si no lo trae, de la fecha del correo.

La conexión se configura solo con variables de entorno (nunca en el código ni en el repositorio):

    ENERGIA_IMAP_SERVIDOR   p. ej. imap.gmail.com      (obligatoria)
    ENERGIA_IMAP_USUARIO    dirección del buzón        (obligatoria)
    ENERGIA_IMAP_CLAVE      contraseña o clave de aplicación (obligatoria)
    ENERGIA_IMAP_PUERTO     993 por defecto
    ENERGIA_IMAP_CARPETA    INBOX por defecto
    ENERGIA_IMAP_DIAS       cuántos días hacia atrás se miran, 45 por defecto
    ENERGIA_IMAP_MINUTOS    cada cuánto revisa el servidor por su cuenta; sin valor o 0, solo a mano

Un correo se elige por el asunto y el remitente que se guardan en cada edificio (ver `correo.py`).
El buzón se abre solo para leer (BODY.PEEK): los correos no se marcan como leídos ni se borran.
"""

import email
import imaplib
import json
import os
import re
import threading
from datetime import datetime, timedelta
from email import policy
from email.utils import parsedate_to_datetime

from energia import config
from energia.correo import coincide, normalizar_texto, palabras_clave
from energia.db import cargar_edificios
from energia.utils import crear_carpetas_edificio, limpiar_nombre

MESES_ES = {
    "enero": 1, "febrero": 2, "marzo": 3, "abril": 4, "mayo": 5, "junio": 6,
    "julio": 7, "agosto": 8, "septiembre": 9, "setiembre": 9, "octubre": 10, "noviembre": 11, "diciembre": 12,
}
MESES_EN = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
MAX_VISTOS = 4000

_cerrojo = threading.Lock()
_estado = {"ultima_revision": None, "nuevos": 0, "error": None}


# ---------------------------------------------------------------------------
# Configuración
# ---------------------------------------------------------------------------

def configuracion():
    """Datos de conexión desde el entorno, o None si falta alguno de los obligatorios."""
    servidor = os.environ.get("ENERGIA_IMAP_SERVIDOR", "").strip()
    usuario = os.environ.get("ENERGIA_IMAP_USUARIO", "").strip()
    clave = os.environ.get("ENERGIA_IMAP_CLAVE", "")
    if not (servidor and usuario and clave):
        return None
    return {
        "servidor": servidor,
        "puerto": int(os.environ.get("ENERGIA_IMAP_PUERTO") or 993),
        "usuario": usuario,
        "clave": clave,
        "carpeta": os.environ.get("ENERGIA_IMAP_CARPETA") or "INBOX",
        "dias": int(os.environ.get("ENERGIA_IMAP_DIAS") or 45),
    }


def minutos_de_revision():
    try:
        return max(0, int(os.environ.get("ENERGIA_IMAP_MINUTOS") or 0))
    except ValueError:
        return 0


def estado():
    """Para mostrar en pantalla: si hay buzón configurado y qué pasó en la última revisión."""
    cfg = configuracion()
    return {
        "configurado": cfg is not None,
        "buzon": cfg["usuario"] if cfg else None,
        "automatico_cada_min": minutos_de_revision(),
        **_estado,
    }


# ---------------------------------------------------------------------------
# Lógica pura (sin red)
# ---------------------------------------------------------------------------

def proponer_mes(nombre_archivo, recibido=None):
    """(año, mes) propuesto para un CSV. Primero el nombre del archivo (2026-03, 03-2026, marzo 2026...);
    si no dice nada, el mes anterior al de la fecha del correo (los CSV llegan al acabar el mes)."""
    nombre = normalizar_texto(os.path.splitext(os.path.basename(nombre_archivo or ""))[0])

    m = re.search(r"(?<!\d)(20\d{2})[ _\-./](0?[1-9]|1[0-2])(?!\d)", nombre)
    if m:
        return int(m.group(1)), int(m.group(2))
    m = re.search(r"(?<!\d)(0?[1-9]|1[0-2])[ _\-./](20\d{2})(?!\d)", nombre)
    if m:
        return int(m.group(2)), int(m.group(1))
    for palabra, mes in MESES_ES.items():
        m = re.search(rf"(?<![a-z]){palabra}(?![a-z])(?:[ _\-./]*(?:de )?(20\d{{2}}))?", nombre)
        if m:
            anio = int(m.group(1)) if m.group(1) else (recibido or datetime.now()).year
            return anio, mes

    fecha = recibido or datetime.now()
    primero = fecha.replace(day=1)
    anterior = primero - timedelta(days=1)
    return anterior.year, anterior.month


def _fecha_correo(mensaje):
    try:
        fecha = parsedate_to_datetime(str(mensaje["date"]))
        return fecha.replace(tzinfo=None) if fecha.tzinfo else fecha
    except (TypeError, ValueError):
        return datetime.now()


def _cabeceras(crudo):
    mensaje = email.message_from_bytes(crudo, policy=policy.default)
    return {
        "message_id": str(mensaje["message-id"] or "").strip(),
        "asunto": str(mensaje["subject"] or ""),
        "remitente": str(mensaje["from"] or ""),
    }


def adjuntos_csv(crudo):
    """Lista de (nombre, bytes) de los CSV adjuntos de un correo completo, más su fecha."""
    mensaje = email.message_from_bytes(crudo, policy=policy.default)
    encontrados = []
    for parte in mensaje.walk():
        nombre = parte.get_filename()
        if nombre and nombre.lower().endswith(".csv"):
            contenido = parte.get_payload(decode=True)
            if contenido:
                encontrados.append((nombre, contenido))
    return encontrados, _fecha_correo(mensaje)


def edificios_con_regla():
    """Edificios activos que tienen palabras clave de asunto guardadas."""
    df = cargar_edificios(False)
    return [e for e in df.to_dict("records") if palabras_clave(e.get("correo_asunto"))]


# ---------------------------------------------------------------------------
# Bandeja en disco: un CSV + un .json con sus datos, por edificio
# ---------------------------------------------------------------------------

def _carpeta_bandeja(codigo, nombre, subcarpeta=""):
    carpeta = os.path.join(crear_carpetas_edificio(codigo, nombre), "bandeja_correo", subcarpeta)
    os.makedirs(carpeta, exist_ok=True)
    return carpeta


def _guardar_en_bandeja(edificio, nombre_csv, contenido, datos):
    carpeta = _carpeta_bandeja(edificio["codigo_proyecto"], edificio["nombre"])
    base = f"{datos['recibido'][:10].replace('-', '')}_{limpiar_nombre(os.path.splitext(nombre_csv)[0])}"
    nombre = base + ".csv"
    n = 1
    while os.path.exists(os.path.join(carpeta, nombre)):
        n += 1
        nombre = f"{base}_{n}.csv"
    with open(os.path.join(carpeta, nombre), "wb") as f:
        f.write(contenido)
    with open(os.path.join(carpeta, nombre[:-4] + ".json"), "w", encoding="utf-8") as f:
        json.dump(dict(datos, archivo=nombre_csv), f, ensure_ascii=False)
    return nombre


def listar_bandeja(codigo, nombre_edificio):
    """CSV recibidos por correo y aún sin importar ni descartar, del más antiguo al más reciente."""
    carpeta = _carpeta_bandeja(codigo, nombre_edificio)
    items = []
    for fichero in sorted(os.listdir(carpeta)):
        if not fichero.endswith(".json"):
            continue
        with open(os.path.join(carpeta, fichero), encoding="utf-8") as f:
            datos = json.load(f)
        items.append({"id": fichero[:-5], **datos})
    return items


def _id_valido(id_):
    if not re.fullmatch(r"[A-Za-z0-9_\-]+", id_ or ""):
        raise ValueError("Identificador de correo no válido.")
    return id_


def leer_de_bandeja(codigo, nombre_edificio, id_):
    """(contenido, datos) de un CSV de la bandeja."""
    carpeta = _carpeta_bandeja(codigo, nombre_edificio)
    id_ = _id_valido(id_)
    ruta_csv, ruta_json = os.path.join(carpeta, id_ + ".csv"), os.path.join(carpeta, id_ + ".json")
    if not (os.path.exists(ruta_csv) and os.path.exists(ruta_json)):
        raise ValueError("Ese CSV ya no está en la bandeja.")
    with open(ruta_csv, "rb") as f:
        contenido = f.read()
    with open(ruta_json, encoding="utf-8") as f:
        return contenido, json.load(f)


def retirar_de_bandeja(codigo, nombre_edificio, id_, destino):
    """Saca un CSV de la bandeja pendiente: `destino` es 'importados' o 'descartados' (se conserva el archivo)."""
    if destino not in ("importados", "descartados"):
        raise ValueError("Destino no válido.")
    id_ = _id_valido(id_)
    origen = _carpeta_bandeja(codigo, nombre_edificio)
    final = _carpeta_bandeja(codigo, nombre_edificio, destino)
    for extension in (".csv", ".json"):
        ruta = os.path.join(origen, id_ + extension)
        if os.path.exists(ruta):
            os.replace(ruta, os.path.join(final, id_ + extension))


# ---------------------------------------------------------------------------
# Registro de correos ya procesados
# ---------------------------------------------------------------------------

def _ruta_vistos():
    os.makedirs(config.CARPETA_BASE, exist_ok=True)
    return os.path.join(config.CARPETA_BASE, "_correos_vistos.json")


def _cargar_vistos():
    try:
        with open(_ruta_vistos(), encoding="utf-8") as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError):
        return {}


def _guardar_vistos(vistos):
    if len(vistos) > MAX_VISTOS:
        recientes = sorted(vistos.items(), key=lambda kv: kv[1])[-MAX_VISTOS:]
        vistos = dict(recientes)
    with open(_ruta_vistos(), "w", encoding="utf-8") as f:
        json.dump(vistos, f)


# ---------------------------------------------------------------------------
# Lectura del buzón (red)
# ---------------------------------------------------------------------------

def _abrir_imap(cfg):
    conexion = imaplib.IMAP4_SSL(cfg["servidor"], cfg["puerto"], timeout=60)
    conexion.login(cfg["usuario"], cfg["clave"])
    return conexion


def _fecha_imap(fecha):
    """Fecha en el formato de IMAP (3-Mar-2026), sin depender del idioma del sistema."""
    return f"{fecha.day}-{MESES_EN[fecha.month - 1]}-{fecha.year}"


def _contenido_fetch(respuesta):
    for trozo in respuesta:
        if isinstance(trozo, tuple):
            return trozo[1]
    return b""


def revisar_buzon(abrir_conexion=None):
    """Lee el buzón, deja en la bandeja los CSV de los correos que coinciden con alguna regla y devuelve
    {'revisados', 'nuevos', 'detalle': [...]}. `abrir_conexion` permite probarlo sin red."""
    cfg = configuracion()
    if cfg is None:
        raise ValueError(
            "El correo no está configurado. Define ENERGIA_IMAP_SERVIDOR, ENERGIA_IMAP_USUARIO y ENERGIA_IMAP_CLAVE "
            "en el equipo donde corre el servidor y reinícialo.")

    with _cerrojo:
        try:
            resultado = _revisar(cfg, abrir_conexion or _abrir_imap)
            _estado.update(ultima_revision=datetime.now().isoformat(timespec="seconds"), nuevos=resultado["nuevos"], error=None)
            return resultado
        except Exception as error:
            _estado.update(ultima_revision=datetime.now().isoformat(timespec="seconds"), nuevos=0, error=str(error))
            raise


def _revisar(cfg, abrir_conexion):
    edificios = edificios_con_regla()
    resultado = {"revisados": 0, "nuevos": 0, "detalle": []}
    if not edificios:
        return resultado

    vistos = _cargar_vistos()
    conexion = abrir_conexion(cfg)
    try:
        conexion.select(cfg["carpeta"], readonly=True)
        desde = _fecha_imap(datetime.now() - timedelta(days=cfg["dias"]))
        _, datos = conexion.search(None, "SINCE", desde)
        for numero in (datos[0] or b"").split():
            resultado["revisados"] += 1
            _, resp = conexion.fetch(numero, "(BODY.PEEK[HEADER.FIELDS (MESSAGE-ID SUBJECT FROM)])")
            cabeceras = _cabeceras(_contenido_fetch(resp))
            clave = cabeceras["message_id"] or f"{cabeceras['remitente']}|{cabeceras['asunto']}"
            if clave in vistos:
                continue
            destinos = [e for e in edificios if coincide(cabeceras["asunto"], cabeceras["remitente"],
                                                         {"asunto": e.get("correo_asunto"), "remitente": e.get("correo_remitente")})]
            if not destinos:
                continue

            _, resp = conexion.fetch(numero, "(BODY.PEEK[])")
            adjuntos, recibido = adjuntos_csv(_contenido_fetch(resp))
            for edificio in destinos:
                for nombre, contenido in adjuntos:
                    anio, mes = proponer_mes(nombre, recibido)
                    _guardar_en_bandeja(edificio, nombre, contenido, {
                        "asunto": cabeceras["asunto"], "remitente": cabeceras["remitente"],
                        "recibido": recibido.isoformat(timespec="seconds"), "anio": anio, "mes": mes,
                    })
                    resultado["nuevos"] += 1
                    resultado["detalle"].append({"codigo": edificio["codigo_proyecto"], "archivo": nombre, "anio": anio, "mes": mes})
            vistos[clave] = datetime.now().isoformat(timespec="seconds")
    finally:
        try:
            conexion.logout()
        except Exception:
            pass
        _guardar_vistos(vistos)
    return resultado


# ---------------------------------------------------------------------------
# Revisión automática en segundo plano
# ---------------------------------------------------------------------------

def iniciar_vigilante():
    """Si hay buzón configurado y ENERGIA_IMAP_MINUTOS > 0, revisa el correo cada tantos minutos en un hilo.
    Devuelve el evento que lo para (o None si no arranca)."""
    minutos = minutos_de_revision()
    if configuracion() is None or minutos <= 0:
        return None
    parar = threading.Event()

    def bucle():
        while not parar.is_set():
            try:
                revisar_buzon()
            except Exception as error:  # queda en el estado y en la consola; se reintenta en el siguiente ciclo
                print(f"[correo] {error}")
            parar.wait(minutos * 60)

    threading.Thread(target=bucle, name="vigilante-correo", daemon=True).start()
    return parar
