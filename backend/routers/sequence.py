"""Router que expone el Módulo 1 del pipeline (secuencia objetivo) vía HTTP."""

from fastapi import APIRouter, HTTPException

from backend.services import get_region
from pipeline.sequence import (
    ALT_ALLELE_PLUS_STRAND,
    CHROMOSOME,
    REF_ALLELE_PLUS_STRAND,
    VARIANT_POS_GRCH38,
)

router = APIRouter(prefix="/api/sequence", tags=["sequence"])


@router.get("")
def get_sequence(padding: int = 200, context: int = 40):
    """Devuelve la región objetivo y la comparación wild-type/mutante.

    - `padding`: nt descargados de Ensembl a cada lado de la variante (ventana completa).
    - `context`: nt mostrados a cada lado de la variante en la comparación wild-type/mutante.
    """
    if padding < 1 or padding > 10_000:
        raise HTTPException(400, "padding debe estar entre 1 y 10000")

    try:
        region = get_region(padding)
    except Exception as exc:  # noqa: BLE001 — reportar cualquier fallo de red/validación al cliente
        raise HTTPException(502, f"No se pudo obtener la secuencia de Ensembl: {exc}") from exc
    v = region.variant_offset_sense
    lo, hi = max(0, v - context), min(len(region.wildtype_sense), v + context)

    return {
        "variant": {
            "gene": "ABCA4",
            "transcript": "NM_000350.3",
            "hgvs_c": "c.161-395G>A",
            "hgvs_g_grch38": f"NC_000001.11:g.{VARIANT_POS_GRCH38}{REF_ALLELE_PLUS_STRAND}>{ALT_ALLELE_PLUS_STRAND}",
            "chromosome": CHROMOSOME,
            "position_grch38": VARIANT_POS_GRCH38,
            "intron": 2,
            "source": "VariantValidator, verificado contra Ensembl (2026-07-28)",
        },
        "region": {
            "start_grch38": region.start,
            "end_grch38": region.end,
            "length": len(region.genomic_plus),
        },
        "comparison": {
            "context_nt": context,
            "variant_offset_in_context": v - lo,
            "wildtype": region.wildtype_sense[lo:hi],
            "mutant": region.mutant_sense[lo:hi],
        },
    }
