"""Tests del router /api/aso-masking (Módulo 6b)."""

import pytest
from fastapi.testclient import TestClient

from backend.main import app
from pipeline.aso_masking import BLOCK_RETENTION, HARMFUL, INEFFECTIVE, USEFUL, classify

client = TestClient(app)


def test_endpoint_responde_los_44_candidatos():
    d = client.get("/api/aso-masking").json()
    assert d["total"] == 44
    assert len(d["candidates"]) == 44


def test_distribucion_medida():
    """Valores de la corrida documentada, no inventados."""
    c = client.get("/api/aso-masking").json()["counts"]
    assert c == {"bloquea": 3, "sin_efecto": 31, "contraproducente": 10}
    assert sum(c.values()) == 44


def test_los_que_bloquean_tambien_hunden_el_aceptor():
    """Hallazgo 1: el efecto se propaga al sitio no cubierto."""
    d = client.get("/api/aso-masking?classification=bloquea").json()
    assert len(d["candidates"]) == 3
    for c in d["candidates"]:
        assert c["donor_cryptic"] == 0.0
        assert c["acceptor_cryptic"] < 0.2, "el aceptor debe caer por debajo del umbral"
        assert not (c["start_rel"] <= -89 < c["end_rel"]), "y sin que el ASO lo cubra"


def test_los_contraproducentes_suben_el_score():
    d = client.get("/api/aso-masking?classification=contraproducente").json()
    assert len(d["candidates"]) == 10
    assert all(c["delta_donor"] > 0 for c in d["candidates"])


def test_ninguno_toca_el_donador_canonico():
    """El ASO no debe dañar el splicing sano."""
    for c in client.get("/api/aso-masking").json()["candidates"]:
        assert abs(c["delta_canonical"]) < 0.05


def test_expone_los_controles():
    """Sin controles el resultado no es interpretable: la API debe mostrarlos."""
    d = client.get("/api/aso-masking").json()
    assert len(d["controls"]) == 4
    assert all(c["ok"] for c in d["controls"])


def test_declara_la_limitacion_y_que_no_es_ensemble():
    d = client.get("/api/aso-masking").json()
    assert "necesaria, no suficiente" in d["limitation"]
    assert "NO es un ensemble" in d["predictor"]["note"]


def test_pseudoexon_coincide_con_pe1b():
    s = client.get("/api/aso-masking").json()["sites"]
    assert s["pseudoexon_size"] == 91
    assert s["donor_cryptic_offset"] - s["acceptor_cryptic_offset"] == 90  # 91 pb inclusivos


@pytest.mark.parametrize("classification", ["bloquea", "contraproducente", "sin_efecto"])
def test_filtro_valido(classification):
    d = client.get(f"/api/aso-masking?classification={classification}").json()
    assert all(c["classification"] == classification for c in d["candidates"])


def test_filtro_invalido_da_400():
    assert client.get("/api/aso-masking?classification=cualquiera").status_code == 400


@pytest.mark.parametrize("score,base,esperado", [
    (0.0, 0.5595, "bloquea"),  # ctrl_on_donor: retención 0
    (0.1398, 0.5595, "bloquea"),  # apenas bajo el borde 0,25
    (0.14, 0.5595, "sin_efecto"),  # apenas sobre el borde 0,25
    (0.5595, 0.5595, "sin_efecto"),  # sin cambio
    (0.6601, 0.5595, "sin_efecto"),  # ganancia justo por debajo de 0,18
    (0.6603, 0.5595, "contraproducente"),  # ganancia justo por encima de 0,18
    (0.0566, 0.2829, "bloquea"),  # escala PANGOLIN, misma retención 0,20
    (0.3339, 0.2829, "contraproducente"),  # escala PANGOLIN, misma ganancia ~0,18
])
def test_classify_es_relativo_al_baseline(score, base, esperado):
    """El criterio es la fracción retenida, no la caída absoluta: por eso las dos
    últimas filas —escalas distintas, misma retención— dan la misma clase."""
    assert classify(score, base) == esperado


# --- veredicto a nivel pseudoexón ---------------------------------------------


def test_expone_el_veredicto_como_conclusion():
    d = client.get("/api/aso-masking").json()
    assert d["verdict"]["counts"] == {USEFUL: 10, INEFFECTIVE: 34, HARMFUL: 0}
    assert sum(d["verdict"]["counts"].values()) == 44
    assert len(d["verdict"]["useful"]) == 10


def test_los_utiles_dejan_intacto_el_donador_canonico():
    """Requisito de seguridad: ninguno debe romper el splicing sano."""
    for c in client.get("/api/aso-masking").json()["verdict"]["useful"]:
        assert c["retention_canonical"] >= 0.80, c["name"]


def test_los_siete_que_anulan_solo_el_aceptor_no_lo_cubren():
    """EL HALLAZGO: se puede anular un sitio sin taparlo."""
    useful = client.get("/api/aso-masking").json()["verdict"]["useful"]
    solo_aceptor = [c for c in useful if c["borders_abolished"] == ["aceptor"]]
    assert len(solo_aceptor) == 7
    for c in solo_aceptor:
        assert not (c["start_rel"] <= -89 < c["end_rel"]), f"{c['name']} SÍ cubre el aceptor"
        assert c["retention_acceptor"] < BLOCK_RETENTION
        assert c["retention_donor"] > BLOCK_RETENTION, "y el donador sobrevive: por eso el criterio por sitio los perdía"


def test_los_tres_que_tapan_el_donador_anulan_los_dos_bordes():
    useful = client.get("/api/aso-masking").json()["verdict"]["useful"]
    ambos = [c for c in useful if set(c["borders_abolished"]) == {"donador", "aceptor"}]
    assert len(ambos) == 3
    assert {c["name"] for c in ambos} == {"cand_5992", "cand_5998", "cand_5999"}


def test_el_veredicto_supera_al_criterio_por_sitio():
    """10 útiles a nivel pseudoexón vs 3 que bloquean el donador."""
    d = client.get("/api/aso-masking").json()
    assert d["verdict"]["counts"][USEFUL] > d["counts"]["bloquea"]
    assert "subestima" in d["verdict"]["why_it_matters"]


def test_el_hueco_del_aceptor_ya_no_se_declara_como_limitacion_sin_matizar():
    d = client.get("/api/aso-masking").json()
    assert d["candidates_covering_acceptor"] == 0
    assert "sin cubrirlo" in d["acceptor_gap_note"]


# --- concordancia entre predictores (/agreement) ------------------------------
#
# Sin cobertura hasta esta suite: el endpoint ya vivía en producción
# (backend/routers/aso_masking.py) pero se agregó sin traspaso al vault ni
# tests propios. Valores tomados de la corrida real (GET /api/aso-masking/agreement
# contra el servidor real, 2026-07-31), no inventados — ver
# wiki/decisiones/0012-veredicto-pseudoexon-no-solo-por-sitio.


def test_agreement_compara_los_44_candidatos():
    d = client.get("/api/aso-masking/agreement").json()
    assert d["n_compared"] == 44
    assert len(d["per_candidate"]) == 44


def test_agreement_por_veredicto_es_total():
    """El hallazgo del ADR 0012: mirando el veredicto a nivel pseudoexón, los dos
    predictores concuerdan en TODOS los candidatos."""
    d = client.get("/api/aso-masking/agreement").json()
    assert d["n_agree"] == 44
    assert d["agreement_fraction"] == 1.0
    assert d["disagreements"] == []


def test_agreement_por_sitio_es_menor_y_ese_es_el_punto():
    """El criterio antiguo (solo el donador) concuerda menos: la brecha entre
    las dos filas de esta tabla ES el resultado, no ruido."""
    d = client.get("/api/aso-masking/agreement").json()
    assert d["n_agree_by_site"] == 35
    assert d["agreement_fraction_by_site"] == 0.7955
    assert len(d["disagreements_by_site"]) == 9
    assert d["n_agree_by_site"] < d["n_agree"]


def test_los_desacuerdos_por_sitio_igual_concuerdan_en_veredicto():
    """Los 9 casos que discrepan en clasificación por sitio SÍ coinciden en
    veredicto -- son el mismo grupo que ataca el aceptor sin cubrirlo, visto
    desde el criterio que antes lo perdía."""
    d = client.get("/api/aso-masking/agreement").json()
    for c in d["disagreements_by_site"]:
        assert c["agree"] is True
        assert c["spliceai"]["verdict"] == c["pangolin"]["verdict"]


def test_agreement_expone_la_limitacion_de_independencia():
    d = client.get("/api/aso-masking/agreement").json()
    assert "no es del todo independiente" in d["limitation"]
    assert "retina" in d["limitation"]


# --- contrato con el frontend ------------------------------------------------
#
# El 2026-07-31 la pestaña "Bloqueo del ASO" tiraba abajo TODA la app (React
# desmontaba el árbol, pantalla en blanco) porque el payload y el frontend se
# habían desincronizado en tres puntos a la vez, y nada lo detectaba: los tipos
# de TypeScript describían la API vieja, así que `tsc` validaba contra la
# mentira. Estos tests fijan el contrato del lado del servidor.


def test_baseline_usa_claves_en_ingles_como_el_resto_del_payload():
    """El meta del pipeline las guarda en español; la API las traduce.

    Mientras no lo hacía, el frontend leía `baseline.acceptor_cryptic` como
    undefined y `.toFixed()` reventaba.
    """
    b = client.get("/api/aso-masking").json()["baseline"]
    assert set(b) == {
        "donor_cryptic",
        "acceptor_cryptic",
        "donor_canonical_e3",
        "acceptor_canonical_e3",
    }
    assert all(isinstance(v, (int, float)) for v in b.values())


def test_predictor_es_un_objeto_no_un_string():
    """Era un string y pasó a objeto. Renderizarlo directo en JSX crashea."""
    p = client.get("/api/aso-masking").json()["predictor"]
    assert isinstance(p, dict)
    assert set(p) >= {"id", "label", "note", "available"}


def test_thresholds_son_relativos_no_absolutos():
    """El criterio vivo es la retención (ADR 0010). Los nombres viejos
    (`block`/`counterproductive`) no deben volver: eran deltas absolutos y no
    son transferibles entre predictores."""
    t = client.get("/api/aso-masking").json()["thresholds"]
    assert "block_retention" in t and "counterproductive_gain" in t
    assert "block" not in t and "counterproductive" not in t


def test_cada_candidato_trae_las_retenciones_y_el_veredicto():
    for c in client.get("/api/aso-masking").json()["candidates"]:
        assert {"retention_donor", "retention_acceptor", "retention_canonical"} <= set(c)
        assert c["verdict"] in {USEFUL, INEFFECTIVE, HARMFUL}
