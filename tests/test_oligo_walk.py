"""Tests del Módulo 2 (Oligo-Walk)."""

from pipeline.oligo_walk import compute_scan_range, generate_oligo_walk
from pipeline.utils import revcomp


def test_generates_expected_number_of_windows():
    seq = "A" * 100
    candidates = generate_oligo_walk(seq, variant_offset=50, length=20, step=1, flank=30)
    # scan_start=20, scan_end=80 -> última ventana empieza en 80-20=60 -> 60-20+1 = 41 ventanas
    assert len(candidates) == 41
    assert candidates[0].start == 20
    assert candidates[-1].end == 80


def test_step_reduces_candidate_count():
    seq = "ACGT" * 50
    step1 = generate_oligo_walk(seq, variant_offset=100, length=20, flank=50, step=1)
    step5 = generate_oligo_walk(seq, variant_offset=100, length=20, flank=50, step=5)
    assert len(step5) < len(step1)


def test_aso_sequence_is_reverse_complement_of_target_window():
    seq = "ACGTACGTAAGGCCTTACGTACGT"
    candidates = generate_oligo_walk(seq, variant_offset=12, length=8, flank=10, step=1)
    for c in candidates:
        assert c.aso_sequence == revcomp(c.target_window)
        assert len(c.aso_sequence) == c.length
        assert seq[c.start : c.end] == c.target_window


def test_covers_variant_flag_is_correct():
    seq = "N" * 60
    variant_offset = 30
    candidates = generate_oligo_walk(seq, variant_offset=variant_offset, length=10, flank=25, step=1)
    for c in candidates:
        expected = c.start <= variant_offset < c.end
        assert c.covers_variant == expected
    # al menos un candidato debe cubrir la variante (la ventana de escaneo la incluye)
    assert any(c.covers_variant for c in candidates)


def test_distance_to_variant_is_zero_near_center():
    seq = "N" * 60
    candidates = generate_oligo_walk(seq, variant_offset=30, length=20, flank=25, step=1)
    centered = [c for c in candidates if c.start == 20]  # ventana 20-40, variante en el medio
    assert centered
    assert abs(centered[0].distance_to_variant) <= 1


def test_flank_clamped_to_sequence_bounds():
    seq = "A" * 20
    # variante cerca del final; flank pediría más allá del límite de la secuencia
    candidates = generate_oligo_walk(seq, variant_offset=18, length=5, flank=100, step=1)
    for c in candidates:
        assert 0 <= c.start
        assert c.end <= len(seq)


def test_invalid_parameters_raise():
    import pytest

    with pytest.raises(ValueError):
        generate_oligo_walk("ACGT", variant_offset=1, length=0)
    with pytest.raises(ValueError):
        generate_oligo_walk("ACGT", variant_offset=1, step=0)


# --- Seguridad de límites: no invadir exones sanos (hallazgo real del 2026-07-28) ---


def test_compute_scan_range_without_bounds_only_clips_to_sequence():
    start, end, clamped = compute_scan_range(
        variant_offset=50, flank=30, sequence_length=100, intron_bounds=None
    )
    assert (start, end) == (20, 80)
    assert clamped is False


def test_compute_scan_range_clips_to_intron_bounds():
    # El intrón "real" (simulado) es más angosto que el flank pedido de un lado.
    start, end, clamped = compute_scan_range(
        variant_offset=500, flank=200, sequence_length=1000, intron_bounds=(400, 900)
    )
    assert start == 400  # 500-200=300, pero el intrón empieza en 400
    assert end == 700  # 500+200=700, dentro del intrón
    assert clamped is True


def test_compute_scan_range_no_clamp_when_flank_fits_inside_intron():
    start, end, clamped = compute_scan_range(
        variant_offset=500, flank=50, sequence_length=1000, intron_bounds=(400, 900)
    )
    assert (start, end) == (450, 550)
    assert clamped is False


def test_generate_oligo_walk_respects_intron_bounds():
    seq = "ACGT" * 300  # 1200 nt
    variant_offset = 500
    # Límite artificial del "intrón": nada antes de 480 ni después de 520.
    candidates = generate_oligo_walk(
        seq,
        variant_offset=variant_offset,
        length=10,
        step=1,
        flank=200,
        intron_bounds=(480, 520),
    )
    for c in candidates:
        assert c.start >= 480
        assert c.end <= 520
