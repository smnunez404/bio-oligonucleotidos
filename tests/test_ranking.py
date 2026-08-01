"""Tests del Módulo 7 (pipeline.ranking).

Los valores del bloque de integración salen de los CSV reales de las dos corridas
del Módulo 6b (`data/results/modulo6b_masking*.csv`) y de `modulo7_inputs.csv`,
no de datos inventados — mismo criterio que el resto de la suite.
"""

import csv
import os

import pytest

from pipeline.ranking import (
    ELIGIBLE_VERDICT,
    Objectives,
    block_strength,
    dominates,
    offtarget_safety,
    pareto_front,
    rank,
    thermo_quality,
)

_REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_RESULTS = os.path.join(_REPO, "data", "results")


# --- objetivos individuales ---------------------------------------------------


def test_block_strength_toma_el_borde_mejor_anulado():
    """Anular CUALQUIERA de los dos bordes desarma el pseudoexón, así que la
    fuerza la da el borde mejor anulado, no el promedio de los dos."""
    r = {"spliceai": {"donador": 0.90, "aceptor": 0.02}}
    assert block_strength(r) == pytest.approx(0.98)


def test_block_strength_promedia_los_predictores():
    r = {"spliceai": {"donador": 0.10, "aceptor": 0.90}, "pangolin": {"donador": 0.20, "aceptor": 0.90}}
    # min por predictor: 0.10 y 0.20 -> media 0.15 -> fuerza 0.85
    assert block_strength(r) == pytest.approx(0.85)


def test_block_strength_perfecto_es_uno():
    assert block_strength({"spliceai": {"donador": 0.0, "aceptor": 0.0}}) == 1.0


def test_block_strength_exige_al_menos_un_predictor():
    with pytest.raises(ValueError, match="al menos un predictor"):
        block_strength({})


def test_offtarget_safety_invierte_el_signo():
    """Menos homología contigua = más seguro = valor MÁS ALTO, para que las tres
    dimensiones se comparen igual."""
    assert offtarget_safety(15) > offtarget_safety(18)


def test_thermo_quality_es_la_media_de_los_dos_percentiles():
    assert thermo_quality(32.6, 97.7) == pytest.approx(65.15)


# --- dominancia y frente ------------------------------------------------------


def _obj(b, s, t):
    return Objectives(block_strength=b, offtarget_safety=s, thermo_quality=t)


def test_dominancia_requiere_mejor_o_igual_en_todo():
    assert dominates(_obj(1.0, -15, 60), _obj(0.9, -16, 50))
    assert not dominates(_obj(1.0, -15, 40), _obj(0.9, -16, 50)), "peor en termo: no domina"


def test_empate_total_no_es_dominancia():
    """Sin esto, dos candidatos idénticos se eliminarían mutuamente y el frente
    quedaría vacío."""
    a = _obj(1.0, -15, 50)
    assert not dominates(a, _obj(1.0, -15, 50))


def test_mejor_en_uno_e_igual_en_el_resto_si_domina():
    assert dominates(_obj(1.0, -15, 50), _obj(1.0, -15, 49))


def test_frente_excluye_a_los_dominados():
    objs = {
        "bueno": _obj(1.0, -15, 60),
        "dominado": _obj(0.9, -16, 50),
        "distinto": _obj(0.8, -15, 99),  # peor bloqueo pero mejor termo: no dominado
    }
    assert pareto_front(objs) == ["bueno", "distinto"]


def test_frente_es_estable_y_ordenado():
    objs = {"z": _obj(1.0, -15, 60), "a": _obj(1.0, -15, 60)}
    assert pareto_front(objs) == ["a", "z"], "empatados: los dos en el frente, orden estable"


# --- puerta de entrada --------------------------------------------------------


def _cand(name, ret, run, acc, homo, verdicts=None):
    return {
        "name": name,
        "verdict_by_predictor": verdicts or {"spliceai": ELIGIBLE_VERDICT, "pangolin": ELIGIBLE_VERDICT},
        "retention_by_predictor": ret,
        "longest_perfect_run": run,
        "accessibility_percentile": acc,
        "homodimer_percentile": homo,
    }


def test_solo_entran_los_que_anulan_el_pseudoexon_en_AMBOS_predictores():
    r = {"spliceai": {"donador": 0.0, "aceptor": 0.0}, "pangolin": {"donador": 0.0, "aceptor": 0.0}}
    res = rank([
        _cand("ok", r, 15, 50, 50),
        _cand("solo_uno", r, 15, 50, 50, {"spliceai": ELIGIBLE_VERDICT, "pangolin": "sin_efecto"}),
        _cand("ninguno", r, 15, 50, 50, {"spliceai": "sin_efecto", "pangolin": "sin_efecto"}),
    ])
    assert res["n_eligible"] == 1
    assert res["rejected"] == ["ninguno", "solo_uno"]


def test_un_candidato_descartado_no_puede_aparecer_en_el_frente():
    """El requisito del plan: ningún descalificado sube."""
    r = {"spliceai": {"donador": 0.0, "aceptor": 0.0}, "pangolin": {"donador": 0.0, "aceptor": 0.0}}
    res = rank([
        _cand("elegible", r, 18, 10, 10),
        _cand("perfecto_pero_inutil", r, 15, 99, 99, {"spliceai": "sin_efecto", "pangolin": "sin_efecto"}),
    ])
    assert "perfecto_pero_inutil" not in res["front"]
    assert all(c.name != "perfecto_pero_inutil" for c in res["candidates"])


def test_el_frente_va_primero_en_la_salida():
    r_fuerte = {"spliceai": {"donador": 0.0, "aceptor": 0.0}}
    r_debil = {"spliceai": {"donador": 0.5, "aceptor": 0.5}}
    res = rank([_cand("debil", r_debil, 18, 10, 10), _cand("fuerte", r_fuerte, 15, 90, 90)])
    assert res["candidates"][0].name == "fuerte"
    assert res["candidates"][0].in_front


def test_los_dominados_dicen_quien_los_domina():
    r_fuerte = {"spliceai": {"donador": 0.0, "aceptor": 0.0}}
    r_debil = {"spliceai": {"donador": 0.5, "aceptor": 0.5}}
    res = rank([_cand("debil", r_debil, 18, 10, 10), _cand("fuerte", r_fuerte, 15, 90, 90)])
    debil = next(c for c in res["candidates"] if c.name == "debil")
    assert debil.dominated_by == ["fuerte"]


# --- integración con los datos reales -----------------------------------------


def _load(path):
    with open(path, encoding="utf-8") as fh:
        return {r["candidato"]: r for r in csv.DictReader(fh)}


def _real_candidates():
    paths = [
        os.path.join(_RESULTS, "modulo6b_masking.csv"),
        os.path.join(_RESULTS, "modulo6b_masking_pangolin.csv"),
        os.path.join(_RESULTS, "modulo7_inputs.csv"),
    ]
    if not all(os.path.exists(p) for p in paths):
        pytest.skip("faltan los CSV de resultados; ver README para regenerarlos")

    sa, pa, inp = (_load(p) for p in paths)
    out = []
    for name, row in sa.items():
        if name not in pa or name not in inp:
            continue
        i = inp[name]
        out.append({
            "name": name,
            "verdict_by_predictor": {"spliceai": row["veredicto"], "pangolin": pa[name]["veredicto"]},
            "retention_by_predictor": {
                "spliceai": {
                    "donador": float(row["retencion_donador"]),
                    "aceptor": float(row["retencion_aceptor"]),
                },
                "pangolin": {
                    "donador": float(pa[name]["retencion_donador"]),
                    "aceptor": float(pa[name]["retencion_aceptor"]),
                },
            },
            "longest_perfect_run": int(i["tramo_contiguo_max"]),
            "accessibility_percentile": float(i["accesibilidad_percentil"]),
            "homodimer_percentile": float(i["homodimero_percentil"]),
        })
    return out


def test_datos_reales_diez_elegibles():
    """Los 10 que anulan el pseudoexón según los dos predictores (ADR 0012)."""
    res = rank(_real_candidates())
    assert res["n_eligible"] == 10
    assert res["n_rejected"] == 34


def test_datos_reales_el_frente_son_tres():
    """Valor medido, no elegido: el frente reduce de 10 a 3."""
    res = rank(_real_candidates())
    assert res["front"] == ["cand_5882", "cand_5992", "cand_5998"]


def test_cada_uno_del_frente_gana_en_una_dimension_distinta():
    """Es lo que hace interpretable al frente: no son 3 empatados, son 3
    trade-offs distintos."""
    res = rank(_real_candidates())
    front = {c.name: c.objectives for c in res["candidates"] if c.in_front}

    assert max(front, key=lambda n: front[n].block_strength) == "cand_5992"
    assert max(front, key=lambda n: front[n].thermo_quality) == "cand_5882"
    # 5998 no gana ninguna sola: sobrevive por la combinación (bloqueo casi
    # perfecto sin ser el peor en termo). Que exista un caso así es la razón de
    # usar Pareto y no ordenar por una sola columna.
    assert "cand_5998" in front


def test_los_que_anulan_ambos_bordes_son_los_peores_en_termodinamica():
    """LA TENSIÓN DEL MÓDULO 7, medida sobre los datos reales.

    Los 3 candidatos que anulan los DOS bordes del pseudoexón (cand_5992, 5998,
    5999 -- los que cubren el donador críptico) son exactamente los 3 peores en
    propiedades fisicoquímicas, y con un salto grande respecto del cuarto. O sea:
    bloquear mejor y ser mejor oligo apuntan en direcciones opuestas.

    Por eso el ranking NO puede devolver un ganador único sin que alguien decida
    qué trade-off prefiere. Es la misma tensión que el Módulo 4 ya había
    detectado entre accesibilidad y mecanismo, ahora medida sobre el efecto real
    de bloqueo en vez de sobre la distancia a la variante.
    """
    res = rank(_real_candidates())
    por_termo = sorted(res["candidates"], key=lambda c: c.objectives.thermo_quality)

    tres_peores = {c.name for c in por_termo[:3]}
    assert tres_peores == {"cand_5992", "cand_5998", "cand_5999"}

    # Y son justamente los de bloqueo más fuerte.
    assert all(c.objectives.block_strength >= 0.9999 for c in por_termo[:3])

    # El salto al cuarto es grande, no un empate técnico.
    assert por_termo[3].objectives.thermo_quality - por_termo[2].objectives.thermo_quality > 20


def test_sensibilidad_el_colapso_termico_es_lo_que_discrimina():
    """Sin colapsar los dos percentiles, el frente pasa de 3 a 9 de 10: deja de
    informar. Esta es la justificación medida de esa convención."""
    s = rank(_real_candidates())["sensitivity"]
    assert s["n_front_3d"] == 3
    assert s["n_front_4d"] == 9
    assert s["n_front_4d"] > s["n_front_3d"]
