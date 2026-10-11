"""Acceso con usuario y contraseña.

Solo se exige si hay usuarios definidos en los secretos de Streamlit (tabla [usuarios]). Sin
usuarios (uso local) la aplicación se abre directamente, como hasta ahora.

Las contraseñas no se guardan: en los secretos solo va su huella (PBKDF2-SHA256).
Para crear la línea de un usuario nuevo:  python -m energia.auth
"""
import getpass
import hashlib
import hmac
import secrets
import sys
import time

import streamlit as st

from energia.secretos import leer_secreto
from energia.ui import aplicar_estilos, mostrar_cabecera_app

ITERACIONES = 240_000
MAX_FALLOS = 5  # intentos fallidos permitidos por usuario...
VENTANA_SEGUNDOS = 600  # ...dentro de esta ventana de tiempo
LONGITUD_MINIMA = 10
MAX_USUARIOS_REGISTRADOS = 1000

_fallos = {}  # usuario -> instantes de los intentos fallidos (compartido por todas las sesiones)
_HUELLA_FALSA = None


def crear_hash(password, sal=None):
    sal = sal if sal is not None else secrets.token_bytes(16)
    huella = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), sal, ITERACIONES)
    return f"pbkdf2_sha256${ITERACIONES}${sal.hex()}${huella.hex()}"


def verificar(password, almacenado):
    try:
        algoritmo, iteraciones, sal, huella = str(almacenado).split("$")
        if algoritmo != "pbkdf2_sha256":
            return False
        calculada = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), bytes.fromhex(sal), int(iteraciones))
    except (ValueError, TypeError):
        return False
    return hmac.compare_digest(calculada.hex(), huella)


def _normalizar(usuario):
    return str(usuario).strip().lower()


def _bloqueado(clave, ahora):
    intentos = [t for t in _fallos.get(clave, []) if ahora - t < VENTANA_SEGUNDOS]
    if intentos:
        _fallos[clave] = intentos
    else:
        _fallos.pop(clave, None)
    return len(intentos) >= MAX_FALLOS


def _registrar_fallo(clave, ahora):
    if clave not in _fallos and len(_fallos) >= MAX_USUARIOS_REGISTRADOS:
        _fallos.pop(next(iter(_fallos)))  # evita que el registro crezca sin límite
    _fallos.setdefault(clave, []).append(ahora)


def comprobar_acceso(usuario, password, usuarios, ahora=None):
    """Devuelve (acceso_permitido, mensaje). `usuarios` es {nombre_en_minusculas: huella}."""
    global _HUELLA_FALSA
    ahora = time.monotonic() if ahora is None else ahora
    clave = _normalizar(usuario)

    if _bloqueado(clave, ahora):
        return False, "Demasiados intentos fallidos. Espera unos minutos antes de volver a probar."

    almacenado = usuarios.get(clave)
    if almacenado is None:
        # Se calcula igualmente una huella para que no se note si el usuario existe o no.
        if _HUELLA_FALSA is None:
            _HUELLA_FALSA = crear_hash("sin-usuario")
        verificar(password, _HUELLA_FALSA)
        _registrar_fallo(clave, ahora)
        return False, "Usuario o contraseña incorrectos."

    if verificar(password, almacenado):
        _fallos.pop(clave, None)
        return True, ""

    _registrar_fallo(clave, ahora)
    return False, "Usuario o contraseña incorrectos."


def cargar_usuarios():
    tabla = leer_secreto("usuarios")
    if not tabla:
        return {}
    try:
        return {_normalizar(nombre): str(huella) for nombre, huella in dict(tabla).items()}
    except (TypeError, ValueError):
        return {}


def requerir_login():
    """Muestra el formulario de acceso si hay usuarios configurados.
    Devuelve True cuando se puede mostrar la aplicación."""
    usuarios = cargar_usuarios()
    if not usuarios:
        return True

    if st.session_state.get("usuario_autenticado") in usuarios:
        return True

    aplicar_estilos()
    mostrar_cabecera_app()

    _, centro, _ = st.columns([1, 2, 1])
    with centro:
        with st.form("acceso"):
            st.subheader("Acceso")
            usuario = st.text_input("Usuario")
            password = st.text_input("Contraseña", type="password")
            entrar = st.form_submit_button("Entrar")

        if entrar:
            permitido, mensaje = comprobar_acceso(usuario, password, usuarios)
            if permitido:
                st.session_state["usuario_autenticado"] = _normalizar(usuario)
                st.rerun()
            st.error(mensaje)

    return False


def mostrar_sesion_en_barra_lateral():
    """Muestra quién ha entrado y el botón de salir (solo si el acceso está activado)."""
    usuario = st.session_state.get("usuario_autenticado")
    if not usuario:
        return

    st.sidebar.divider()
    st.sidebar.caption(f"Usuario: {usuario}")
    if st.sidebar.button("Cerrar sesión"):
        st.session_state.pop("usuario_autenticado", None)
        st.rerun()


def _crear_usuario_por_consola():
    print("Crear un usuario para la aplicación\n")
    nombre = _normalizar(input("Nombre de usuario (sin espacios): "))
    if not nombre or " " in nombre or "=" in nombre or '"' in nombre:
        print("Nombre no válido: usa letras y números, sin espacios.")
        return 1

    password = getpass.getpass(f"Contraseña (mínimo {LONGITUD_MINIMA} caracteres, no se verá al escribir): ")
    if len(password) < LONGITUD_MINIMA:
        print(f"La contraseña es demasiado corta (mínimo {LONGITUD_MINIMA} caracteres).")
        return 1
    if password != getpass.getpass("Repite la contraseña: "):
        print("Las contraseñas no coinciden.")
        return 1

    print("\nAñade esta línea en los Secrets de la app, debajo de [usuarios]:\n")
    print(f'{nombre} = "{crear_hash(password)}"')
    print("\nLa contraseña no se guarda en ningún sitio: solo va su huella.")
    return 0


if __name__ == "__main__":
    sys.exit(_crear_usuario_por_consola())
