"""Pruebas de la capa de servicios de la interfaz web (sin servidor)."""
import json
import os

import pytest

from energia import servicios
from energia.demo import CODIGO_DEMO

CARPETA_DEMO = os.path.join(os.path.dirname(__file__), "..", "ejemplos", "demo")


def _leer_demo(nombre):
    with open(os.path.join(CARPETA_DEMO, nombre), "rb") as f:
        return f.read()


def _json_estricto(valor):
    """Lo que devuelve un servicio tiene que poder enviarse como JSON sin NaN."""
    json.dumps(valor, allow_nan=False)


def test_sin_edificios_los_servicios_devuelven_aviso(db_temporal):
    for resultado in (
        servicios.panel("X", 2026, 1),
        servicios.comparativa_mes("X", 2026, 1),
        servicios.comparativa_acumulada("X", 2026),
        servicios.informe("X", 2026, 1),
        servicios.costes("X", 2026, 0.18, 0.07),
        servicios.co2("X", 2026, 0.18, 0.20),
        servicios.base_comparable(2026),
    ):
        assert "aviso" in resultado


def test_panel_con_datos_demo(db_demo):
    p = servicios.panel(CODIGO_DEMO, 2026, 3)
    _json_estricto(p)
    assert p["kpis"]["meses_bms"] == 3
    assert p["kpis"]["consumo_acumulado_kwh"] > 0
    assert p["simulacion_activa"]
    assert p["fig_consumo"] is not None


def test_comparativa_mensual_y_acumulada(db_demo):
    mes = servicios.comparativa_mes(CODIGO_DEMO, 2026, 3)
    _json_estricto(mes)
    assert mes["kpis"]["real_kwh"] > mes["kpis"]["simulado_kwh"] > 0
    assert mes["fig_barras"] and mes["fig_desviacion"] and mes["fig_pareto"]

    acumulada = servicios.comparativa_acumulada(CODIGO_DEMO, 2026)
    _json_estricto(acumulada)
    assert acumulada["kpis"]["meses_bms"] == 3
    assert len(acumulada["tabla_meses"]) == 3
    assert acumulada["kpis"]["proyeccion_anual_kwh"] > 0


def test_comparativa_de_un_mes_sin_bms_devuelve_aviso(db_demo):
    assert "aviso" in servicios.comparativa_mes(CODIGO_DEMO, 2026, 4)
    assert "aviso" in servicios.informe(CODIGO_DEMO, 2026, 4)


def test_base_comparable_y_filtro_por_categoria(db_demo):
    base = servicios.base_comparable(2026)
    _json_estricto(base)
    assert len(base["tabla"]) == 1 and base["figura"] is not None
    assert servicios.base_comparable(2026, ["no existe"])["seleccion"] == base["categorias"]


def test_informe_incluye_el_texto_y_el_nombre_del_archivo(db_demo):
    informe = servicios.informe(CODIGO_DEMO, 2026, 3)
    _json_estricto(informe)
    assert "INFORME MENSUAL ENERGÉTICO" in informe["texto"]
    assert informe["archivo"] == f"informe_{CODIGO_DEMO}_2026_03.txt"
    assert all(abs(a["desviacion_pct"]) > 10 for a in informe["alertas"])


def test_costes_y_co2_dependen_de_los_parametros(db_demo):
    barato = servicios.costes(CODIGO_DEMO, 2026, 0.10, 0.05)
    caro = servicios.costes(CODIGO_DEMO, 2026, 0.20, 0.10)
    _json_estricto(caro)
    assert caro["kpis"]["coste_total_eur"] == pytest.approx(2 * barato["kpis"]["coste_total_eur"])
    assert len(caro["tabla_mes"]) == 3

    emisiones = servicios.co2(CODIGO_DEMO, 2026, 0.18, 0.20)
    _json_estricto(emisiones)
    assert emisiones["kpis"]["co2_acumulado_tn"] > 0


def test_crud_de_edificios(db_demo):
    with pytest.raises(ValueError):
        servicios.crear_edificio({"codigo_proyecto": "", "nombre": ""})
    with pytest.raises(ValueError):
        servicios.crear_edificio({"codigo_proyecto": CODIGO_DEMO, "nombre": "Repetido"})

    nuevo = servicios.crear_edificio({"codigo_proyecto": "t-1", "nombre": "Test", "superficie_m2": "1200"})
    assert nuevo["codigo"] == "T-1" and os.path.isdir(nuevo["carpeta"])

    servicios.editar_edificio("T-1", {"nombre": "Test 2", "superficie_m2": 1500})
    assert any(e["nombre"] == "Test 2" and e["superficie_m2"] == 1500 for e in servicios.lista_edificios(True))

    servicios.cambiar_estado("T-1", "ARCHIVADO")
    assert [e["codigo_proyecto"] for e in servicios.lista_edificios()] == [CODIGO_DEMO]
    with pytest.raises(ValueError):
        servicios.cambiar_estado("T-1", "OTRO")

    with pytest.raises(ValueError):
        servicios.borrar_edificio("T-1", "no es el codigo")
    assert servicios.borrar_edificio("T-1", "t-1")["edificios"] == 1


def test_importar_simulacion_y_bms(db_demo):
    sim = servicios.importar_simulacion(
        CODIGO_DEMO, "Otra", "", 2026, False, "simulacion_demo.dat", _leer_demo("simulacion_demo.dat"))
    assert sim["filas"] > 0
    servicios.activar_simulacion(CODIGO_DEMO, sim["sim_id"])
    activas = [s for s in servicios.simulaciones(CODIGO_DEMO)["simulaciones"] if s["activa"]]
    assert [s["id"] for s in activas] == [sim["sim_id"]]
    with pytest.raises(ValueError):
        servicios.importar_simulacion(CODIGO_DEMO, "x", "", 2026, False, "vacio.dat", b"")

    resultado = servicios.importar_bms(CODIGO_DEMO, 2026, [
        {"mes": 4, "archivo": "abril.csv", "contenido": _leer_demo("bms_2026_01_1.csv"), "nombre": "BMS abril"},
        {"mes": 5, "archivo": "malo.csv", "contenido": b"a,b\n1,2\n"},
    ])
    assert resultado["importados"] == 1
    assert resultado["resultados"][1]["ok"] is False
    assert servicios.comparativa_mes(CODIGO_DEMO, 2026, 4).get("kpis")
    with pytest.raises(ValueError):
        servicios.importar_bms(CODIGO_DEMO, 2026, [{"mes": 13, "archivo": "x.csv", "contenido": b""}])


def test_importar_en_un_edificio_inexistente_falla(db_temporal):
    with pytest.raises(ValueError):
        servicios.importar_bms("NO-EXISTE", 2026, [{"mes": 1, "archivo": "x.csv", "contenido": b"x"}])
    with pytest.raises(ValueError):
        servicios.importar_simulacion("NO-EXISTE", "x", "", 2026, False, "x.dat", b"x")


@pytest.mark.parametrize("simulado, real, esperado", [
    (100, 100, "ok"),
    (100, 110, "ok"),        # el 10 % exacto sigue siendo correcto
    (100, 90, "ok"),
    (100, 120, "atencion"),  # el 20 % exacto es atención
    (100, 121, "revisar"),
    (100, 40, "revisar"),
    (0, 0, "sin_dato"),
    (0, 5, "revisar"),       # consumo real sin nada simulado: no se puede dar un %
])
def test_nivel_de_gravedad(simulado, real, esperado):
    assert servicios._nivel(simulado, real) == esperado


def test_alertas_mapa_de_calor(db_demo):
    a = servicios.alertas(CODIGO_DEMO, 2026)
    _json_estricto(a)
    assert [m["mes"] for m in a["meses"] if m["con_bms"]] == [1, 2, 3]
    assert len(a["meses"]) == 12 and len(a["totales_mes"]) == 3
    assert {c["nivel"] for c in a["celdas"]} <= {"ok", "atencion", "revisar"}
    # Sin valor simulado no hay porcentaje, y se marca para revisar
    sin_simular = [c for c in a["celdas"] if c["simulado_kwh"] == 0]
    assert sin_simular and all(c["desviacion_pct"] is None and c["nivel"] == "revisar" for c in sin_simular)
    # Las categorías van de mayor a menor consumo y el total coincide con la suma de los meses
    consumos = [max(c["simulado_kwh"], c["real_kwh"]) for c in a["categorias"]]
    assert consumos == sorted(consumos, reverse=True)
    assert a["total"]["real_kwh"] == pytest.approx(sum(t["real_kwh"] for t in a["totales_mes"]))


def test_datos_mensuales_para_el_constructor(db_demo):
    d = servicios.datos_mensuales(CODIGO_DEMO, 2026)
    _json_estricto(d)
    assert d["meses_con_bms"] == [1, 2, 3]
    assert d["categorias"] == sorted(d["categorias"])
    sin_bms = [f for f in d["filas"] if f["mes"] > 3]
    assert sin_bms and all(f["real_kwh"] is None for f in sin_bms)
    assert all(f["real_kwh"] is not None for f in d["filas"] if f["mes"] <= 3)


def test_guardar_correo_del_edificio(db_demo):
    r = servicios.guardar_correo(CODIGO_DEMO, "  CSV   monitorización  ", " @cliente.com ")
    assert r["correo_asunto"] == "CSV monitorización" and r["correo_remitente"] == "@cliente.com"
    demo = next(e for e in servicios.lista_edificios(True) if e["codigo_proyecto"] == CODIGO_DEMO)
    assert demo["correo_asunto"] == "CSV monitorización" and demo["correo_remitente"] == "@cliente.com"
    with pytest.raises(ValueError):
        servicios.guardar_correo("NO-EXISTE", "x", "")


def test_alertas_y_datos_mensuales_sin_simulacion_o_sin_bms_devuelven_aviso(db_demo):
    assert "aviso" in servicios.alertas(CODIGO_DEMO, 2020)
    assert "aviso" in servicios.datos_mensuales(CODIGO_DEMO, 2020)
    assert "aviso" in servicios.alertas("NO-EXISTE", 2026)
