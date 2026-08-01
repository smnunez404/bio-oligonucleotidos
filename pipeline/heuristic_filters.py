"""Módulo 3 — filtro heurístico rápido: GC% y exclusión de G-runs.

Filtro O(n) sobre la secuencia ASO real (la que se sintetiza, no la ventana
del ARNm) para purgar candidatos inviables antes de análisis más pesados
(termodinámica, off-target, splicing). Reglas consolidadas de las 5 fuentes
de investigación ingeridas — ver wiki/conceptos/pipeline-bioinformatico-diseno-aso.md:

- GC% fuera de 40-70%: insuficiente estabilidad de hibridación (muy bajo) o
  estructuras secundarias rígidas / solubilidad pobre (muy alto).
- 4+ guaninas consecutivas (G-run): riesgo de plegado en G-cuádruplex, que
  secuestra al ASO en una conformación inactiva.

No pondera ni rankea nada — eso es el Módulo 7 (ranking). Este módulo solo
decide aprobado/rechazado con motivo explícito.
"""

import re
from dataclasses import dataclass

from .oligo_walk import OligoCandidate

GC_MIN = 0.40
GC_MAX = 0.70
_G_RUN = re.compile(r"G{4,}", re.IGNORECASE)


def gc_fraction(seq: str) -> float:
    if not seq:
        return 0.0
    gc = sum(1 for b in seq.upper() if b in "GC")
    return gc / len(seq)


def has_g_run(seq: str) -> bool:
    return bool(_G_RUN.search(seq))


@dataclass
class FilteredCandidate:
    candidate: OligoCandidate
    gc_fraction: float
    has_g_run: bool
    passed: bool
    reasons: list[str]  # motivos de rechazo; vacío si passed=True


def apply_heuristic_filters(
    candidates: list[OligoCandidate],
    gc_min: float = GC_MIN,
    gc_max: float = GC_MAX,
) -> list[FilteredCandidate]:
    """Evalúa cada candidato contra las reglas de GC% y G-run.

    Evalúa sobre `candidate.aso_sequence` (la secuencia real del parche que se
    sintetiza), no sobre `target_window` (la región del ARNm) — la estabilidad
    y el riesgo de G-cuádruplex son propiedades del propio oligo.
    """
    results = []
    for c in candidates:
        gc = gc_fraction(c.aso_sequence)
        g_run = has_g_run(c.aso_sequence)

        reasons = []
        if gc < gc_min:
            reasons.append(f"GC% muy bajo ({gc:.0%} < {gc_min:.0%})")
        if gc > gc_max:
            reasons.append(f"GC% muy alto ({gc:.0%} > {gc_max:.0%})")
        if g_run:
            reasons.append("contiene G-run (GGGG+, riesgo de G-cuádruplex)")

        results.append(
            FilteredCandidate(
                candidate=c,
                gc_fraction=gc,
                has_g_run=g_run,
                passed=len(reasons) == 0,
                reasons=reasons,
            )
        )
    return results
