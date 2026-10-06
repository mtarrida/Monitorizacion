"""Configuración y constantes de la aplicación."""
import os
from datetime import date

# La base de datos y la carpeta de archivos se pueden cambiar con variables de entorno
# (útil para pruebas y para el despliegue online). Por defecto, igual que antes.
DB = os.environ.get("ENERGIA_DB", "database.db")
CARPETA_BASE = os.environ.get("ENERGIA_DATOS", "datos_edificios")
LOGO_PATH = os.path.join("assets", "pgi_logo.png")

COLOR_CORPORATIVO = "#AB1735"
COLOR_CORPORATIVO_OSCURO = "#8C1E35"
COLOR_GRIS_FONDO = "#F6F7F8"
COLOR_GRIS_BORDE = "#E4E6EA"

ANIO_ACTUAL = date.today().year

MESES = {
    1: "Enero",
    2: "Febrero",
    3: "Marzo",
    4: "Abril",
    5: "Mayo",
    6: "Junio",
    7: "Julio",
    8: "Agosto",
    9: "Septiembre",
    10: "Octubre",
    11: "Noviembre",
    12: "Diciembre",
}

TIPOS_EDIFICIO = [
    "Oficinas",
    "Hotel",
    "Residencial",
    "Hospitalario",
    "Docente",
    "Comercial",
    "Industrial",
    "Otro",
]

UNIDADES_REFERENCIA = ["m²", "habitaciones", "puestos de trabajo", "camas", "usuarios", "otro"]
