"""Tests del Módulo 3 (filtro heurístico: GC% y G-runs)."""

from pipeline.heuristic_filters import (
    GC_MAX,
    GC_MIN,
    apply_heuristic_filters,
    gc_fraction,
    has_g_run,
)
from pipeline.oligo_walk import OligoCandidate


def _candidate(aso_sequence: str) -> OligoCandidate:
    return OligoCandidate(
        start=0,
        end=len(aso_sequence),
        length=len(aso_sequence),
        target_window="N" * len(aso_sequence),
        aso_sequence=aso_sequence,
        covers_variant=False,
        distance_to_variant=0,
    )


def test_gc_fraction_basic():
    assert gc_fraction("GGCC") == 1.0
    assert gc_fraction("AATT") == 0.0
    assert gc_fraction("ATGC") == 0.5
    assert gc_fraction("") == 0.0


def test_gc_fraction_is_case_insensitive():
    assert gc_fraction("gGcC") == 1.0


def test_has_g_run_detects_four_or_more_consecutive_g():
    assert has_g_run("AAAGGGGAAA") is True
    assert has_g_run("AAAGGGAAA") is False  # solo 3 G seguidas, no debe marcar
    assert has_g_run("GGGGGG") is True


def test_has_g_run_is_case_insensitive():
    assert has_g_run("aaaggggaaa") is True


def test_candidate_within_gc_range_and_no_g_run_passes():
    # 50% GC, sin G-run
    seq = "ATGCATGCATGCATGCATGC"
    result = apply_heuristic_filters([_candidate(seq)])[0]
    assert result.passed is True
    assert result.reasons == []
    assert result.gc_fraction == 0.5


def test_candidate_with_low_gc_is_rejected_with_reason():
    seq = "AT" * 15  # 0% GC
    result = apply_heuristic_filters([_candidate(seq)])[0]
    assert result.passed is False
    assert any("GC%" in r and "bajo" in r for r in result.reasons)


def test_candidate_with_high_gc_is_rejected_with_reason():
    seq = "GC" * 15  # 100% GC
    result = apply_heuristic_filters([_candidate(seq)])[0]
    assert result.passed is False
    assert any("GC%" in r and "alto" in r for r in result.reasons)


def test_candidate_with_g_run_is_rejected_even_with_good_gc():
    seq = "ATGGGGATCGATCGATCGAT"  # GC% razonable pero con GGGG
    result = apply_heuristic_filters([_candidate(seq)])[0]
    assert GC_MIN <= result.gc_fraction <= GC_MAX
    assert result.has_g_run is True
    assert result.passed is False
    assert any("G-run" in r for r in result.reasons)


def test_candidate_can_fail_for_multiple_reasons_simultaneously():
    seq = "GGGGGGGGGGGGGGGGGGGG"  # 100% GC y G-run
    result = apply_heuristic_filters([_candidate(seq)])[0]
    assert result.passed is False
    assert len(result.reasons) == 2


def test_apply_heuristic_filters_preserves_order_and_count():
    seqs = ["ATGCATGCATGCATGCATGC", "AT" * 15, "GGGGGGGGGGGGGGGGGGGG"]
    results = apply_heuristic_filters([_candidate(s) for s in seqs])
    assert len(results) == 3
    assert [r.candidate.aso_sequence for r in results] == seqs
