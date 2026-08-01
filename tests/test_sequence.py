"""Tests del módulo 1 (secuencia objetivo).

Los tests marcados `network` hacen una llamada real a Ensembl REST y validan
la coordenada confirmada por VariantValidator contra la secuencia real
(no solo mockean la respuesta) — si Ensembl cambia el ensamblaje o la
coordenada resultara estar mal, este test debe fallar de forma ruidosa.
"""

import pytest

from pipeline.sequence import (
    EXON_RANK2_START_GRCH38,
    EXON_RANK3_END_GRCH38,
    REF_ALLELE_PLUS_STRAND,
    VARIANT_POS_GRCH38,
    TargetRegion,
    _revcomp,
    fetch_target_region,
)


def test_revcomp_basic():
    assert _revcomp("ACGT") == "ACGT"
    assert _revcomp("AACCGGTT") == "AACCGGTT"
    assert _revcomp("GATTACA") == "TGTAATC"


def test_revcomp_handles_n_and_lowercase():
    assert _revcomp("ACGTNacgtn") == "nacgtNACGT"


def test_mutant_sense_flips_only_the_variant_base():
    # Región sintética de 21 nt, variante en el centro (offset 10, hebra plus).
    region = TargetRegion(
        chrom="1",
        start=1,
        end=21,
        genomic_plus="AAAAAAAAAA" + REF_ALLELE_PLUS_STRAND + "AAAAAAAAAA",
        variant_offset_plus=10,
    )
    wt = region.wildtype_sense
    mut = region.mutant_sense
    assert len(wt) == len(mut) == 21
    # En hebra menos, wild-type y mutante solo deben diferir en una posición.
    diffs = [i for i, (a, b) in enumerate(zip(wt, mut)) if a != b]
    assert diffs == [region.variant_offset_sense]


@pytest.mark.network
def test_fetch_target_region_matches_variantvalidator_reference_allele():
    region = fetch_target_region(padding=50)
    assert region.chrom == "1"
    assert region.end - region.start == 100
    # La aserción central: la base real de Ensembl en la coordenada confirmada
    # por VariantValidator debe coincidir con el alelo de referencia esperado.
    assert region.genomic_plus[region.variant_offset_plus] == REF_ALLELE_PLUS_STRAND
    # El offset en sentido del transcrito debe ser un índice válido dentro de la secuencia.
    assert 0 <= region.variant_offset_sense < len(region.wildtype_sense)


def test_intron2_length_is_consistent_with_bounds():
    # Blindaje contra el off-by-one detectado el 2026-07-28: la constante
    # documentada y el rango que realmente calcula el pipeline tienen que
    # coincidir. Antes decían 1394 y 1393 respectivamente.
    from pipeline.sequence import INTRON2_LENGTH

    start = EXON_RANK3_END_GRCH38 - 500
    region = TargetRegion(
        chrom="1",
        start=start,
        end=start + 2999,
        genomic_plus="A" * 3000,
        variant_offset_plus=VARIANT_POS_GRCH38 - start,
    )
    lo, hi = region.intron2_bounds_sense
    assert hi - lo == INTRON2_LENGTH == 1393


def test_variant_distance_to_nearest_exon_matches_hgvs_name():
    # Segunda verificación independiente de la coordenada: "c.161-395G>A" dice
    # que la variante está a 395 nt del exón más cercano. Si esto no diera 395,
    # las constantes de límites de exón estarían mal.
    assert VARIANT_POS_GRCH38 - EXON_RANK3_END_GRCH38 == 395
    assert EXON_RANK2_START_GRCH38 - VARIANT_POS_GRCH38 == 999


def test_intron2_bounds_sense_excludes_flanking_exon():
    # Región sintética pequeña anclada a las coordenadas genómicas reales del
    # exón rank=3: los últimos 6 nt (offset plus 0-5) son ese exón; el resto
    # (offset plus 6-29) es intrón real (aunque el intrón real completo es más
    # largo que estos 30 nt — el recorte a los límites de la secuencia es
    # exactamente lo que se está probando).
    start = EXON_RANK3_END_GRCH38 - 5
    region = TargetRegion(
        chrom="1",
        start=start,
        end=start + 29,
        genomic_plus="A" * 30,
        variant_offset_plus=20,  # no relevante para este test
    )
    lo, hi = region.intron2_bounds_sense
    assert 0 <= lo < hi <= 30
    # En sentido del transcrito, el exón (offsets plus 0-5) queda invertido al
    # final de la secuencia (offsets sense 24-29) — el rango de intrón NO debe
    # incluirlos.
    assert hi <= 24
