"""Router que expone el Módulo 3 del pipeline (filtro heurístico GC%/G-run) vía HTTP."""

from fastapi import APIRouter, HTTPException

from backend.routers.oligo_walk import validate_walk_params
from backend.services import build_candidates
from pipeline.heuristic_filters import GC_MAX, GC_MIN, apply_heuristic_filters

router = APIRouter(prefix="/api/heuristic-filter", tags=["heuristic-filter"])


@router.get("")
def get_heuristic_filter(
    length: int = 20,
    step: int = 1,
    flank: int = 200,
    gc_min: float = GC_MIN,
    gc_max: float = GC_MAX,
):
    """Genera los candidatos del Módulo 2 y les aplica el filtro heurístico rápido.

    - `gc_min`/`gc_max`: rango aceptable de GC% (fracción 0-1; por defecto 0.40-0.70).

    Reutiliza `build_candidates` (misma fuente de verdad que el Módulo 2), para
    que ambos módulos no puedan desincronizarse.
    """
    validate_walk_params(length, step, flank)
    if not (0 <= gc_min < gc_max <= 1):
        raise HTTPException(400, "gc_min debe ser < gc_max, ambos entre 0 y 1")

    try:
        region, candidates, scan_start, scan_end, clamped = build_candidates(
            length, step, flank
        )
    except HTTPException:
        raise
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(502, f"No se pudo obtener la secuencia de Ensembl: {exc}") from exc

    intron_bounds = region.intron2_bounds_sense
    filtered = apply_heuristic_filters(candidates, gc_min=gc_min, gc_max=gc_max)
    passed_count = sum(1 for f in filtered if f.passed)

    return {
        "params": {
            "length": length,
            "step": step,
            "flank": flank,
            "gc_min": gc_min,
            "gc_max": gc_max,
        },
        "variant_offset": region.variant_offset_sense,
        "scan_start": scan_start,
        "scan_end": scan_end,
        "intron2_bounds": {"start": intron_bounds[0], "end": intron_bounds[1]},
        "clamped_to_intron": clamped,
        "total_count": len(filtered),
        "passed_count": passed_count,
        "rejected_count": len(filtered) - passed_count,
        "candidates": [
            {
                "start": f.candidate.start,
                "end": f.candidate.end,
                "aso_sequence": f.candidate.aso_sequence,
                "covers_variant": f.candidate.covers_variant,
                "distance_to_variant": f.candidate.distance_to_variant,
                "gc_fraction": round(f.gc_fraction, 4),
                "has_g_run": f.has_g_run,
                "passed": f.passed,
                "reasons": f.reasons,
            }
            for f in filtered
        ],
    }
