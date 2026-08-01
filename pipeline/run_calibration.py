"""Corre la calibración del ADR 0002 con el juego de pesos elegido.

QUÉ HACE
--------
Puntúa los 32 AONs de Kaltak et al. 2023 (variante ABCA4 c.5461-10T>C, intrón 38)
con el criterio de enmascarado del pipeline, y mide si los AONs de eficacia
publicada quedan arriba del ranking.

La primera corrida (SpliceAI, 2026-08-01) dio los 5 conocidos en las posiciones
1, 3, 4, 5 y 6 de 32, AUC 0,974. Ver
wiki/bitacora/2026-08-01-calibracion-kaltak-el-metodo-discrimina.

POR QUÉ IMPORTA REPETIRLO CON OTROS PESOS
------------------------------------------
Si la discriminación se sostiene con **Retina-SpliceAI** —el único predictor
entrenado sobre el tejido correcto— la calibración vale mucho más. Y el juego
`gtex` del mismo trabajo es el control que permite atribuir cualquier diferencia
al tejido y no al procedimiento de entrenamiento.

CÓMO CORRERLO
-------------
    KMP_AFFINITY=disabled PYTHONPATH=. conda run -n spliceai \\
        python pipeline/run_calibration.py --predictor retina

Tarda ~6 min por predictor en CPU (33 inferencias de 12 kb).

CONTROLES QUE CORRE ANTES DE PUNTUAR NADA
------------------------------------------
1. El alelo de referencia en la coordenada tiene que coincidir (lo valida
   `fetch_calibration_region`, que aborta si no).
2. El pico aceptor más alto debe caer en **+10** respecto de la variante — la
   variante se llama `c.5461-10`, así que esa posición es una verificación
   independiente de la coordenada. Si no cae ahí, el script ABORTA: puntuar
   contra el sitio equivocado daría números plausibles y sin sentido.
3. Los 32 AONs tienen que ubicarse dentro de la región descargada.
"""

from __future__ import annotations

import argparse
import json
import os
import sys

from pipeline.aso_masking import mask_window
from pipeline.calibration import (
    BEST_AON,
    KNOWN_EFFECTIVE,
    build_windows,
    fetch_calibration_region,
    load_aons,
    rank_summary,
)

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RESULTS_DIR = os.path.join(REPO_ROOT, "data", "results")

# El aceptor del exón 39, en coordenadas relativas a la variante. No es una
# elección: se verifica contra el perfil real antes de usarlo (control 2).
ACCEPTOR_OFFSET = 10
# Los AONs que TAPAN ese aceptor lo anulan, que es trivialmente malo. Se marcan
# para poder repetir la estadística sin ellos (análisis de sensibilidad).
MIN_ACCEPTOR_SCORE = 0.80


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--predictor", default="spliceai", choices=["spliceai", "retina", "gtex"])
    ap.add_argument("--padding", type=int, default=6000)
    ap.add_argument("--out", default=None)
    args = ap.parse_args()

    from pipeline.splice_neural import CH_ACCEPTOR, load_models, predict_scores

    print(f"Calibración ADR 0002 — pesos: {args.predictor}", flush=True)

    region = fetch_calibration_region(padding=args.padding)
    v = region.variant_offset_sense
    print(f"  región {len(region.mutant_sense)} nt | variante en {v}", flush=True)

    aons = load_aons()
    windows, missing = build_windows(region, aons)
    if missing:
        print(f"ABORTA: {len(missing)} AONs fuera de la región: {missing}", file=sys.stderr)
        return 1
    print(f"  {len(windows)} AONs ubicados", flush=True)

    models = load_models(args.predictor)

    # --- control 2: ¿el aceptor del exón 39 está donde debe? ---
    p_wt = predict_scores(region.wildtype_sense, models)
    acc = v + ACCEPTOR_OFFSET
    pico = max(range(v - 5, v + 40), key=lambda i: p_wt[i, CH_ACCEPTOR])
    score_acc = float(p_wt[acc, CH_ACCEPTOR])
    print(
        f"  control: pico aceptor en {pico - v:+d} (esperado +{ACCEPTOR_OFFSET}), "
        f"score {score_acc:.4f}",
        flush=True,
    )
    if pico != acc or score_acc < MIN_ACCEPTOR_SCORE:
        print(
            f"ABORTA: el aceptor del exón 39 no se reconoce con estos pesos "
            f"(pico en {pico - v:+d}, score {score_acc:.4f}). Puntuar contra el sitio "
            "equivocado produciría números plausibles y sin sentido.",
            file=sys.stderr,
        )
        return 1

    base = float(predict_scores(region.mutant_sense, models)[acc, CH_ACCEPTOR])
    print(f"  baseline (mutante) = {base:.4f}\n", flush=True)

    res = {}
    for i, (name, s, e) in enumerate(windows, 1):
        sc = float(predict_scores(mask_window(region.mutant_sense, s, e), models)[acc, CH_ACCEPTOR])
        res[name] = {
            "score": round(sc, 4),
            "delta": round(sc - base, 4),
            "retencion": round(sc / base, 4) if base else None,
            "start_rel": s - v,
            "end_rel": e - v,
            "largo": e - s,
            "conocido_eficaz": name in KNOWN_EFFECTIVE,
            "tapa_aceptor": s - v <= ACCEPTOR_OFFSET < e - v,
        }
        print(f"  [{i:2}/{len(windows)}] {name:7} {sc:.4f} delta={sc - base:+.4f}", flush=True)

    deltas = {n: r["delta"] for n, r in res.items()}
    resumen = rank_summary(deltas, higher_is_better=True)
    sin_obvios = {n: r["delta"] for n, r in res.items() if not r["tapa_aceptor"]}
    sensibilidad = rank_summary(sin_obvios, higher_is_better=True)

    out = args.out or os.path.join(RESULTS_DIR, f"calibracion_kaltak_{args.predictor}.json")
    os.makedirs(RESULTS_DIR, exist_ok=True)
    with open(out, "w", encoding="utf-8") as fh:
        json.dump(
            {
                "predictor": args.predictor,
                "baseline": base,
                "acceptor_offset": ACCEPTOR_OFFSET,
                "aons": res,
                "resumen": resumen,
                "sensibilidad_sin_los_que_tapan_el_aceptor": sensibilidad,
            },
            fh,
            indent=2,
            ensure_ascii=False,
        )

    print(f"\n  posiciones de los {len(KNOWN_EFFECTIVE)} conocidos: {resumen['posiciones']}")
    print(f"  {BEST_AON} (QR-1011) en posición {resumen['mejor_aon_posicion']} de {len(res)}")
    print(f"  AUC = {resumen['AUC']:.3f}  |  sin los obvios = {sensibilidad['AUC']:.3f}")
    print(f"  -> {os.path.relpath(out, REPO_ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
