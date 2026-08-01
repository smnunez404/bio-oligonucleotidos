"""Tests del módulo de calibración (ADR 0002).

Las partes puras (ubicación de AONs, estadística de ranking) se prueban sin red y
sin predictor. La corrida real está documentada en
wiki/bitacora/2026-08-01-calibracion-kaltak-el-metodo-discrimina.
"""

import json
import os

import pytest

from pipeline.calibration import (
    ALT_ALLELE_PLUS_STRAND,
    BEST_AON,
    KNOWN_EFFECTIVE,
    REF_ALLELE_PLUS_STRAND,
    VARIANT_POS_GRCH38,
    CalibrationRegion,
    build_windows,
    load_aons,
    locate_aon,
    rank_summary,
)

_REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_RESULTS = os.path.join(_REPO, "data", "results", "calibracion_kaltak.json")


# --- coordenadas de la variante de calibración -------------------------------


def test_coordenada_confirmada_por_variantvalidator():
    """c.5461-10T>C resuelta el 2026-08-01. ABCA4 está en hebra menos, así que el
    T>C del transcrito es A>G en el genoma."""
    assert VARIANT_POS_GRCH38 == 94_011_395
    assert (REF_ALLELE_PLUS_STRAND, ALT_ALLELE_PLUS_STRAND) == ("A", "G")


def test_es_otra_variante_que_la_del_proyecto():
    """Salvaguarda: si alguien apuntara la calibración a la variante principal,
    el test dejaría de ser un control independiente y nadie lo notaría."""
    from pipeline.sequence import VARIANT_POS_GRCH38 as PRINCIPAL

    assert VARIANT_POS_GRCH38 != PRINCIPAL


# --- ubicación de los AONs ----------------------------------------------------


def test_locate_aon_busca_el_complemento_reverso():
    """El AON es antisentido: su diana es su complemento reverso, no él mismo."""
    sense = "AAAA" + "GGGCCCATGCTCC" + "TTTT"
    aon = "GGAGCAUGGGCCC"  # revcomp del bloque de en medio, en ARN
    assert locate_aon(aon, sense) == (4, 17)


def test_locate_aon_devuelve_none_si_no_esta():
    assert locate_aon("ACGUACGUACGU", "TTTTTTTTTTTT") is None


def test_build_windows_reporta_los_no_ubicados():
    region = CalibrationRegion(
        wildtype_sense="A" * 50, mutant_sense="A" * 50, variant_offset_sense=25, padding=25
    )
    aons = [{"aon": "X", "secuencia_rna": "UUUUU"}, {"aon": "Y", "secuencia_rna": "GGGGG"}]
    windows, missing = build_windows(region, aons)
    assert [w[0] for w in windows] == ["X"]  # revcomp(UUUUU) = AAAAA, sí está
    assert missing == ["Y"]


# --- secuencias de Kaltak -----------------------------------------------------


def test_las_32_secuencias_estan_disponibles():
    aons = load_aons()
    assert len(aons) == 32
    assert {a["aon"] for a in aons} >= set(KNOWN_EFFECTIVE)


def test_qr1011_es_aon44_con_su_secuencia_publicada():
    """Valor de la Tabla S1 de Kaltak et al. 2023, no inventado."""
    aons = {a["aon"]: a for a in load_aons()}
    assert BEST_AON == "AON44"
    assert aons["AON44"]["secuencia_rna"] == "AUGCUCCAUGGGCCUCGG"
    assert int(aons["AON44"]["longitud_nt"]) == 18


def test_aon44_es_aon60_mas_una_base():
    """Verificación cruzada tabla-vs-prosa: el texto dice que AON44 es 'AON60 and
    its 1-nt longer version'. Si la extracción del PDF hubiera fallado, esto no
    daría."""
    aons = {a["aon"]: a["secuencia_rna"] for a in load_aons()}
    assert aons["AON44"].endswith(aons["AON60"])
    assert len(aons["AON44"]) == len(aons["AON60"]) + 1


# --- estadística del ranking --------------------------------------------------


def test_rank_summary_detecta_separacion_perfecta():
    scores = {n: 10.0 for n in KNOWN_EFFECTIVE}
    scores.update({f"otro{i}": 0.0 for i in range(10)})
    s = rank_summary(scores)
    assert s["AUC"] == 1.0


def test_rank_summary_detecta_azar():
    """Conocidos y otros intercalados -> AUC cerca de 0,5."""
    scores = {}
    for i, n in enumerate(KNOWN_EFFECTIVE):
        scores[n] = 10 - i * 2
        scores[f"otro{i}"] = 9 - i * 2
    s = rank_summary(scores)
    assert 0.4 < s["AUC"] < 0.75


def test_rank_summary_invierte_con_higher_is_better():
    scores = {n: -1.0 for n in KNOWN_EFFECTIVE}
    scores["otro"] = 1.0
    assert rank_summary(scores, higher_is_better=True)["AUC"] == 0.0
    assert rank_summary(scores, higher_is_better=False)["AUC"] == 1.0


# --- resultado real de la corrida --------------------------------------------


def _resultados():
    if not os.path.exists(_RESULTS):
        pytest.skip("falta calibracion_kaltak.json; ver el README para regenerarlo")
    return json.load(open(_RESULTS, encoding="utf-8"))


def test_los_32_aons_se_ubicaron_en_la_region():
    """Ninguno quedó fuera de la ventana descargada."""
    assert len(_resultados()["aons"]) == 32


def test_el_metodo_discrimina_los_aons_eficaces():
    """EL RESULTADO DE LA CALIBRACIÓN: los 5 AONs que Kaltak reporta como
    eficaces quedan en el top-6 de 32. AUC medida = 0,974."""
    d = _resultados()["aons"]
    s = rank_summary({n: v["delta"] for n, v in d.items()}, higher_is_better=True)
    assert s["AUC"] > 0.95
    assert max(s["posiciones"].values()) <= 6
    assert s["mejor_aon_posicion"] <= 3  # QR-1011


def test_la_discriminacion_no_depende_de_los_obviamente_destructivos():
    """Análisis de sensibilidad: quitando los 4 AONs que tapan el aceptor del
    exón 39 (anularlo es trivialmente malo), la separación se mantiene."""
    d = _resultados()["aons"]
    acc = 10
    sin_obvios = {
        n: v["delta"] for n, v in d.items() if not (v["start_rel"] <= acc < v["end_rel"])
    }
    assert len(sin_obvios) == 28
    assert rank_summary(sin_obvios, higher_is_better=True)["AUC"] > 0.95
