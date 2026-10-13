"""Buzón de correo: propuesta de mes, bandeja por edificio e importación, con un buzón IMAP falso (sin red)."""
import os
from datetime import datetime
from email.message import EmailMessage

import pytest

from energia import buzon, servicios
from energia.db import guardar_correo_edificio
from energia.demo import CARPETA_DEMO, CODIGO_DEMO


def leer_demo(nombre):
    with open(os.path.join(CARPETA_DEMO, nombre), "rb") as f:
        return f.read()


def correo(asunto, remitente="bms@cliente.com", adjuntos=(), id_mensaje=None, fecha="Thu, 02 Apr 2026 09:00:00 +0200"):
    mensaje = EmailMessage()
    mensaje["Subject"] = asunto
    mensaje["From"] = remitente
    mensaje["To"] = "buzon@empresa.com"
    mensaje["Date"] = fecha
    mensaje["Message-ID"] = id_mensaje or f"<{abs(hash((asunto, tuple(n for n, _ in adjuntos))))}@cliente.com>"
    mensaje.set_content("Se adjunta la monitorización.")
    for nombre, contenido in adjuntos:
        mensaje.add_attachment(contenido, maintype="text", subtype="csv", filename=nombre)
    return mensaje.as_bytes()


class BuzonFalso:
    """Imita lo mínimo de imaplib.IMAP4_SSL que usa buzon.py."""

    def __init__(self, mensajes):
        self.mensajes = {str(i + 1).encode(): m for i, m in enumerate(mensajes)}
        self.seleccion = None
        self.completos = 0
        self.cerrado = False

    def select(self, carpeta, readonly=False):
        self.seleccion = (carpeta, readonly)
        return "OK", [b"1"]

    def search(self, _charset, *criterios):
        self.criterios = criterios
        return "OK", [b" ".join(self.mensajes)]

    def fetch(self, numero, partes):
        crudo = self.mensajes[numero]
        if "HEADER" in partes:
            crudo = crudo.split(b"\n\n", 1)[0] + b"\n\n"
        else:
            self.completos += 1
        return "OK", [(b"1 (BODY[] {%d}" % len(crudo), crudo), b")"]

    def logout(self):
        self.cerrado = True


@pytest.fixture
def con_buzon(db_demo, monkeypatch):
    monkeypatch.setenv("ENERGIA_IMAP_SERVIDOR", "imap.prueba.test")
    monkeypatch.setenv("ENERGIA_IMAP_USUARIO", "buzon@empresa.com")
    monkeypatch.setenv("ENERGIA_IMAP_CLAVE", "no-es-una-clave-real")
    guardar_correo_edificio(CODIGO_DEMO, "CSV monitorización", "")
    return db_demo


# ------------------------------------------------------------------ propuesta de mes

@pytest.mark.parametrize("nombre, esperado", [
    ("bms_2026_03.csv", (2026, 3)),
    ("consumos-2026-11-edificio.csv", (2026, 11)),
    ("03-2026 consumos.csv", (2026, 3)),
    ("Monitorizacion marzo 2026.csv", (2026, 3)),
    ("export_Septiembre_2025.csv", (2025, 9)),
    ("datos 20261203.csv", None),  # sin separador no se inventa un mes: cae a la fecha del correo
])
def test_proponer_mes_por_nombre(nombre, esperado):
    recibido = datetime(2026, 4, 2)
    assert buzon.proponer_mes(nombre, recibido) == (esperado or (2026, 3))


def test_proponer_mes_sin_pistas_usa_el_mes_anterior_al_correo():
    assert buzon.proponer_mes("export.csv", datetime(2026, 4, 2)) == (2026, 3)
    assert buzon.proponer_mes("export.csv", datetime(2026, 1, 5)) == (2025, 12)


# ------------------------------------------------------------------ configuración

def test_sin_variables_el_buzon_no_esta_configurado(monkeypatch):
    for variable in ("ENERGIA_IMAP_SERVIDOR", "ENERGIA_IMAP_USUARIO", "ENERGIA_IMAP_CLAVE"):
        monkeypatch.delenv(variable, raising=False)
    assert buzon.configuracion() is None
    assert buzon.estado()["configurado"] is False
    with pytest.raises(ValueError, match="no está configurado"):
        buzon.revisar_buzon()


def test_la_configuracion_se_lee_del_entorno(con_buzon):
    cfg = buzon.configuracion()
    assert (cfg["servidor"], cfg["puerto"], cfg["carpeta"], cfg["dias"]) == ("imap.prueba.test", 993, "INBOX", 45)
    assert "clave" not in buzon.estado()


# ------------------------------------------------------------------ revisión del buzón

def mensajes_de_prueba():
    csv = leer_demo("bms_2026_03_3.csv")
    return [
        correo("CSV monitorización edificio demo", adjuntos=[("bms_2026_03.csv", csv)]),
        correo("Factura de abril", adjuntos=[("factura.csv", csv)]),   # no coincide con la regla
        correo("RE: csv MONITORIZACION", adjuntos=[]),                  # coincide, pero sin CSV
    ]


def test_revisar_deja_en_la_bandeja_solo_los_csv_que_coinciden(con_buzon):
    falso = BuzonFalso(mensajes_de_prueba())
    resultado = buzon.revisar_buzon(lambda cfg: falso)

    assert resultado["revisados"] == 3
    assert resultado["nuevos"] == 1
    assert resultado["detalle"] == [{"codigo": CODIGO_DEMO, "archivo": "bms_2026_03.csv", "anio": 2026, "mes": 3}]
    assert falso.seleccion == ("INBOX", True)          # solo lectura: no marca nada como leído
    assert falso.completos == 2                         # el correo de la factura ni se descarga
    assert falso.cerrado

    items = servicios.bandeja(CODIGO_DEMO)["items"]
    assert len(items) == 1
    assert items[0]["archivo"] == "bms_2026_03.csv"
    assert items[0]["asunto"] == "CSV monitorización edificio demo"
    assert (items[0]["anio"], items[0]["mes"]) == (2026, 3)
    assert buzon.estado()["nuevos"] == 1 and buzon.estado()["error"] is None


def test_un_correo_ya_procesado_no_se_vuelve_a_guardar(con_buzon):
    buzon.revisar_buzon(lambda cfg: BuzonFalso(mensajes_de_prueba()))
    segunda = buzon.revisar_buzon(lambda cfg: BuzonFalso(mensajes_de_prueba()))
    assert segunda["nuevos"] == 0
    assert len(servicios.bandeja(CODIGO_DEMO)["items"]) == 1


def test_sin_reglas_guardadas_no_se_recoge_nada(db_demo, monkeypatch):
    monkeypatch.setenv("ENERGIA_IMAP_SERVIDOR", "imap.prueba.test")
    monkeypatch.setenv("ENERGIA_IMAP_USUARIO", "buzon@empresa.com")
    monkeypatch.setenv("ENERGIA_IMAP_CLAVE", "no-es-una-clave-real")
    falso = BuzonFalso(mensajes_de_prueba())
    assert buzon.revisar_buzon(lambda cfg: falso)["nuevos"] == 0
    assert falso.completos == 0


def test_el_remitente_de_la_regla_tambien_filtra(con_buzon):
    guardar_correo_edificio(CODIGO_DEMO, "CSV monitorización", "@solo-este.com")
    falso = BuzonFalso(mensajes_de_prueba())  # remitente bms@cliente.com
    assert buzon.revisar_buzon(lambda cfg: falso)["nuevos"] == 0


def test_un_fallo_de_conexion_queda_en_el_estado(con_buzon):
    def conexion_rota(cfg):
        raise OSError("sin red")

    with pytest.raises(OSError):
        buzon.revisar_buzon(conexion_rota)
    assert buzon.estado()["error"] == "sin red"


# ------------------------------------------------------------------ importar y descartar

def test_importar_de_la_bandeja_crea_el_bms_y_vacia_la_bandeja(con_buzon):
    buzon.revisar_buzon(lambda cfg: BuzonFalso(mensajes_de_prueba()))
    item = servicios.bandeja(CODIGO_DEMO)["items"][0]
    antes = len(servicios.bms(CODIGO_DEMO)["bms"])

    resultado = servicios.importar_de_bandeja(CODIGO_DEMO, item["id"], 2026, 3)

    assert resultado["importados"] == 1
    assert len(servicios.bms(CODIGO_DEMO)["bms"]) == antes + 1
    assert servicios.bandeja(CODIGO_DEMO)["items"] == []
    with pytest.raises(ValueError, match="ya no está"):
        servicios.importar_de_bandeja(CODIGO_DEMO, item["id"], 2026, 3)


def test_un_csv_invalido_se_queda_en_la_bandeja(con_buzon):
    falso = BuzonFalso([correo("CSV monitorización", adjuntos=[("roto.csv", b"esto,no,es\nun,csv,de bms\n")])])
    buzon.revisar_buzon(lambda cfg: falso)
    item = servicios.bandeja(CODIGO_DEMO)["items"][0]

    resultado = servicios.importar_de_bandeja(CODIGO_DEMO, item["id"], 2026, 3)

    assert resultado["importados"] == 0 and not resultado["resultados"][0]["ok"]
    assert len(servicios.bandeja(CODIGO_DEMO)["items"]) == 1


def test_descartar_saca_el_csv_de_la_bandeja_sin_importarlo(con_buzon):
    buzon.revisar_buzon(lambda cfg: BuzonFalso(mensajes_de_prueba()))
    item = servicios.bandeja(CODIGO_DEMO)["items"][0]
    antes = len(servicios.bms(CODIGO_DEMO)["bms"])

    servicios.descartar_de_bandeja(CODIGO_DEMO, item["id"])

    assert servicios.bandeja(CODIGO_DEMO)["items"] == []
    assert len(servicios.bms(CODIGO_DEMO)["bms"]) == antes


def test_el_identificador_no_permite_salir_de_la_bandeja(con_buzon):
    for malo in ("../../database", "..\\x", "a/b", ""):
        with pytest.raises(ValueError):
            servicios.importar_de_bandeja(CODIGO_DEMO, malo, 2026, 3)
        with pytest.raises(ValueError):
            servicios.descartar_de_bandeja(CODIGO_DEMO, malo)
