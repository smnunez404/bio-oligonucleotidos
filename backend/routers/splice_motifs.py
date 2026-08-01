"""Router que expone el análisis de motivos de splicing vía HTTP."""

from fastapi import APIRouter, HTTPException

from backend.services import get_region
from pipeline.splice_motifs import DONOR_EXONIC_LEN, compare_donors_near_variant

router = APIRouter(prefix="/api/splice-motifs", tags=["splice-motifs"])


@router.get("")
def get_splice_motifs(search_radius: int = 10):
    """Compara sitios donadores 5' candidatos cerca de la variante (WT vs. mutante).

    Heurística de coincidencia con el consenso canónico — NO es un predictor
    entrenado. Ver las limitaciones documentadas en `pipeline/splice_motifs.py`.
    """
    if not (1 <= search_radius <= 100):
        raise HTTPException(400, "search_radius debe estar entre 1 y 100")

    try:
        region = get_region()
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(502, f"No se pudo obtener la secuencia de Ensembl: {exc}") from exc

    comparisons = compare_donors_near_variant(
        region.wildtype_sense,
        region.mutant_sense,
        region.variant_offset_sense,
        search_radius=search_radius,
    )

    strengthened = [c for c in comparisons if c.delta > 0]

    return {
        "search_radius": search_radius,
        "exonic_len": DONOR_EXONIC_LEN,
        "consensus": "MAG|GURAGU",
        "method": "coincidencia posicional con el consenso canónico (heurística, no un predictor entrenado)",
        "candidate_count": len(comparisons),
        "strengthened_count": len(strengthened),
        "candidates": [
            {
                "offset_from_variant": c.offset_from_variant,
                "wildtype_motif": c.wildtype.motif,
                "wildtype_score": c.wildtype.score,
                "mutant_motif": c.mutant.motif,
                "mutant_score": c.mutant.score,
                "mutant_matches": c.mutant.matches,
                "wildtype_matches": c.wildtype.matches,
                "delta": c.delta,
            }
            for c in comparisons
        ],
    }
