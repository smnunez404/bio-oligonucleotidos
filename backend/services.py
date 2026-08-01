"""Capa de servicio compartida entre routers.

Antes cada router tenía su propio `_cache` y su propia copia de la lógica de
generación de candidatos: eso provocaba (a) descargar la misma región de
Ensembl una vez por router en el arranque, y (b) riesgo de que el Módulo 3
quedara desincronizado del Módulo 2 si cambiaban los parámetros de generación.
Centralizado acá el 2026-07-28.
"""

from pipeline.oligo_walk import OligoCandidate, compute_scan_range, generate_oligo_walk
from pipeline.sequence import TargetRegion, fetch_target_region

_REGION_CACHE: dict[int, TargetRegion] = {}


def get_region(padding: int = 5000) -> TargetRegion:
    """Devuelve la región objetivo, descargándola de Ensembl solo la primera vez."""
    if padding not in _REGION_CACHE:
        _REGION_CACHE[padding] = fetch_target_region(padding=padding)
    return _REGION_CACHE[padding]


def build_candidates(
    length: int, step: int, flank: int
) -> tuple[TargetRegion, list[OligoCandidate], int, int, bool]:
    """Genera los candidatos del Oligo-Walk sobre la región cacheada.

    Única fuente de verdad para los Módulos 2 y 3 (y los que vengan): aplica
    siempre los límites reales del intrón, para que ningún módulo pueda
    trabajar sobre candidatos que invaden un exón sano.

    Devuelve `(region, candidatos, scan_start, scan_end, clamped_to_intron)`.
    """
    region = get_region()
    mutant = region.mutant_sense
    variant_offset = region.variant_offset_sense
    intron_bounds = region.intron2_bounds_sense

    candidates = generate_oligo_walk(
        mutant,
        variant_offset,
        length=length,
        step=step,
        flank=flank,
        intron_bounds=intron_bounds,
    )
    scan_start, scan_end, clamped = compute_scan_range(
        variant_offset, flank, len(mutant), intron_bounds
    )
    return region, candidates, scan_start, scan_end, clamped
