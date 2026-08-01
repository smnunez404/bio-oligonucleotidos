"""Router que expone el Módulo 5 del pipeline (off-target) vía HTTP."""

from fastapi import APIRouter, HTTPException

from backend.routers.oligo_walk import validate_walk_params
from backend.services import build_candidates
from pipeline.heuristic_filters import GC_MAX, GC_MIN, apply_heuristic_filters
from pipeline.off_target import (
    MAX_MISMATCHES,
    MIN_ALIGNMENT_LENGTH,
    SEVERITY_LABELS,
    SEVERITY_ORDER,
    TARGET_GENE_SYMBOL,
    analyze_off_target,
)
from pipeline.thermodynamics import analyze_candidates

router = APIRouter(prefix="/api/off-target", tags=["off-target"])

# Cuántos hits detallar por candidato en la respuesta HTTP (evita payloads
# gigantes cuando un candidato tiene decenas de hits): siempre se incluye el
# peor hit completo aparte, así que esto solo limita la lista "hits".
MAX_HITS_IN_RESPONSE = 10


@router.get("")
def get_off_target(length: int = 20, step: int = 1, flank: int = 200):
    """Cribado off-target de los candidatos que pasaron el Módulo 4 contra el
    transcriptoma humano completo (BLAST local, ver wiki/decisiones/0005).

    Encadena el pipeline completo: Oligo-Walk (M2) → filtro heurístico (M3) →
    termodinámica (M4) → off-target (M5). Solo se corre BLAST sobre los
    candidatos que ya sobrevivieron los filtros más baratos.
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
    survivors_heuristic = [f.candidate for f in filtered if f.passed]

    thermo_results = analyze_candidates(survivors_heuristic, target_sequence=region.mutant_sense)
    survivors_thermo = [r.candidate for r in thermo_results if r.passed]

    if not survivors_thermo:
        # Nada que blastear -- devolver una respuesta vacía coherente en vez
        # de invocar blastn con una lista vacía.
        results = []
    else:
        try:
            results = analyze_off_target(survivors_thermo)
        except RuntimeError as exc:
            # DB/binario de BLAST ausente o mal configurado: error claro, no 500 opaco.
            raise HTTPException(503, str(exc)) from exc

    severity_counts = {level: 0 for level in SEVERITY_ORDER}
    for r in results:
        severity_counts[r.severity] += 1

    return {
        "params": {"length": length, "step": step, "flank": flank},
        "rule": {
            "min_alignment_length": MIN_ALIGNMENT_LENGTH,
            "max_mismatches": MAX_MISMATCHES,
            "target_gene_symbol": TARGET_GENE_SYMBOL,
            "severity_levels": SEVERITY_ORDER,
            "severity_labels": SEVERITY_LABELS,
        },
        "method_caveat": (
            "Cribado contra el TRANSCRIPTOMA (Ensembl GRCh38, cDNA + ncRNA, "
            "410.920 transcritos), no contra el genoma completo -- ver "
            "wiki/decisiones/0005. Este módulo YA NO aplica un gate binario "
            "pasa/no-pasa: la regla original (>=15 pb de homología contigua, "
            "<=4 mismatches) marcaba a los 44 candidatos por igual como "
            "'tóxicos' porque viene de la lógica de ASOs que cortan ARN "
            "(gapmers/RNasa H), no de bloqueo estérico (nuestro PMO), donde "
            "la ubicación del hit importa más que su sola existencia -- ver "
            "wiki/decisiones/0006 con evidencia de literatura citada. Ahora "
            "cada candidato se anota con un nivel de SEVERIDAD (alto/moderado/"
            "leve/sin_señal), pensado como insumo para el futuro Módulo 7 "
            "(ranking), no como veredicto: ningún candidato se descarta "
            "automáticamente acá. La severidad se calcula sobre el TRAMO "
            "CONTIGUO PERFECTO más largo contra un gen ajeno (>=18 pb alto, "
            "16-17 moderado, 13-15 leve, <=12 sin señal), no sobre el conteo "
            "de mismatches: un mismatch en el medio del alineamiento parte la "
            "unión en dos tramos débiles, mientras que el mismo mismatch en el "
            "borde deja un tramo largo intacto. Los umbrales están anclados en "
            "el mínimo de homología contigua de la regla heredada (15 pb), no "
            "calibrados específicamente para PMO. La severidad mide cuán fuerte "
            "podría unirse el candidato a otro gen, no si eso causaría daño. No "
            "existe un ASO publicado para esta variante con el que calibrarla."
        ),
        "funnel": {
            "generated": len(candidates),
            "passed_heuristic": len(survivors_heuristic),
            "passed_thermo": len(survivors_thermo),
            "annotated_off_target": len(results),
        },
        "analyzed_count": len(results),
        "severity_counts": severity_counts,
        "candidates": [
            {
                "start": r.candidate.start,
                "end": r.candidate.end,
                "aso_sequence": r.candidate.aso_sequence,
                "covers_variant": r.candidate.covers_variant,
                "distance_to_variant": r.candidate.distance_to_variant,
                "severity": r.severity,
                "severity_label": r.severity_label,
                # Tramo contiguo perfecto más largo entre todos los hits
                # off-target: es el valor sobre el que se calcula la
                # severidad (ver ADR 0006), así que se expone explícitamente
                # para que la UI pueda mostrar el porqué del nivel.
                "longest_perfect_run": max(
                    (h.longest_perfect_run for h in r.off_target_hits), default=0
                ),
                "off_target_count": r.off_target_count,
                "distinct_genes_hit": r.distinct_genes_hit,
                "worst_hit": (
                    None
                    if r.worst_hit is None
                    else {
                        "transcript_id": r.worst_hit.transcript_id,
                        "gene_id": r.worst_hit.gene_id,
                        "gene_symbol": r.worst_hit.gene_symbol,
                        "pident": r.worst_hit.pident,
                        "length": r.worst_hit.length,
                        "mismatches": r.worst_hit.mismatches,
                        "evalue": r.worst_hit.evalue,
                        "bitscore": r.worst_hit.bitscore,
                    }
                ),
                "hits": [
                    {
                        "transcript_id": h.transcript_id,
                        "gene_id": h.gene_id,
                        "gene_symbol": h.gene_symbol,
                        "pident": h.pident,
                        "length": h.length,
                        "mismatches": h.mismatches,
                        "longest_perfect_run": h.longest_perfect_run,
                        "is_target_gene": h.is_target_gene,
                        "meets_off_target_rule": h.meets_off_target_rule,
                    }
                    for h in r.off_target_hits[:MAX_HITS_IN_RESPONSE]
                ],
                "reasons": r.reasons,
            }
            for r in results
        ],
    }
