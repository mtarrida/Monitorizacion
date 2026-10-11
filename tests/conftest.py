import os

import pytest

from energia import config, db
from energia.db import inicializar_db
from energia.demo import crear_demo


class ArchivoFalso:
    """Imita el archivo subido de Streamlit (los lectores solo usan getvalue)."""

    def __init__(self, contenido, nombre="archivo"):
        self.contenido = contenido.encode("utf-8") if isinstance(contenido, str) else contenido
        self.name = nombre

    def getvalue(self):
        return self.contenido


def _vaciar_postgres(url):
    import psycopg

    with psycopg.connect(url, autocommit=True) as conn:
        conn.execute("DROP SCHEMA public CASCADE")
        conn.execute("CREATE SCHEMA public")


@pytest.fixture(params=["sqlite", "postgres"])
def db_temporal(request, tmp_path, monkeypatch):
    """Base de datos vacía, aislada de la real. Se prueba con SQLite y, si hay una base
    PostgreSQL de pruebas (variable TEST_DATABASE_URL), también con PostgreSQL."""
    monkeypatch.setattr(config, "CARPETA_BASE", str(tmp_path / "datos"))

    if request.param == "postgres":
        url = os.environ.get("TEST_DATABASE_URL")
        if not url:
            pytest.skip("Define TEST_DATABASE_URL para probar con PostgreSQL")
        monkeypatch.setenv("DATABASE_URL", url)
        db._inicializadas.clear()
        _vaciar_postgres(url)
    else:
        monkeypatch.delenv("DATABASE_URL", raising=False)
        monkeypatch.setattr(config, "DB", str(tmp_path / "test.db"))

    inicializar_db()
    return tmp_path


@pytest.fixture
def db_demo(db_temporal):
    """Base de datos temporal con el edificio demo (simulación + 5 importaciones BMS)."""
    crear_demo()
    return db_temporal
