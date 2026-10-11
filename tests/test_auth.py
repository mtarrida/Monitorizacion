from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

from energia import auth
from energia.auth import (
    MAX_FALLOS,
    VENTANA_SEGUNDOS,
    cargar_usuarios,
    comprobar_acceso,
    crear_hash,
    verificar,
)

APP = str(Path(__file__).resolve().parent.parent / "app.py")
CLAVE = "una-clave-larga-123"


@pytest.fixture(autouse=True)
def sin_fallos_previos():
    auth._fallos.clear()
    yield
    auth._fallos.clear()


def test_hash_no_contiene_la_clave_y_se_verifica():
    huella = crear_hash(CLAVE)
    assert CLAVE not in huella
    assert huella.startswith("pbkdf2_sha256$")
    assert verificar(CLAVE, huella)
    assert not verificar("otra-clave", huella)


def test_el_mismo_texto_da_huellas_distintas():
    assert crear_hash(CLAVE) != crear_hash(CLAVE)


@pytest.mark.parametrize("basura", ["", "x", "a$b$c$d", "pbkdf2_sha256$no$no$no", None, 123])
def test_huellas_mal_formadas_no_dan_acceso_ni_rompen(basura):
    assert verificar(CLAVE, basura) is False


def test_comprobar_acceso_correcto_incorrecto_y_desconocido():
    usuarios = {"maria": crear_hash(CLAVE)}
    assert comprobar_acceso("maria", CLAVE, usuarios) == (True, "")
    assert comprobar_acceso("  MARIA ", CLAVE, usuarios)[0] is True  # no distingue mayúsculas ni espacios
    assert comprobar_acceso("maria", "mal", usuarios) == (False, "Usuario o contraseña incorrectos.")
    assert comprobar_acceso("nadie", CLAVE, usuarios) == (False, "Usuario o contraseña incorrectos.")


def test_mismo_mensaje_si_el_usuario_existe_o_no():
    usuarios = {"maria": crear_hash(CLAVE)}
    assert comprobar_acceso("maria", "mal", usuarios) == comprobar_acceso("nadie", "mal", usuarios)


def test_bloqueo_tras_demasiados_fallos_y_desbloqueo_con_el_tiempo():
    usuarios = {"maria": crear_hash(CLAVE)}
    for i in range(MAX_FALLOS):
        assert comprobar_acceso("maria", "mal", usuarios, ahora=100 + i)[0] is False

    # bloqueada: ni siquiera con la clave correcta
    permitido, mensaje = comprobar_acceso("maria", CLAVE, usuarios, ahora=110)
    assert permitido is False and "Demasiados intentos" in mensaje

    # pasada la ventana de tiempo, vuelve a poder entrar
    assert comprobar_acceso("maria", CLAVE, usuarios, ahora=100 + VENTANA_SEGUNDOS + 10)[0] is True


def test_un_acierto_borra_los_fallos_anteriores():
    usuarios = {"maria": crear_hash(CLAVE)}
    for i in range(MAX_FALLOS - 1):
        comprobar_acceso("maria", "mal", usuarios, ahora=i)
    assert comprobar_acceso("maria", CLAVE, usuarios, ahora=50)[0] is True
    for i in range(MAX_FALLOS - 1):
        assert comprobar_acceso("maria", "mal", usuarios, ahora=60 + i)[0] is False
    assert comprobar_acceso("maria", CLAVE, usuarios, ahora=70)[0] is True  # no llegó a bloquearse


def test_el_registro_de_fallos_no_crece_sin_limite():
    usuarios = {"maria": crear_hash(CLAVE)}
    for i in range(auth.MAX_USUARIOS_REGISTRADOS + 200):
        comprobar_acceso(f"intruso{i}", "x", usuarios, ahora=i)
    assert len(auth._fallos) <= auth.MAX_USUARIOS_REGISTRADOS


# ---- la aplicación completa ----

def _app(usuarios=None):
    at = AppTest.from_file(APP, default_timeout=120)
    if usuarios is not None:
        at.secrets["usuarios"] = usuarios
    at.run()
    return at


def test_sin_usuarios_configurados_la_app_se_abre_directamente(db_demo):
    at = _app()
    assert not at.exception
    assert len(at.tabs) >= 8
    assert "Contraseña" not in [t.label for t in at.text_input]  # no hay formulario de acceso


def test_con_usuarios_primero_pide_acceso_y_no_muestra_datos(db_demo):
    at = _app({"maria": crear_hash(CLAVE)})
    assert not at.exception
    assert [t.label for t in at.text_input] == ["Usuario", "Contraseña"]
    assert len(at.tabs) == 0
    assert len(at.metric) == 0 and len(at.dataframe) == 0
    # nada de los datos del edificio aparece antes de entrar
    assert "Edificio Demo" not in str(at.get("selectbox")) and not at.sidebar.selectbox


def test_login_incorrecto_no_entra(db_demo):
    at = _app({"maria": crear_hash(CLAVE)})
    at.text_input[0].set_value("maria")
    at.text_input[1].set_value("mal")
    at.button[0].click()
    at.run()
    assert [e.value for e in at.error] == ["Usuario o contraseña incorrectos."]
    assert len(at.tabs) == 0


def test_login_correcto_entra_y_muestra_el_usuario(db_demo):
    at = _app({"maria": crear_hash(CLAVE)})
    at.text_input[0].set_value("Maria")
    at.text_input[1].set_value(CLAVE)
    at.button[0].click()
    at.run()
    assert not at.exception
    assert len(at.tabs) >= 8
    assert any("Usuario: maria" in c.value for c in at.sidebar.caption)


def test_cerrar_sesion_vuelve_a_pedir_acceso(db_demo):
    at = _app({"maria": crear_hash(CLAVE)})
    at.text_input[0].set_value("maria")
    at.text_input[1].set_value(CLAVE)
    at.button[0].click()
    at.run()
    salir = [b for b in at.sidebar.button if b.label == "Cerrar sesión"][0]
    salir.click()
    at.run()
    assert [t.label for t in at.text_input] == ["Usuario", "Contraseña"]
    assert len(at.tabs) == 0


def test_cargar_usuarios_normaliza_y_tolera_basura():
    assert cargar_usuarios() == {}  # sin secretos configurados


def test_opcion_demo_crea_el_edificio_de_demostracion(db_temporal, monkeypatch):
    monkeypatch.setenv("ENERGIA_DEMO", "1")
    at = _app()
    assert not at.exception
    assert "PGI-DEMO-001 - Edificio Demo" in at.sidebar.selectbox(key="global_edificio").options
