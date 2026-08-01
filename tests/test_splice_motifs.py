"""Tests del análisis de motivos de splicing (donador 5' críptico)."""

from pipeline.splice_motifs import (
    compare_donors_near_variant,
    score_donor,
)


def test_perfect_consensus_scores_nine():
    # CAG|GTAAGT = consenso perfecto (M=C, R=A)
    seq = "NNN" + "CAG" + "GTAAGT" + "NNN"
    motif = score_donor(seq, boundary=5)  # último nt exónico = índice 5 (la G de CAG)
    assert motif is not None
    assert motif.motif == "CAGGTAAGT"
    assert motif.score == 9
    assert all(motif.matches)


def test_degenerate_positions_accept_both_options():
    # M acepta C o A; R acepta A o G -> AAG|GTGAGT también debe dar 9
    seq = "NNN" + "AAG" + "GTGAGT" + "NNN"
    motif = score_donor(seq, boundary=5)
    assert motif is not None
    assert motif.score == 9


def test_score_donor_returns_none_without_enough_context():
    assert score_donor("ACGT", boundary=0) is None  # falta contexto exónico
    assert score_donor("ACGT", boundary=3) is None  # falta contexto intrónico


def test_variant_that_improves_position_minus_two_is_detected():
    # Construido para replicar el patrón real: G>A en posición -2 del donador.
    # WT:  ...GGG|GTAGGT   MUT: ...GAG|GTAGGT
    prefix = "TTTTTTTTTT"
    suffix = "CCCCCCCCCC"
    wt = prefix + "GGG" + "GTAGGT" + suffix
    mut = prefix + "GAG" + "GTAGGT" + suffix
    variant_offset = len(prefix) + 1  # la posición que cambia (la del medio de GGG/GAG)
    assert wt[variant_offset] == "G" and mut[variant_offset] == "A"

    results = compare_donors_near_variant(wt, mut, variant_offset, search_radius=5)
    assert results, "debería encontrar al menos un donador con GT canónico"

    top = results[0]
    assert top.delta == 1  # la mutación mejora el motivo en exactamente 1 posición
    assert top.offset_from_variant == 1  # el corte cae 1 nt después de la variante
    assert top.wildtype.motif == "GGGGTAGGT"
    assert top.mutant.motif == "GAGGTAGGT"


def test_only_candidates_with_canonical_gt_are_returned():
    # Sin GT en +1,+2 no hay donador canónico -> no debe devolverse nada.
    wt = "TTTTTTTTTT" + "GGG" + "AACCTT" + "CCCCCCCCCC"
    mut = "TTTTTTTTTT" + "GAG" + "AACCTT" + "CCCCCCCCCC"
    results = compare_donors_near_variant(wt, mut, variant_offset=11, search_radius=5)
    assert all(r.has_canonical_gt for r in results)


def test_neutral_variant_produces_no_improvement():
    # Una variante que no toca el motivo del donador no debe mejorarlo.
    wt = "TTTTTTTTTT" + "CAG" + "GTAAGT" + "CCCCCCCCCC"
    mut = "TTTTTTTTTA" + "CAG" + "GTAAGT" + "CCCCCCCCCC"  # cambia lejos del motivo
    results = compare_donors_near_variant(wt, mut, variant_offset=9, search_radius=5)
    assert all(r.delta <= 0 for r in results)
