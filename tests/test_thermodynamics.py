"""Tests del Módulo 4 (termodinámica y accesibilidad)."""

import pytest

from pipeline.oligo_walk import OligoCandidate
from pipeline.thermodynamics import (
    HOMODIMER_DG_LIMIT,
    TM_MAX,
    TM_MIN,
    analyze_candidate,
    analyze_candidates,
)
from pipeline.utils import revcomp


def _candidate(aso: str, start: int = 0) -> OligoCandidate:
    return OligoCandidate(
        start=start,
        end=start + len(aso),
        length=len(aso),
        target_window=revcomp(aso),
        aso_sequence=aso,
        covers_variant=False,
        distance_to_variant=0,
    )


def test_returns_all_metrics():
    r = analyze_candidate(_candidate("ATGCATGCATGCATGCATGC"))
    assert isinstance(r.tm, float)
    assert isinstance(r.dg_hybridization, float)
    assert isinstance(r.dg_self_structure, float)
    assert isinstance(r.dg_homodimer, float)


def test_unstructured_oligo_has_self_structure_near_zero():
    # Poly-A no puede formar estructura consigo mismo.
    r = analyze_candidate(_candidate("AAAAAAAAAAAAAAAAAAAA"))
    assert r.dg_self_structure == 0.0


def test_palindromic_oligo_has_stable_hairpin():
    # Diseñado para formar horquilla: tallo GC + bucle + tallo complementario.
    r = analyze_candidate(_candidate("GGGGCCCCAAAAGGGGCCCC"))
    assert r.dg_self_structure < -3.0
    assert any("horquilla" in m for m in r.reasons)


def test_hybridization_with_perfect_complement_is_favorable():
    # target_window es el complemento reverso exacto del ASO -> dúplex perfecto.
    r = analyze_candidate(_candidate("ATGCATGCATGCATGCATGC"))
    assert r.dg_hybridization < 0


def test_low_tm_oligo_is_flagged():
    # AT puro -> Tm muy baja.
    r = analyze_candidate(_candidate("ATATATATATATATATATAT"))
    assert r.tm < TM_MIN
    assert any("Tm baja" in m for m in r.reasons)


def test_high_tm_oligo_is_flagged():
    # GC puro -> Tm muy alta.
    r = analyze_candidate(_candidate("GCGCGCGCGCGCGCGCGCGC"))
    assert r.tm > TM_MAX
    assert any("Tm alta" in m for m in r.reasons)


def test_passed_is_true_only_when_no_reasons():
    for aso in ("ATGCATGCATGCATGCATGC", "ATATATATATATATATATAT", "GGGGCCCCAAAAGGGGCCCC"):
        r = analyze_candidate(_candidate(aso))
        assert r.passed == (len(r.reasons) == 0)


def test_accessibility_is_none_without_target_sequence():
    results = analyze_candidates([_candidate("ATGCATGCATGCATGCATGC")], target_sequence=None)
    assert results[0].accessibility is None
    assert results[0].accessibility_percentile is None


def test_accessibility_computed_when_target_sequence_given():
    target = "ACGUACGUAC" * 30  # 300 nt
    cands = [
        OligoCandidate(
            start=s,
            end=s + 20,
            length=20,
            target_window=target[s : s + 20],
            aso_sequence=revcomp(target[s : s + 20]),
            covers_variant=False,
            distance_to_variant=0,
        )
        for s in range(50, 150, 10)
    ]
    results = analyze_candidates(cands, target_sequence=target)
    assert all(r.accessibility is not None for r in results)
    assert all(0.0 <= r.accessibility <= 1.0 for r in results)


def test_percentiles_span_full_range_and_rank_correctly():
    asos = [
        "ATGCATGCATGCATGCATGC",
        "AAAAAAAAAAAAAAAAAAAA",
        "GGGGCCCCAAAAGGGGCCCC",
        "ATATATATATATATATATAT",
    ]
    results = analyze_candidates([_candidate(a, i * 30) for i, a in enumerate(asos)])
    pcts = [r.homodimer_percentile for r in results]
    assert min(pcts) == 0.0 and max(pcts) == 100.0
    # El de mayor percentil debe ser el de homodímero MENOS negativo (mejor).
    mejor = max(results, key=lambda r: r.homodimer_percentile)
    assert mejor.dg_homodimer == max(r.dg_homodimer for r in results)


def test_homodimer_threshold_flags_self_complementary_oligo():
    # Auto-complementario -> homodímero muy estable.
    r = analyze_candidate(_candidate("GCGCGCGCGCGCGCGCGCGC"))
    assert r.dg_homodimer < HOMODIMER_DG_LIMIT
    assert any("homodímero" in m for m in r.reasons)


# --- CRIT-4: orientación de hebra en la Tm, CORREGIDO el 2026-08-01 ----------
#
# Estos tests fijan que la corrección siga aplicada. Si alguien vuelve a pasar el
# ASO en vez de la diana, fallan ruidosamente -- y con razón: ese bug movía el
# embudo del Módulo 4 de 16 a 44 candidatos y generó un hallazgo espurio que
# llegó hasta un ADR.
#
# Ver pipeline/thermodynamics.py y
# wiki/bitacora/2026-08-01-correccion-crit4-tm-y-sus-consecuencias.


def test_crit4_biopython_documenta_que_seq_debe_ser_la_hebra_de_arn():
    """La fuente de la corrección, verificable sin correr el pipeline."""
    from Bio.SeqUtils import MeltingTemp as mt

    assert "must be the RNA sequence" in mt.Tm_NN.__doc__
    # Y la tabla es asimétrica: por eso el orden cambia el número.
    assert mt.R_DNA_NN1["AA/TT"] != mt.R_DNA_NN1["TT/AA"]


def test_crit4_la_tm_se_calcula_sobre_la_diana_no_sobre_el_aso():
    """El test que impide la regresión: la Tm debe venir de la hebra de ARN."""
    from Bio.SeqUtils import MeltingTemp as mt

    from pipeline.thermodynamics import _to_rna, analyze_candidate, tm_rna_oriented

    candidate = OligoCandidate(
        start=0,
        end=20,
        length=20,
        target_window="ACGTACGTACGTACGTACGT",
        aso_sequence="ACGTACGTACGTACGTACGT",  # NO es el revcomp: los distingue
        covers_variant=False,
        distance_to_variant=0,
    )
    esperado = mt.Tm_NN(_to_rna(candidate.target_window), nn_table=mt.R_DNA_NN1)
    assert analyze_candidate(candidate).tm == pytest.approx(esperado)
    assert tm_rna_oriented(candidate) == pytest.approx(esperado)


@pytest.mark.network
def test_crit4_el_embudo_corregido_son_16_candidatos():
    """Valor medido tras la corrección (antes eran 44, con solo 6 en común).

    Si esto cambia, algo movió el filtro termodinámico y hay que regenerar todo
    `data/results/`.
    """
    from backend.services import build_candidates
    from pipeline.heuristic_filters import apply_heuristic_filters
    from pipeline.thermodynamics import analyze_candidates

    region, candidates, *_ = build_candidates(20, 1, 200)
    survivors = [f.candidate for f in apply_heuristic_filters(candidates) if f.passed]
    results = analyze_candidates(survivors, target_sequence=region.mutant_sense)

    assert len(survivors) == 276
    assert sum(1 for r in results if r.passed) == 16
