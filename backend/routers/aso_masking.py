"""Router que expone la simulación de bloqueo del ASO (Módulo 6b) vía HTTP.

Lee el CSV que produce `pipeline/run_masking.py` y lo cachea en memoria: cada
corrida son 49 inferencias del predictor (minutos en CPU), así que no se puede
recalcular por request.

DOS PREDICTORES
---------------
El endpoint acepta `?predictor=spliceai|pangolin` y sirve el CSV correspondiente.
Los dos existen porque el Módulo 6c mostró que SpliceAI y Pangolin coinciden en
las posiciones críticas, y revalidar el enmascarado con el segundo predictor es
más fuerte que confiar en uno solo. La clasificación se calcula con la ÚNICA
función del pipeline (`pipeline.aso_masking.classify`), que trabaja en fracción
del baseline y por eso sirve para ambas escalas.
"""

import csv
import json
import os

from fastapi import APIRouter, HTTPException

from pipeline.aso_masking import (
    BLOCK_RETENTION,
    CANONICAL_SAFE_RETENTION,
    COUNTERPRODUCTIVE_GAIN,
    HARMFUL,
    INEFFECTIVE,
    USEFUL,
    classify,
    pseudoexon_verdict,
)

router = APIRouter(prefix="/api/aso-masking", tags=["aso-masking"])

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_RESULTS_DIR = os.path.join(_REPO_ROOT, "data", "results")

PREDICTORS = {
    "spliceai": {
        "csv": "modulo6b_masking.csv",
        "label": "SpliceAI (5 modelos, promediados)",
        "note": "un solo predictor promediado sobre sus 5 réplicas, NO es un ensemble de herramientas",
    },
    "pangolin": {
        "csv": "modulo6b_masking_pangolin.csv",
        "label": "Pangolin (4 tejidos × 5 réplicas, promediados)",
        "note": (
            "ninguno de los 4 tejidos es retina; devuelve UNA probabilidad de "
            "'es sitio de splicing', sin separar donador de aceptor"
        ),
    },
}
DEFAULT_PREDICTOR = "spliceai"

_cache: dict[str, dict] = {}

# El `*_meta.json` que escribe run_masking.py guarda el baseline con las claves
# en español del pipeline. El resto de este payload usa claves en inglés
# (`donor_cryptic`, `delta_donor`, ...), así que se traduce acá para no exponer
# dos idiomas en la misma respuesta.
#
# No es cosmético: mientras el baseline salió en español, el frontend leía
# `baseline.acceptor_cryptic` como `undefined` y `.toFixed()` tiraba abajo toda
# la app al abrir la pestaña (2026-07-31). TypeScript no lo vio porque el tipo
# declarado decía inglés y nadie lo contrastó contra la API real.
_BASELINE_KEYS = {
    "donador_criptico": "donor_cryptic",
    "aceptor_criptico": "acceptor_cryptic",
    "donador_canonico_e3": "donor_canonical_e3",
    "aceptor_canonico_e3": "acceptor_canonical_e3",
}


def _baseline_en(meta: dict) -> dict:
    """Baseline con las mismas claves en inglés que usa el resto del payload."""
    raw = meta.get("baseline", {}) or {}
    out = {_BASELINE_KEYS.get(k, k): v for k, v in raw.items()}
    faltan = set(_BASELINE_KEYS.values()) - set(out)
    if faltan:
        raise HTTPException(
            500,
            f"el baseline del meta no trae {sorted(faltan)}; regenerá el CSV con "
            "run_masking.py",
        )
    return out


def _load(predictor: str) -> dict:
    """Carga CSV + meta de un predictor. El meta trae baseline y controles MEDIDOS
    en la misma corrida — no hay constantes escritas a mano en este router."""
    if predictor in _cache:
        return _cache[predictor]

    spec = PREDICTORS[predictor]
    csv_path = os.path.join(_RESULTS_DIR, spec["csv"])
    meta_path = csv_path.replace(".csv", "_meta.json")

    if not os.path.exists(csv_path):
        raise HTTPException(
            503,
            f"Faltan los resultados del Módulo 6b para {predictor}. Se generan con "
            f"`python pipeline/run_masking.py --predictor {predictor}` "
            f"(49 inferencias, minutos en CPU) y quedan en "
            f"{os.path.relpath(csv_path, _REPO_ROOT)}. Ver el README.",
        )

    meta = {}
    if os.path.exists(meta_path):
        with open(meta_path, encoding="utf-8") as fh:
            meta = json.load(fh)

    baseline = meta.get("baseline", {})
    base_donor = baseline.get("donador_criptico")

    rows = []
    with open(csv_path, encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            score = float(r["donador_criptico"])
            # La clasificación del CSV y la recalculada tienen que coincidir; si no,
            # el CSV se generó con otro criterio y servirlo sería engañoso.
            if "clasificacion" in r and base_donor:
                recalc = classify(score, base_donor)
                if recalc != r["clasificacion"]:
                    raise HTTPException(
                        500,
                        f"{predictor}/{r['candidato']}: el CSV dice "
                        f"'{r['clasificacion']}' y el criterio vigente dice "
                        f"'{recalc}'. Regenerá el CSV con run_masking.py.",
                    )
            rows.append({
                "name": r["candidato"],
                "start_rel": int(r["start_rel"]),
                "end_rel": int(r["end_rel"]),
                "covers_donor": r["cubre_donador"] == "True",
                "donor_cryptic": score,
                "delta_donor": float(r["delta_donador"]),
                "retention_donor": (
                    float(r["retencion_donador"]) if "retencion_donador" in r
                    else (score / base_donor if base_donor else None)
                ),
                "acceptor_cryptic": float(r["aceptor_criptico"]),
                "delta_acceptor": float(r["delta_aceptor"]),
                "retention_acceptor": (
                    float(r["retencion_aceptor"]) if "retencion_aceptor" in r else None
                ),
                "donor_canonical_e3": float(r["donador_canonico_e3"]),
                "delta_canonical": float(r["delta_canonico"]),
                "classification": r.get("clasificacion") or classify(score, base_donor),
                "verdict": r.get("veredicto"),
                "borders_abolished": [b for b in (r.get("bordes_anulados") or "").split("+") if b],
                "retention_canonical": (
                    float(r["retencion_canonico"]) if "retencion_canonico" in r else None
                ),
            })

    out = {"rows": rows, "meta": meta, "spec": spec}
    _cache[predictor] = out
    return out


@router.get("")
def get_aso_masking(classification: str | None = None, predictor: str = DEFAULT_PREDICTOR):
    """Efecto de cada candidato sobre los sitios crípticos, por enmascarado con N.

    NO es una medición de eficacia: el enmascarado es binario y total (asume
    ocupación del 100 % y bloqueo perfecto). Condición necesaria, no suficiente.
    Ver wiki/decisiones/0008 y 0010.
    """
    if predictor not in PREDICTORS:
        raise HTTPException(400, f"predictor debe ser uno de {sorted(PREDICTORS)}")

    valid = {"bloquea", "contraproducente", "sin_efecto"}
    if classification is not None and classification not in valid:
        raise HTTPException(400, f"classification debe ser uno de {sorted(valid)}")

    data = _load(predictor)
    rows, meta, spec = data["rows"], data["meta"], data["spec"]
    counts = {k: sum(1 for r in rows if r["classification"] == k) for k in valid}
    verdict_counts = {
        v: sum(1 for r in rows if r["verdict"] == v) for v in (USEFUL, INEFFECTIVE, HARMFUL)
    }
    shown = [r for r in rows if classification is None or r["classification"] == classification]

    return {
        "predictor": {
            "id": predictor,
            "label": spec["label"],
            "note": spec["note"],
            "available": sorted(PREDICTORS),
        },
        "method": (
            "la ventana del ASO se reemplaza por N, que la codificación one-hot de "
            "ambos predictores mapea al vector nulo — proxy del bloqueo estérico de un PMO"
        ),
        "limitation": (
            "enmascarado binario y total: asume ocupación del 100 % y bloqueo perfecto. "
            "Un ASO real tiene afinidad finita y compite con proteínas de unión a ARN. "
            "Condición necesaria, no suficiente. No validado en célula."
        ),
        "baseline": _baseline_en(meta),
        "controls": meta.get("controls", []),
        "thresholds": {
            "block_retention": BLOCK_RETENTION,
            "counterproductive_gain": COUNTERPRODUCTIVE_GAIN,
            "note": (
                "criterio relativo al baseline del predictor: bloquea si el sitio "
                f"retiene menos del {BLOCK_RETENTION:.0%} de su señal original. Un "
                "umbral absoluto no serviría porque las dos escalas difieren."
            ),
        },
        "sites": {
            "donor_cryptic_offset": 1,
            "acceptor_cryptic_offset": -89,
            "pseudoexon_size": 91,
            "pseudoexon_note": "coincide con PE1b (91 pb) medido por minigén en Peng et al. 2025",
        },
        "verdict": {
            "counts": verdict_counts,
            "useful": [r for r in rows if r["verdict"] == USEFUL],
            "criterion": (
                "un pseudoexón necesita que la maquinaria reconozca sus DOS bordes "
                "(aceptor = dónde empieza, donador = dónde termina). Anular CUALQUIERA "
                "de los dos lo elimina — como una grapa: alcanza con romper una pata. "
                f"Y el donador canónico del exón 3 debe retener ≥{CANONICAL_SAFE_RETENTION:.0%} "
                "de su señal: si el ASO lo dañara, arreglaría el pseudoexón rompiendo el "
                "splicing normal."
            ),
            "why_it_matters": (
                "mirar solo el donador subestima los candidatos útiles: 7 candidatos que "
                "el criterio por sitio llama 'sin_efecto' aniquilan el ACEPTOR sin cubrirlo, "
                "cayendo sobre el tracto de polipirimidina 9-14 nt aguas arriba"
            ),
        },
        "total": len(rows),
        "counts": counts,
        "counts_note": (
            "`counts` es la clasificación por SITIO (solo el donador críptico), que es la "
            "métrica de la corrida publicada del 2026-07-30. La conclusión del módulo es "
            "`verdict`, a nivel pseudoexón."
        ),
        "candidates_covering_acceptor": sum(1 for r in rows if r["start_rel"] <= -89 < r["end_rel"]),
        "acceptor_gap_note": (
            "ningún candidato final CUBRE el aceptor críptico: del barrido, 20 lo cubrían, "
            "16 cayeron en filtros heurísticos y 4 en termodinámica. Esto se documentó como "
            "limitación hasta el 2026-07-30, cuando dejó de serlo: 7 candidatos lo ANULAN "
            "sin cubrirlo (retención 0,009-0,077 en SpliceAI y 0,002-0,034 en Pangolin), "
            "porque caen sobre el tracto de polipirimidina 9-14 nt aguas arriba, que el "
            "aceptor necesita para ser reconocido. Cubrir un sitio no es la única forma de "
            "anularlo. Ver el campo `verdict`."
        ),
        "candidates": shown,
    }


@router.get("/agreement")
def get_predictor_agreement():
    """Concordancia de clasificación entre los dos predictores, candidato por candidato.

    Es el resultado del Módulo 6c aplicado al 6b: dos herramientas independientes
    revalidando el mismo enmascarado. Los desacuerdos se exponen con nombre, no se
    resumen en un porcentaje.
    """
    loaded = {}
    for p in PREDICTORS:
        try:
            loaded[p] = _load(p)
        except HTTPException:
            continue

    if len(loaded) < 2:
        raise HTTPException(
            503,
            "La concordancia necesita los dos CSV. Falta: "
            + ", ".join(sorted(set(PREDICTORS) - set(loaded))),
        )

    by_pred = {p: {r["name"]: r for r in d["rows"]} for p, d in loaded.items()}
    names = sorted(set.intersection(*(set(v) for v in by_pred.values())))

    per_candidate, agree = [], 0
    for nm in names:
        a, b = by_pred["spliceai"][nm], by_pred["pangolin"][nm]
        same_verdict = a["verdict"] == b["verdict"]
        same_class = a["classification"] == b["classification"]
        agree += same_verdict
        per_candidate.append({
            "name": nm,
            "start_rel": a["start_rel"],
            "covers_donor": a["covers_donor"],
            "spliceai": {
                "donor_cryptic": a["donor_cryptic"],
                "retention_donor": a["retention_donor"],
                "retention_acceptor": a["retention_acceptor"],
                "classification": a["classification"],
                "verdict": a["verdict"],
                "borders_abolished": a["borders_abolished"],
            },
            "pangolin": {
                "donor_cryptic": b["donor_cryptic"],
                "retention_donor": b["retention_donor"],
                "retention_acceptor": b["retention_acceptor"],
                "classification": b["classification"],
                "verdict": b["verdict"],
                "borders_abolished": b["borders_abolished"],
            },
            "agree": same_verdict,
            "agree_by_site": same_class,
        })

    agree_site = sum(1 for c in per_candidate if c["agree_by_site"])
    return {
        "n_compared": len(names),
        "n_agree": agree,
        "agreement_fraction": round(agree / len(names), 4) if names else None,
        "n_agree_by_site": agree_site,
        "agreement_fraction_by_site": round(agree_site / len(names), 4) if names else None,
        "disagreements": [c for c in per_candidate if not c["agree"]],
        "disagreements_by_site": [c for c in per_candidate if not c["agree_by_site"]],
        "baseline": {p: _baseline_en(d["meta"]) for p, d in loaded.items()},
        "note": (
            "la concordancia se mide sobre el VEREDICTO (anula el pseudoexón / sin "
            "efecto / daña el canónico), no sobre el score: las dos escalas no son "
            "comparables en magnitud. `*_by_site` es la concordancia del criterio más "
            "estrecho, que mira solo el donador críptico, y es MENOR — la diferencia "
            "entre las dos es el resultado interesante. Ver wiki/decisiones/0009 y 0012."
        ),
        "limitation": (
            "los dos modelos se entrenaron en buena parte sobre las mismas bases "
            "públicas de anotaciones, así que su acuerdo no es del todo independiente. "
            "Y ninguno tiene modelo de retina."
        ),
        "per_candidate": per_candidate,
    }
