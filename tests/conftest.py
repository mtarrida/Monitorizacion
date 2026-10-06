import pytest

from energia import config
from energia.db import inicializar_db
from energia.demo import crear_demo


class ArchivoFalso:
    """Imita el archivo subido de Streamlit (los lectores solo usan getvalue)."""

    def __init__(self, contenido, nombre="archivo"):
        self.contenido = contenido.encode("utf-8") if isinstance(contenido, str) else contenido
        self.name = nombre

    def getvalue(self):
        return self.contenido


@pytest.fixture
def db_temporal(tmp_path, monkeypatch):
    """Base de datos vacía y carpeta de datos temporales, aisladas de la real."""
    monkeypatch.setattr(config, "DB", str(tmp_path / "test.db"))
    monkeypatch.setattr(config, "CARPETA_BASE", str(tmp_path / "datos"))
    inicializar_db()
    return tmp_path


@pytest.fixture
def db_demo(db_temporal):
    """Base de datos temporal con el edificio demo (simulación + 5 importaciones BMS)."""
    crear_demo()
    return db_temporal
