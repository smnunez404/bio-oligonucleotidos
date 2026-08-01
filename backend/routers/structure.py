"""Router que expone la estructura secundaria real del ARN diana (vista didáctica)."""

from fastapi import APIRouter, HTTPException

from backend.routers.oligo_walk import validate_walk_params
from backend.services import build_candidates, get_region
from pipeline.heuristic_filters import apply_heuristic_filters
from pipeline.splice_motifs import DONOR_MOTIF_LEN, compare_donors_near_variant
from pipeline.structure_layout import fold_region
from pipeline.thermodynamics import analyze_candidates

router = APIRouter(prefix="/api/structure", tags=["structure"])


@router.get("")
def get_structure(half_window: int = 150, length: int = 20, step: int = 1, flank: int = 200):
    """Devuelve el plegado real del ARN diana + dónde caen los candidatos clave.

    Pensado para la vista explicativa: muestra con datos reales por qué existe
    la tensión entre "accesible" y "en el lugar correcto".
    """
    if not (40 <= half_window <= 400):
        raise HTTPException(400, "half_window debe estar entre 40 y 400")
    validate_walk_params(length, step, flank)

    try:
        region = get_region()
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(502, f"No se pudo obtener la secuencia de Ensembl: {exc}") from exc

    mutant = region.mutant_sense
    variant_offset = region.variant_offset_sense

    folded = fold_region(mutant, variant_offset, half_window=half_window)

    # --- Sitio donador críptico reforzado por la mutación ---
    donor_range = None
    donors = compare_donors_near_variant(
        region.wildtype_sense, mutant, variant_offset, search_radius=10
    )
    strengthened = next((d for d in donors if d.delta > 0), None)
    if strengthened is not None:
        # El motivo abarca 3 nt exónicos + 6 intrónicos alrededor del corte.
        donor_start = strengthened.boundary - 2
        donor_range = {
            "start": donor_start,
            "end": donor_start + DONOR_MOTIF_LEN,
            "wildtype_score": strengthened.wildtype.score,
            "mutant_score": strengthened.mutant.score,
        }

    # --- Candidatos clave: el más accesible vs. los que tapan el donador ---
    _region, candidates, _s, _e, _c = build_candidates(length, step, flank)
    filtered = apply_heuristic_filters(candidates)
    survivors = [f.candidate for f in filtered if f.passed]
    thermo = [t for t in analyze_candidates(survivors, target_sequence=mutant) if t.passed]

    def as_dict(t):
        return {
            "start": t.candidate.start,
            "end": t.candidate.end,
            "accessibility_percentile": t.accessibility_percentile,
            "distance_to_variant": t.candidate.distance_to_variant,
            "tm": round(t.tm, 1),
        }

    most_accessible = None
    donor_covering = []
    if thermo:
        most_accessible = as_dict(
            max(thermo, key=lambda t: t.accessibility_percentile or -1)
        )
        if donor_range:
            covering = [
                t
                for t in thermo
                if t.candidate.start < donor_range["end"]
                and t.candidate.end > donor_range["start"]
            ]
            donor_covering = [
                as_dict(t)
                for t in sorted(
                    covering, key=lambda t: -(t.accessibility_percentile or -1)
                )
            ]

    return {
        "window": {"start": folded.window_start, "end": folded.window_end},
        "variant_index": folded.variant_index,
        "structure": folded.structure,
        "mfe": round(folded.mfe, 1),
        "paired_fraction": round(folded.paired_fraction, 3),
        "donor_range": donor_range,
        "most_accessible": most_accessible,
        "donor_covering": donor_covering,
        "approved_total": len(thermo),
        "points": [
            {
                "i": p.index,
                "b": p.base,
                "x": round(p.x, 1),
                "y": round(p.y, 1),
                "p": p.paired,
                "u": round(p.unpaired_prob, 4) if p.unpaired_prob is not None else None,
            }
            for p in folded.points
        ],
    }
