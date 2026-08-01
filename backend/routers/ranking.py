"""Router del Módulo 7 — ranking multicriterio por frente de Pareto.

Lee los CSV ya generados (los dos del enmascarado más el de insumos de termo y
off-target) por la misma razón que el router del 6b: recalcularlos exige los dos
predictores neuronales y BLAST contra el transcriptoma completo, que no pueden
correr por request.

El cálculo del ranking en sí vive en `pipeline/ranking.py` y es puro: este router
solo arma las entradas y serializa la salida.
"""

import csv
import os

from fastapi import APIRouter, HTTPException

from pipeline.ranking import DIMENSIONS, ELIGIBLE_VERDICT, rank

router = APIRouter(prefix="/api/ranking", tags=["ranking"])

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_RESULTS_DIR = os.path.join(_REPO_ROOT, "data", "results")

_SOURCES = {
    "spliceai": "modulo6b_masking.csv",
    "pangolin": "modulo6b_masking_pangolin.csv",
    "inputs": "modulo7_inputs.csv",
}

_cache: dict | None = None


def _read(filename: str) -> dict[str, dict]:
    path = os.path.join(_RESULTS_DIR, filename)
    if not os.path.exists(path):
        raise HTTPException(
            503,
            f"Falta {os.path.relpath(path, _REPO_ROOT)}, que el Módulo 7 necesita. "
            "Ver el README para regenerarlo.",
        )
    with open(path, encoding="utf-8") as fh:
        return {r["candidato"]: r for r in csv.DictReader(fh)}


def _build_candidates() -> list[dict]:
    sa = _read(_SOURCES["spliceai"])
    pa = _read(_SOURCES["pangolin"])
    inputs = _read(_SOURCES["inputs"])

    out = []
    for name, row in sa.items():
        if name not in pa or name not in inputs:
            # Un candidato que no esté en las tres fuentes no se puede rankear con
            # los tres criterios; omitirlo en silencio sería peor que no incluirlo.
            continue
        i = inputs[name]
        out.append({
            "name": name,
            "start_rel": int(row["start_rel"]),
            "end_rel": int(row["end_rel"]),
            "borders_abolished": [b for b in (row.get("bordes_anulados") or "").split("+") if b],
            "severity": i["severidad_off_target"],
            "verdict_by_predictor": {
                "spliceai": row["veredicto"],
                "pangolin": pa[name]["veredicto"],
            },
            "retention_by_predictor": {
                "spliceai": {
                    "donador": float(row["retencion_donador"]),
                    "aceptor": float(row["retencion_aceptor"]),
                },
                "pangolin": {
                    "donador": float(pa[name]["retencion_donador"]),
                    "aceptor": float(pa[name]["retencion_aceptor"]),
                },
            },
            "longest_perfect_run": int(i["tramo_contiguo_max"]),
            "accessibility_percentile": float(i["accesibilidad_percentil"]),
            "homodimer_percentile": float(i["homodimero_percentil"]),
        })
    return out


def _compute() -> dict:
    global _cache
    if _cache is not None:
        return _cache

    candidates = _build_candidates()
    result = rank(candidates)
    by_name = {c["name"]: c for c in candidates}

    _cache = {
        "method": (
            "frente de Pareto sobre tres dimensiones: no se promedian ni se les "
            "asignan pesos, porque no hay ningún dato que justifique una tasa de "
            "cambio entre ellas. Un candidato entra al frente si NINGÚN otro lo "
            "supera en las tres a la vez."
        ),
        "why_not_weights": (
            "una suma ponderada exige inventar cuántos pb de homología off-target "
            "valen 0,01 de fuerza de bloqueo. Ese número no existe en este "
            "proyecto: no hay candidato validado en célula con el cual calibrarlo."
        ),
        "gate": (
            f"solo compiten los candidatos cuyo veredicto es '{ELIGIBLE_VERDICT}' "
            "en LOS DOS predictores. No anular el pseudoexón no es 'estar peor "
            "rankeado': es no servir."
        ),
        "dimensions": [
            {
                "id": "block_strength",
                "label": "Fuerza de bloqueo",
                "description": (
                    "1 − retención media del borde mejor anulado, promediando los "
                    "dos predictores. Más alto = el sitio falso queda más apagado."
                ),
                "source": "Módulo 6b/6c",
            },
            {
                "id": "offtarget_safety",
                "label": "Seguridad off-target",
                "description": (
                    "negativo del tramo contiguo perfecto más largo contra otro "
                    "gen. Más alto = menos homología con genes que no son ABCA4."
                ),
                "source": "Módulo 5",
            },
            {
                "id": "thermo_quality",
                "label": "Calidad termodinámica",
                "description": (
                    "media de los percentiles de accesibilidad y de "
                    "no-autodimerización. Más alto = mejor oligo fisicoquímicamente."
                ),
                "source": "Módulo 4",
            },
        ],
        "front": result["front"],
        "n_eligible": result["n_eligible"],
        "n_rejected": result["n_rejected"],
        "sensitivity": result["sensitivity"],
        "candidates": [
            {
                "name": c.name,
                "in_front": c.in_front,
                "dominated_by": c.dominated_by,
                "objectives": {d: getattr(c.objectives, d) for d in DIMENSIONS},
                "start_rel": by_name[c.name]["start_rel"],
                "end_rel": by_name[c.name]["end_rel"],
                "borders_abolished": by_name[c.name]["borders_abolished"],
                "severity": by_name[c.name]["severity"],
                "raw": c.raw,
            }
            for c in result["candidates"]
        ],
        "limitation": (
            "ranking de propiedades calculadas in silico, NINGUNA validada "
            "experimentalmente, sobre una diana sin control positivo publicado. "
            "Dice qué candidatos convendría sintetizar primero, no cuál va a "
            "funcionar. El frente devuelve un conjunto y no un ganador: elegir "
            "uno de los tres es una decisión de criterio, no un resultado."
        ),
        "provenance_caveat": (
            "`modulo7_inputs.csv` se reproduce byte a byte con "
            "`pipeline/run_modulo7_inputs.py` (BLAST real contra el "
            "transcriptoma completo). Detalle que importa: sus percentiles "
            "térmicos son relativos a los 44 que compiten entre sí, NO a los 276 "
            "que devuelve /api/thermodynamics -- usar esos otros cambiaría el "
            "frente."
        ),
        "sources": _SOURCES,
    }
    return _cache


@router.get("")
def get_ranking(only_front: bool = False):
    """Ranking multicriterio de los candidatos que anulan el pseudoexón.

    `only_front=true` devuelve solo los no dominados. Ver wiki/decisiones/0011.
    """
    data = dict(_compute())
    if only_front:
        data["candidates"] = [c for c in data["candidates"] if c["in_front"]]
    return data
