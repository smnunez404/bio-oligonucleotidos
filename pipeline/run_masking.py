"""Módulo 6b — corre el enmascarado de los 44 candidatos con el predictor elegido.

Este runner NO existía: la corrida original del 6b se hizo con un script de sesión
que se perdió, así que `data/results/modulo6b_masking.csv` no era regenerable. Eso
es exactamente el problema que un revisor pediría arreglar.

Uso:
    # SpliceAI (entorno `spliceai`)
    PYTHONPATH=. python pipeline/run_masking.py --predictor spliceai

    # Pangolin (entorno `pangolin`, necesita la variable de entorno)
    KMP_AFFINITY=disabled PYTHONPATH=. python pipeline/run_masking.py --predictor pangolin

Los dos predictores viven en entornos separados y no pueden convivir (TensorFlow vs
PyTorch): hay que correr el script dos veces, una por entorno. Ver el README.

ORDEN DE OPERACIONES, y por qué importa
---------------------------------------
1. Se corren los 4 CONTROLES del método.
2. Si algún control falla, el script ABORTA sin escribir el CSV.
3. Solo entonces se corren los 44 candidatos.
Así no puede existir un CSV de resultados cuyo método no haya sido validado en la
misma corrida y con el mismo predictor.
"""

from __future__ import annotations

import argparse
import csv
import functools
import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pipeline.aso_masking import (  # noqa: E402
    BLOCK_RETENTION,
    CANONICAL_SAFE_RETENTION,
    HARMFUL,
    INEFFECTIVE,
    USEFUL,
    CallableScorer,
    classify,
    evaluate_masks,
)
from pipeline.sequence import fetch_target_region  # noqa: E402

WINDOWS_JSON = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "data", "results", "modulo6b_windows.json",
)
"""Ventanas de los candidatos que sobrevivieron el embudo Módulo 2 -> 3 -> 4.

POR QUÉ ES UN ARCHIVO Y NO SE CALCULA ACÁ: el embudo necesita ViennaRNA (Módulo 4),
que vive en el entorno `bio-oligo`; el enmascarado necesita los pesos del predictor,
que viven en `spliceai` o `pangolin`. Los tres entornos son disjuntos y no pueden
convivir (TensorFlow vs PyTorch vs ViennaRNA), así que el embudo se materializa una
vez con `--emit-windows` desde `bio-oligo` y los dos predictores leen el MISMO
archivo. Ventaja secundaria: los dos predictores evalúan exactamente las mismas 44
ventanas por construcción, no por coincidencia.
"""


def emit_windows(region) -> list[dict]:
    """Reproduce el embudo Módulo 2 -> 3 -> 4 y devuelve las ventanas. Requiere `bio-oligo`.

    Mismos parámetros que la corrida original (bitácora 2026-07-30): ventana de
    20 nt, paso de 1, flanco de 200 nt. Los candidatos se nombran `cand_<start>`
    con el offset ABSOLUTO en la región, así que el nombre solo es estable si el
    padding es el mismo — de ahí que PADDING esté fijo y documentado.
    """
    from pipeline.heuristic_filters import apply_heuristic_filters
    from pipeline.oligo_walk import generate_oligo_walk
    from pipeline.thermodynamics import analyze_candidates

    cands = generate_oligo_walk(
        region.mutant_sense,
        region.variant_offset_sense,
        length=20,
        step=1,
        flank=200,
        intron_bounds=region.intron2_bounds_sense,
    )
    kept = [f.candidate for f in apply_heuristic_filters(cands) if f.passed]
    thermo = analyze_candidates(kept, target_sequence=region.mutant_sense)
    survivors = [t.candidate for t in thermo if getattr(t, "passed", True)]
    return [
        {"name": f"cand_{c.start}", "start": c.start, "end": c.end,
         "aso_sequence": c.aso_sequence}
        for c in sorted(survivors, key=lambda c: c.start)
    ]


def load_windows(region) -> list[dict]:
    """Lee las ventanas del archivo y verifica que correspondan a esta región."""
    if not os.path.exists(WINDOWS_JSON):
        raise SystemExit(
            f"Falta {os.path.relpath(WINDOWS_JSON, REPO_ROOT)}. Generalo primero desde\n"
            "el entorno `bio-oligo` (el único con ViennaRNA):\n"
            "    PYTHONPATH=. python pipeline/run_masking.py --emit-windows"
        )
    with open(WINDOWS_JSON, encoding="utf-8") as fh:
        blob = json.load(fh)
    if blob["padding"] != PADDING or blob["variant_offset"] != region.variant_offset_sense:
        raise SystemExit(
            f"Las ventanas de {os.path.relpath(WINDOWS_JSON, REPO_ROOT)} se generaron con "
            f"padding={blob['padding']} / variante en {blob['variant_offset']}, y esta "
            f"región tiene padding={PADDING} / variante en {region.variant_offset_sense}. "
            "Las coordenadas no corresponden: regeneralas con --emit-windows."
        )
    return blob["windows"]

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RESULTS_DIR = os.path.join(REPO_ROOT, "data", "results")

DONOR_CRYPTIC = "donador_criptico"
ACCEPTOR_CRYPTIC = "aceptor_criptico"
DONOR_CANONICAL_E3 = "donador_canonico_e3"
ACCEPTOR_CANONICAL_E3 = "aceptor_canonico_e3"

SITE_OFFSETS = {
    DONOR_CRYPTIC: (1, "donor"),
    ACCEPTOR_CRYPTIC: (-89, "acceptor"),
    DONOR_CANONICAL_E3: (536, "donor"),
    ACCEPTOR_CANONICAL_E3: (395, "acceptor"),
}
"""Sitio -> (offset relativo a la variante, tipo). Offsets del Módulo 1/6."""

# Controles del método. Cada uno es (nombre, offset_inicio, largo, qué se espera).
CONTROL_SPECS = [
    ("ctrl_far_upstream", -300, 20, "sin efecto sobre el donador críptico"),
    ("ctrl_far_downstream", 300, 20, "sin efecto sobre el donador críptico"),
    ("ctrl_on_donor", -8, 20, "anula el donador críptico"),
    ("ctrl_on_canonical_e3", 527, 20, "anula el donador canónico del E3, no el críptico"),
]
"""Los offsets son los de la corrida original del 6b (bitácora 2026-07-30), para
que los controles sean literalmente los mismos y no unos parecidos."""


def _check_controls(baseline, effects_by_name) -> list[dict]:
    """Verifica los 4 controles y devuelve su detalle. Lanza si alguno falla."""
    out, failures = [], []
    b_don = baseline[DONOR_CRYPTIC]
    b_can = baseline[DONOR_CANONICAL_E3]

    for name, _off, _ln, expected in CONTROL_SPECS:
        eff = effects_by_name[name]
        ret_don = eff.retention[DONOR_CRYPTIC]
        ret_can = eff.retention[DONOR_CANONICAL_E3]

        if name.startswith("ctrl_far"):
            ok = ret_don > 0.9
        elif name == "ctrl_on_donor":
            ok = ret_don < BLOCK_RETENTION
        else:  # ctrl_on_canonical_e3: efecto local
            ok = ret_can < BLOCK_RETENTION and ret_don > ret_can

        out.append({
            "name": name, "label": expected,
            "donor_cryptic": round(eff.scores[DONOR_CRYPTIC], 4),
            "delta_donor": round(eff.deltas[DONOR_CRYPTIC], 4),
            "retention_donor": round(ret_don, 4),
            "donor_canonical_e3": round(eff.scores[DONOR_CANONICAL_E3], 4),
            "retention_canonical": round(ret_can, 4),
            "expected": expected, "ok": bool(ok),
        })
        if not ok:
            failures.append(name)

    print(f"\n  baseline: donador críptico {b_don:.4f} | canónico E3 {b_can:.4f}")
    for c in out:
        mark = "OK " if c["ok"] else "FALLA"
        print(f"  [{mark}] {c['name']:24s} ret_donador={c['retention_donor']:.3f} "
              f"ret_canónico={c['retention_canonical']:.3f}  ({c['expected']})")

    if failures:
        raise SystemExit(
            f"\nABORTA: los controles {failures} no pasaron con este predictor.\n"
            "No se escribe el CSV: un resultado cuyo método no valida no sirve."
        )
    return out


def build_spliceai_scorer(region, models=None, weights="spliceai"):
    """Adaptador de la arquitectura SpliceAI-10k. Requiere el entorno `spliceai`.

    `weights` elige el juego de pesos (ver `pipeline.splice_neural.WEIGHT_SETS`):
    `spliceai` (Illumina), `retina` (Retina-SpliceAI, el único con el tejido
    correcto para una distrofia retiniana) o `gtex` (control del mismo trabajo,
    misma arquitectura y procedimiento pero sin retina). Los tres comparten
    arquitectura, así que el adaptador es el mismo.
    """
    from pipeline.splice_neural import CH_ACCEPTOR, CH_DONOR, CONTEXT, predict_scores

    models = models if models is not None else __import__(
        "pipeline.splice_neural", fromlist=["load_models"]
    ).load_models(weights)

    ch = {"donor": CH_DONOR, "acceptor": CH_ACCEPTOR}
    v = region.variant_offset_sense
    # Recorte para ahorrar cómputo: SpliceAI solo usa CONTEXT/2 por lado, así que
    # más allá de eso el score de los sitios evaluados no cambia.
    half = CONTEXT // 2
    offs = [v + o for o, _ in SITE_OFFSETS.values()]
    lo = max(0, min(offs) - half - 600)
    hi = min(len(region.mutant_sense), max(offs) + half + 600)

    def score(seq: str) -> dict[str, float]:
        p = predict_scores(seq[lo:hi], models=models)
        return {
            nm: float(p[v + off - lo, ch[kind]])
            for nm, (off, kind) in SITE_OFFSETS.items()
        }

    return CallableScorer(name=weights, fn=score)


def build_pangolin_scorer(region, models=None):
    """Adaptador de Pangolin. Requiere el entorno `pangolin` y KMP_AFFINITY=disabled.

    Pangolin devuelve UNA probabilidad de "es sitio de splicing" — no separa
    donador de aceptor. Así que el mismo array sirve para los cuatro sitios y el
    campo `kind` se ignora. Eso es una diferencia de método, no un atajo: ver
    wiki/decisiones/0009.
    """
    from pipeline.pangolin_cross import (
        CONTEXT_NT,
        MODEL_NUMS,
        offset_to_index,
        require_affinity_disabled,
    )
    from pipeline.run_pangolin_cross import load_models as _load, score as _score

    require_affinity_disabled()
    models = models if models is not None else _load()
    v = region.variant_offset_sense

    def score(seq: str) -> dict[str, float]:
        # Promedio de los 4 tejidos: ninguno es retina, así que ninguno tiene
        # prioridad. Ver la limitación declarada en el ADR 0009.
        per_tissue = [_score(seq, models[mn], mn) for mn in MODEL_NUMS]
        mean = [sum(vals) / len(vals) for vals in zip(*per_tissue)]
        return {
            nm: float(mean[offset_to_index(off, v)])
            for nm, (off, _kind) in SITE_OFFSETS.items()
        }

    return CallableScorer(name="pangolin", fn=score)


BUILDERS = {
    "spliceai": build_spliceai_scorer,
    "pangolin": build_pangolin_scorer,
    # Mismo adaptador, distintos pesos. Ver build_spliceai_scorer.
    "retina": functools.partial(build_spliceai_scorer, weights="retina"),
    "gtex": functools.partial(build_spliceai_scorer, weights="gtex"),
}

# Padding de la región. Es el de la corrida original del 6b, y no se toca por dos
# razones: (1) los candidatos se nombran por su offset absoluto (`cand_5992`), así
# que otro padding renombraría todo y rompería la comparación uno a uno contra el
# CSV de SpliceAI; (2) Pangolin necesita CONTEXT_NT=5000 a cada lado de CADA sitio
# evaluado, y con 6000 el sitio más lejano (+536) cae en el índice 1536 de 2001
# scores — entra con margen. Con el padding por defecto de fetch_target_region la
# región sería demasiado corta y Pangolin devolvería un puñado de scores.
PADDING = 6000


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--predictor", choices=sorted(BUILDERS))
    ap.add_argument(
        "--emit-windows", action="store_true",
        help="solo materializa las ventanas del embudo (requiere el entorno bio-oligo)",
    )
    ap.add_argument("--out", default=None, help="CSV de salida (default: por predictor)")
    args = ap.parse_args()

    if args.emit_windows:
        region = fetch_target_region(padding=PADDING)
        windows = emit_windows(region)
        os.makedirs(RESULTS_DIR, exist_ok=True)
        with open(WINDOWS_JSON, "w", encoding="utf-8") as fh:
            json.dump(
                {"padding": PADDING, "variant_offset": region.variant_offset_sense,
                 "region_nt": len(region.mutant_sense), "n": len(windows),
                 "windows": windows},
                fh, indent=1,
            )
        print(f"{len(windows)} ventanas -> {os.path.relpath(WINDOWS_JSON, REPO_ROOT)}")
        return

    if not args.predictor:
        raise SystemExit("hace falta --predictor (o --emit-windows)")

    out_csv = args.out or os.path.join(
        RESULTS_DIR,
        "modulo6b_masking.csv" if args.predictor == "spliceai"
        else f"modulo6b_masking_{args.predictor}.csv",
    )

    print(f"Módulo 6b — enmascarado con {args.predictor}")
    region = fetch_target_region(padding=PADDING)
    v = region.variant_offset_sense
    print(f"  región: {len(region.mutant_sense)} nt | variante en índice {v}")

    candidates = load_windows(region)
    print(f"  candidatos tras heurísticos + termodinámica: {len(candidates)}")

    # Ventanas: primero los controles, después los candidatos.
    windows = [(nm, v + off, v + off + ln) for nm, off, ln, _ in CONTROL_SPECS]
    windows += [(c["name"], c["start"], c["end"]) for c in candidates]

    scorer = BUILDERS[args.predictor](region)
    t0 = time.time()
    print(f"  corriendo {len(windows) + 1} inferencias...", flush=True)
    baseline, effects = evaluate_masks(region.mutant_sense, scorer, windows)
    print(f"  listo en {time.time() - t0:.0f}s")

    by_name = {e.name: e for e in effects}
    controls = _check_controls(baseline, by_name)

    cand_effects = [by_name[c["name"]] for c in candidates]

    os.makedirs(RESULTS_DIR, exist_ok=True)
    with open(out_csv, "w", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh)
        w.writerow([
            "candidato", "start_abs", "start_rel", "end_rel", "cubre_donador",
            "veredicto", "bordes_anulados",
            "clasificacion",
            "donador_criptico", "delta_donador", "retencion_donador",
            "aceptor_criptico", "delta_aceptor", "retencion_aceptor",
            "donador_canonico_e3", "delta_canonico", "retencion_canonico",
        ])
        for eff in cand_effects:
            donor_abs = v + SITE_OFFSETS[DONOR_CRYPTIC][0]
            verdict, borders = eff.verdict(
                donor_site=DONOR_CRYPTIC,
                acceptor_site=ACCEPTOR_CRYPTIC,
                canonical_site=DONOR_CANONICAL_E3,
            )
            w.writerow([
                eff.name, eff.start, eff.start - v, eff.end - v,
                eff.start <= donor_abs < eff.end,
                verdict, "+".join(borders),
                eff.classification(DONOR_CRYPTIC),
                f"{eff.scores[DONOR_CRYPTIC]:.4f}",
                f"{eff.deltas[DONOR_CRYPTIC]:+.4f}",
                f"{eff.retention[DONOR_CRYPTIC]:.4f}",
                f"{eff.scores[ACCEPTOR_CRYPTIC]:.4f}",
                f"{eff.deltas[ACCEPTOR_CRYPTIC]:+.4f}",
                f"{eff.retention[ACCEPTOR_CRYPTIC]:.4f}",
                f"{eff.scores[DONOR_CANONICAL_E3]:.4f}",
                f"{eff.deltas[DONOR_CANONICAL_E3]:+.4f}",
                f"{eff.retention[DONOR_CANONICAL_E3]:.4f}",
            ])

    meta = {
        "predictor": scorer.name,
        "padding": PADDING,
        "region_nt": len(region.mutant_sense),
        "variant_offset": v,
        "baseline": {k: round(vv, 4) for k, vv in baseline.items()},
        "controls": controls,
        "block_retention": BLOCK_RETENTION,
        "canonical_safe_retention": CANONICAL_SAFE_RETENTION,
        "n_candidates": len(cand_effects),
        # Por SITIO (donador críptico). Se conserva porque es la métrica de la
        # corrida publicada del 2026-07-30, pero NO es la conclusión del módulo.
        "distribution_donor_only": {
            cl: sum(1 for e in cand_effects if e.classification(DONOR_CRYPTIC) == cl)
            for cl in ("bloquea", "sin_efecto", "contraproducente")
        },
        # A nivel PSEUDOEXÓN: la métrica que responde la pregunta del proyecto.
        "distribution": {
            vd: sum(
                1 for e in cand_effects
                if e.verdict(donor_site=DONOR_CRYPTIC, acceptor_site=ACCEPTOR_CRYPTIC,
                             canonical_site=DONOR_CANONICAL_E3)[0] == vd
            )
            for vd in (USEFUL, INEFFECTIVE, HARMFUL)
        },
        "useful_candidates": [
            {
                "name": e.name,
                "start_rel": e.start - v,
                "end_rel": e.end - v,
                "borders": e.verdict(donor_site=DONOR_CRYPTIC, acceptor_site=ACCEPTOR_CRYPTIC,
                                     canonical_site=DONOR_CANONICAL_E3)[1],
                "retention_donor": round(e.retention[DONOR_CRYPTIC], 4),
                "retention_acceptor": round(e.retention[ACCEPTOR_CRYPTIC], 4),
                "retention_canonical": round(e.retention[DONOR_CANONICAL_E3], 4),
            }
            for e in cand_effects
            if e.verdict(donor_site=DONOR_CRYPTIC, acceptor_site=ACCEPTOR_CRYPTIC,
                         canonical_site=DONOR_CANONICAL_E3)[0] == USEFUL
        ],
    }
    meta_path = out_csv.replace(".csv", "_meta.json")
    with open(meta_path, "w", encoding="utf-8") as fh:
        json.dump(meta, fh, indent=1, ensure_ascii=False)

    print(f"\n  por sitio (solo donador críptico): {meta['distribution_donor_only']}")
    print(f"  a nivel pseudoexón:                {meta['distribution']}")
    for c in meta["useful_candidates"]:
        print(f"    {c['name']} rel={c['start_rel']:+5d}..{c['end_rel']:+d} "
              f"anula {'+'.join(c['borders']):16s} canónico intacto {c['retention_canonical']:.3f}")
    print(f"  CSV:  {os.path.relpath(out_csv, REPO_ROOT)}")
    print(f"  meta: {os.path.relpath(meta_path, REPO_ROOT)}")


if __name__ == "__main__":
    main()
