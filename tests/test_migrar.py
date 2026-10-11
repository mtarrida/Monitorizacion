import os

import pytest

from energia import config, db
from energia.analisis import comparativa_mensual
from energia.db import cargar_edificios, cargar_simulacion_activa, crear_consumo_bms, guardar_edificio
from energia.demo import crear_demo
from energia.migrar import main, migrar
from tests.conftest import _vaciar_postgres


@pytest.fixture
def origen_sqlite_y_destino_pg(tmp_path, monkeypatch):
    """Una base SQLite con la demo (origen) y una base PostgreSQL vacía (destino)."""
    url = os.environ.get("TEST_DATABASE_URL")
    if not url:
        pytest.skip("Define TEST_DATABASE_URL para probar con PostgreSQL")

    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.setattr(config, "DB", str(tmp_path / "origen.db"))
    crear_demo()

    monkeypatch.setenv("DATABASE_URL", url)
    db._inicializadas.clear()
    _vaciar_postgres(url)
    return str(tmp_path / "origen.db")


def test_migrar_copia_todo_y_da_los_mismos_resultados(origen_sqlite_y_destino_pg):
    copiadas = migrar(origen_sqlite_y_destino_pg)

    assert copiadas == {
        "edificios": 1,
        "simulaciones": 1,
        "simulacion_detalle": 72,
        "consumos_bms": 5,
        "consumo_bms_detalle": 70,
    }
    assert list(cargar_edificios(True)["codigo_proyecto"]) == ["PGI-DEMO-001"]

    sim_id = int(cargar_simulacion_activa("PGI-DEMO-001").iloc[0]["id"])
    comp = comparativa_mensual("PGI-DEMO-001", sim_id, 2026, 3)
    assert comp["real_kwh"].sum() == pytest.approx(66887.70, abs=0.01)
    assert comp["simulado_kwh"].sum() == pytest.approx(37069.03, abs=0.01)


def test_migrar_deja_el_contador_de_ids_al_dia(origen_sqlite_y_destino_pg):
    migrar(origen_sqlite_y_destino_pg)
    # Con los ids 1..5 ya copiados, la siguiente importación debe ser la 6 (y no chocar)
    assert crear_consumo_bms("PGI-DEMO-001", 2026, 4, "BMS 2026-04", "") == 6


def test_migrar_se_niega_si_el_destino_ya_tiene_datos(origen_sqlite_y_destino_pg):
    migrar(origen_sqlite_y_destino_pg)
    with pytest.raises(ValueError, match="ya tiene datos"):
        migrar(origen_sqlite_y_destino_pg)
    assert len(cargar_edificios(True)) == 1  # no se duplicó nada


def test_migrar_no_pisa_lo_que_ya_hay_en_destino(origen_sqlite_y_destino_pg):
    db.inicializar_db()
    guardar_edificio({
        "codigo_proyecto": "OTRO", "nombre": "Otro", "cliente": "", "ubicacion": "", "uso": "Oficinas",
        "superficie_m2": 1.0, "sistema_climatizacion": "", "observaciones": "",
    })
    with pytest.raises(ValueError):
        migrar(origen_sqlite_y_destino_pg)
    assert list(cargar_edificios(True)["codigo_proyecto"]) == ["OTRO"]


def test_migrar_sin_origen(origen_sqlite_y_destino_pg, tmp_path):
    with pytest.raises(FileNotFoundError):
        migrar(str(tmp_path / "no_existe.db"))


def test_migrar_sin_postgres_configurado(tmp_path, monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    with pytest.raises(ValueError, match="DATABASE_URL"):
        migrar(str(tmp_path / "x.db"))


def test_main_informa_sin_romper(origen_sqlite_y_destino_pg, capsys):
    assert main([origen_sqlite_y_destino_pg]) == 0
    salida = capsys.readouterr().out
    assert "simulacion_detalle: 72 filas" in salida

    assert main([origen_sqlite_y_destino_pg]) == 1  # segunda vez: destino con datos
    assert "No se ha copiado nada" in capsys.readouterr().out
