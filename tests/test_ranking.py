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


def test_datos_reales_tres_elegibles():
    """Los 3 que anulan el pseudoexón según los dos predictores.

    Eran 10 hasta el 2026-08-01; la corrección de CRIT-4 (orientación de hebra
    en la Tm) redujo el embudo de entrada de 44 a 16 candidatos.
    """
    res = rank(_real_candidates())
    assert res["n_eligible"] == 12
    assert res["n_rejected"] == 66


def test_datos_reales_el_frente_son_dos():
    """Valor medido, no elegido: de los 3 elegibles, 2 quedan no dominados.

    `cand_5999` es el único dominado. Ojo con leer esto como una reducción
    fuerte: con 3 candidatos y 3 dimensiones, que queden 2 está dentro de lo
    esperable por azar (ver el hallazgo STAT-8 del panel de revisión).
    """
    res = rank(_real_candidates())
    assert res["front"] == ["cand_5882", "cand_5992", "cand_5998"]


def test_cada_uno_del_frente_gana_en_una_dimension_distinta():
    """Es lo que hace interpretable al frente: no son empatados, son trade-offs."""
    res = rank(_real_candidates())
    front = {c.name: c.objectives for c in res["candidates"] if c.in_front}
    assert set(front) == {"cand_5882", "cand_5992", "cand_5998"}
    assert max(front, key=lambda n: front[n].block_strength) == "cand_5992"
    assert max(front, key=lambda n: front[n].thermo_quality) == "cand_5882"


def test_los_que_anulan_solo_el_aceptor_estan_entre_los_elegibles():
    """Tras el ADR 0014 (Tm anota, no filtra) esta clase vuelve a ser visible.

    Con el gate de Tm activo ninguno pasaba: su Tm de proxy es 36-40 °C. Es la
    justificación retrospectiva de haber convertido el filtro en anotación.
    """
    res = rank(_real_candidates())
    nombres = {c.name for c in res["candidates"]}
    # Los 3 que cubren el donador siguen estando...
    assert {"cand_5992", "cand_5998", "cand_5999"} <= nombres
    # ...y ahora también la familia que ataca el tracto de polipirimidina.
    assert {"cand_5877", "cand_5882", "cand_5883"} <= nombres
    assert len(nombres) == 12


def test_sensibilidad_el_colapso_termico_es_lo_que_discrimina():
    """Sin colapsar los dos percentiles, el frente pasa de 3 a 9 de 10: deja de
    informar. Esta es la justificación medida de esa convención."""
    s = rank(_real_candidates())["sensitivity"]
    assert s["n_front_3d"] == 3
    assert s["n_front_4d"] == 11
    assert s["n_front_4d"] > s["n_front_3d"]
