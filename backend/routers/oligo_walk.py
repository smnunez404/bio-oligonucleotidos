"""Router que expone el Módulo 2 del pipeline (Oligo-Walk) vía HTTP."""

from fastapi import APIRouter, HTTPException

from backend.services import build_candidates

router = APIRouter(prefix="/api/oligo-walk", tags=["oligo-walk"])


def validate_walk_params(length: int, step: int, flank: int) -> None:
    """Validación compartida de los parámetros del Oligo-Walk."""
    if not (5 <= length <= 40):
        raise HTTPException(400, "length debe estar entre 5 y 40")
    if not (1 <= step <= 50):
        raise HTTPException(400, "step debe estar entre 1 y 50")
    if not (10 <= flank <= 5000):
        raise HTTPException(400, "flank debe estar entre 10 y 5000")


@router.get("")
def get_oligo_walk(length: int = 20, step: int = 1, flank: int = 200):
    """Genera los candidatos ASO por ventana deslizante alrededor de la variante.

    - `length`: longitud del oligo en nt (16-25 recomendado).
    - `step`: paso entre ventanas consecutivas (1 = exhaustivo).
    - `flank`: nt escaneados a cada lado de la variante.

    El escaneo se recorta a los límites reales del intrón 2 (confirmados vía
    Ensembl), para no generar candidatos que invadan un exón sano.
    """
    validate_walk_params(length, step, flank)

    try:
        region, candidates, scan_start, scan_end, clamped = build_candidates(
            length, step, flank
        )
    except HTTPException:
        raise
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(502, f"No se pudo obtener la secuencia de Ensembl: {exc}") from exc

    intron_bounds = region.intron2_bounds_sense

    return {
        "params": {"length": length, "step": step, "flank": flank},
        "variant_offset": region.variant_offset_sense,
        "scan_start": scan_start,
        "scan_end": scan_end,
        "intron2_bounds": {"start": intron_bounds[0], "end": intron_bounds[1]},
        "clamped_to_intron": clamped,
        "count": len(candidates),
        "candidates": [
            {
                "start": c.start,
                "end": c.end,
                "target_window": c.target_window,
                "aso_sequence": c.aso_sequence,
                "covers_variant": c.covers_variant,
                "distance_to_variant": c.distance_to_variant,
            }
            for c in candidates
        ],
    }
