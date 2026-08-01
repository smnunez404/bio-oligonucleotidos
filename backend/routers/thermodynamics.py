"""Router que expone el Módulo 4 del pipeline (termodinámica) vía HTTP."""

from fastapi import APIRouter, HTTPException

from backend.routers.oligo_walk import validate_walk_params
from backend.services import build_candidates
from pipeline.heuristic_filters import GC_MAX, GC_MIN, apply_heuristic_filters
from pipeline.thermodynamics import (
    HAIRPIN_DG_LIMIT,
    HOMODIMER_DG_LIMIT,
    TM_MAX,
    TM_MIN,
    analyze_candidates,
)

router = APIRouter(prefix="/api/thermodynamics", tags=["thermodynamics"])


@router.get("")
def get_thermodynamics(length: int = 20, step: int = 1, flank: int = 200):
    """Analiza termodinámica y accesibilidad de los candidatos que pasaron el Módulo 3.

    Encadena el pipeline: Oligo-Walk (M2) → filtro heurístico (M3) → termodinámica (M4).
    Solo se analizan los candidatos aprobados por M3, que es justamente el
    propósito del filtro rápido: no gastar cómputo pesado en candidatos inviables.
    """
    validate_walk_params(length, step, flank)

    try:
        region, candidates, _scan_start, _scan_end, _clamped = build_candidates(
            length, step, flank
        )
    except HTTPException:
        raise
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(502, f"No se pudo obtener la secuencia de Ensembl: {exc}") from exc

    filtered = apply_heuristic_filters(candidates, gc_min=GC_MIN, gc_max=GC_MAX)
    survivors = [f.candidate for f in filtered if f.passed]

    results = analyze_candidates(survivors, target_sequence=region.mutant_sense)
    passed_count = sum(1 for r in results if r.passed)

    return {
        "params": {"length": length, "step": step, "flank": flank},
        "thresholds": {
            "tm_min": TM_MIN,
            "tm_max": TM_MAX,
            "hairpin_dg_limit": HAIRPIN_DG_LIMIT,
            "homodimer_dg_limit": HOMODIMER_DG_LIMIT,
        },
        "method_caveat": (
            "Química PMO: no existen tablas termodinámicas de vecino-más-cercano "
            "públicas para PMO. La Tm usa parámetros de híbrido ARN/ADN (R_DNA_NN1) "
            "y los ΔG el modelo de ARN de ViennaRNA — son una aproximación por "
            "composición de bases, útil para comparar candidatos entre sí, no como "
            "valores absolutos de un PMO real. Además, los umbrales provienen de "
            "fuentes que no especifican con qué herramienta se calcularon."
        ),
        "funnel": {
            "generated": len(candidates),
            "passed_heuristic": len(survivors),
            "passed_thermo": passed_count,
        },
        "analyzed_count": len(results),
        "passed_count": passed_count,
        "rejected_count": len(results) - passed_count,
        "candidates": [
            {
                "start": r.candidate.start,
                "end": r.candidate.end,
                "aso_sequence": r.candidate.aso_sequence,
                "covers_variant": r.candidate.covers_variant,
                "distance_to_variant": r.candidate.distance_to_variant,
                "tm": round(r.tm, 1),
                "dg_hybridization": round(r.dg_hybridization, 2),
                "dg_self_structure": round(r.dg_self_structure, 2),
                "dg_homodimer": round(r.dg_homodimer, 2),
                "accessibility": r.accessibility,
                "accessibility_percentile": r.accessibility_percentile,
                "homodimer_percentile": r.homodimer_percentile,
                "passed": r.passed,
                "reasons": r.reasons,
            }
            for r in results
        ],
    }
