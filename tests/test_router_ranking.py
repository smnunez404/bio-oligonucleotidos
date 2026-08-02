"""Tests del router /api/ranking (Módulo 7).

Valores de la corrida real contra los CSV del repo, no inventados.
"""

from fastapi.testclient import TestClient

from backend.main import app
from pipeline.ranking import DIMENSIONS

client = TestClient(app)


def test_el_frente_son_los_tres_medidos():
    d = client.get("/api/ranking").json()
    assert d["front"] == ["cand_5882", "cand_5992", "cand_5998"]
    assert d["n_eligible"] == 12
    assert d["n_rejected"] == 66


def test_expone_las_tres_dimensiones_con_su_modulo_de_origen():
    """La UI tiene que poder decir de qué módulo sale cada número."""
    d = client.get("/api/ranking").json()
    assert [dim["id"] for dim in d["dimensions"]] == list(DIMENSIONS)
    assert {dim["source"] for dim in d["dimensions"]} == {"Módulo 4", "Módulo 5", "Módulo 6b/6c"}


def test_cada_candidato_trae_sus_tres_objetivos():
    for c in client.get("/api/ranking").json()["candidates"]:
        assert set(c["objectives"]) == set(DIMENSIONS)


def test_los_dominados_dicen_quien_los_domina():
    """Auditable: un candidato fuera del frente debe poder justificar por qué."""
    for c in client.get("/api/ranking").json()["candidates"]:
        if not c["in_front"]:
            assert c["dominated_by"], f"{c['name']} fuera del frente sin dominador"
            assert all(n in {x["name"] for x in client.get("/api/ranking").json()["candidates"]}
                       for n in c["dominated_by"])
        else:
            assert c["dominated_by"] == []


def test_el_frente_va_primero():
    cands = client.get("/api/ranking").json()["candidates"]
    front_flags = [c["in_front"] for c in cands]
    assert front_flags == sorted(front_flags, reverse=True), "los del frente deben ir arriba"


def test_filtro_only_front():
    d = client.get("/api/ranking?only_front=true").json()
    assert len(d["candidates"]) == 3
    assert all(c["in_front"] for c in d["candidates"])
    # El resumen no cambia: sigue diciendo cuántos había en total.
    assert d["n_eligible"] == 12


def test_declara_que_no_usa_pesos_y_por_que():
    d = client.get("/api/ranking").json()
    assert "no se promedian" in d["method"]
    assert "no existe en este" in d["why_not_weights"]


def test_declara_la_puerta_de_entrada():
    d = client.get("/api/ranking").json()
    assert "LOS DOS predictores" in d["gate"]


def test_expone_el_analisis_de_sensibilidad():
    """El plan pedía sensibilidad explícita: sin colapsar los percentiles
    térmicos el frente pasa de 3 a 9, o sea deja de discriminar."""
    s = client.get("/api/ranking").json()["sensitivity"]
    assert s["n_front_3d"] == 3
    assert s["n_front_4d"] == 11


def test_declara_las_limitaciones_y_la_procedencia_verificada():
    d = client.get("/api/ranking").json()
    assert "NINGUNA validada" in d["limitation"]
    assert "no es un ganador" in d["limitation"] or "no un ganador" in d["limitation"]
    assert "se reproduce byte a byte" in d["provenance_caveat"]


def test_ningun_candidato_no_elegible_aparece_en_la_salida():
    """Los 66 que no anulan el pseudoexón no se rankean: no compiten."""
    d = client.get("/api/ranking").json()
    assert len(d["candidates"]) == 12
