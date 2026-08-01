"""Compara los sitios de splicing entre juegos de pesos — genera `retina_comparacion.json`.

POR QUÉ EXISTE
--------------
Corrige **CRIT-6** de la revisión adversarial. El archivo original se produjo con
un script de sesión que nunca se versionó, y tenía **los sitios canónicos mal
etiquetados**: lo que llamaba `donador_canonico_e3` estaba en el offset −999,
que es el borde del **exón 2**, y lo que llamaba `aceptor_canonico_e2` estaba en
+395, que es el aceptor del **exón 3**. Los nombres estaban cruzados.

Consecuencia del error: la normalización del bloque E del dossier se hizo contra
el sitio equivocado. Este script deja los nombres derivados de la geometría real
en vez de escritos a mano, así que el error no puede repetirse.

GEOMETRÍA (verificable, no asumida)
------------------------------------
ABCA4 está en hebra menos, y la región se trabaja en sentido del transcrito. En
ese sentido el orden es: exón 2 → intrón 2 → exón 3.

- El **donador** del intrón 2 está en el borde 5' del intrón: última base exónica
  del exón 2. En coordenadas relativas a la variante cae en **−999**.
- El **aceptor** del intrón 2 está en el borde 3': primera base del exón 3. Cae
  en **+395** — que coincide con el "−395" del nombre HGVS `c.161-395G>A`, y es
  por eso una verificación independiente de la coordenada.

El script **aborta** si esos offsets no son los esperados.

CÓMO CORRERLO
-------------
    KMP_AFFINITY=disabled PYTHONPATH=. conda run -n spliceai \\
        python pipeline/run_site_comparison.py

Corre los tres juegos de pesos (~1 min cada uno) y escribe
`data/results/retina_comparacion.json`.
"""

from __future__ import annotations

import argparse
import json
import os
import sys

from pipeline.sequence import fetch_target_region

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_OUT = os.path.join(REPO_ROOT, "data", "results", "retina_comparacion.json")

# Offsets esperados, relativos a la variante. Se verifican contra la geometría
# real de la región antes de puntuar nada.
EXPECTED_DONOR_INTRON2 = -999   # borde 5' del intrón 2 = fin del exón 2
EXPECTED_ACCEPTOR_INTRON2 = 395  # borde 3' del intrón 2 = inicio del exón 3

# HAY DOS DONADORES CANÓNICOS EN LA REGIÓN, y confundirlos fue parte de CRIT-6:
#   -999  = donador del intrón 2   (fin del exón 2)
#   +536  = donador del intrón 3   (fin del exón 3)  <- el que usa run_masking.py
# Se miden LOS DOS. Normalizar el sitio críptico contra uno u otro da números
# distintos (32,4 % vs 26,1 % en retina), así que cuál se usa debe ser explícito
# y no quedar implícito en el nombre de una clave.
DONOR_CANONICAL_E3 = 536

# Sitios crípticos que la variante crea (Módulo 6).
CRYPTIC_DONOR = 1
CRYPTIC_ACCEPTOR = -89


def build_sites(region) -> dict[str, tuple[int, str]]:
    """{nombre: (índice absoluto, tipo)}. Los nombres salen de la geometría."""
    v = region.variant_offset_sense
    lo, hi = region.intron2_bounds_sense

    donor_abs, acceptor_abs = lo - 1, hi
    donor_rel, acceptor_rel = donor_abs - v, acceptor_abs - v

    if donor_rel != EXPECTED_DONOR_INTRON2 or acceptor_rel != EXPECTED_ACCEPTOR_INTRON2:
        raise SystemExit(
            f"ABORTA: geometría inesperada. Donador del intrón 2 en {donor_rel:+d} "
            f"(esperado {EXPECTED_DONOR_INTRON2:+d}) y aceptor en {acceptor_rel:+d} "
            f"(esperado {EXPECTED_ACCEPTOR_INTRON2:+d}). Etiquetar sitios sin verificar "
            "la geometría es exactamente el error CRIT-6."
        )

    return {
        # Nombres explícitos sobre a qué exón pertenece cada borde, para que no
        # se pueda volver a confundir e2 con e3.
        "donador_canonico_fin_exon2": (donor_abs, "donador"),
        "aceptor_canonico_inicio_exon3": (acceptor_abs, "aceptor"),
        # El mismo sitio que usa run_masking.py como referencia canónica.
        "donador_canonico_fin_exon3": (v + DONOR_CANONICAL_E3, "donador"),
        "donador_criptico": (v + CRYPTIC_DONOR, "donador"),
        "aceptor_criptico": (v + CRYPTIC_ACCEPTOR, "aceptor"),
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="Compara sitios entre juegos de pesos.")
    ap.add_argument("--out", default=DEFAULT_OUT)
    ap.add_argument("--padding", type=int, default=6000)
    ap.add_argument(
        "--weights", nargs="+", default=["spliceai", "retina", "gtex"],
        help="juegos de pesos a comparar (ver pipeline.splice_neural.WEIGHT_SETS)",
    )
    args = ap.parse_args()

    from pipeline.splice_neural import CH_ACCEPTOR, CH_DONOR, load_models, predict_scores

    region = fetch_target_region(padding=args.padding)
    sites = build_sites(region)
    v = region.variant_offset_sense
    channel = {"donador": CH_DONOR, "aceptor": CH_ACCEPTOR}

    print(f"región {len(region.mutant_sense)} nt | variante en {v}")
    for name, (idx, kind) in sites.items():
        print(f"  {name:42} offset {idx - v:+5d}  ({kind})")

    out: dict[str, dict] = {}
    for weights in args.weights:
        models = load_models(weights)
        p_wt = predict_scores(region.wildtype_sense, models)
        p_mu = predict_scores(region.mutant_sense, models)

        res = {}
        for name, (idx, kind) in sites.items():
            col = channel[kind]
            wt, mut = float(p_wt[idx, col]), float(p_mu[idx, col])
            res[name] = {
                "offset_rel": idx - v,
                "tipo": kind,
                "wt": round(wt, 4),
                "mut": round(mut, 4),
                "delta": round(mut - wt, 4),
            }
        out[weights] = res

        print(f"\n--- {weights} ---")
        for name, r in res.items():
            print(f"  {name:42} wt={r['wt']:.4f} mut={r['mut']:.4f} delta={r['delta']:+.4f}")

    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as fh:
        json.dump(
            {
                "nota": (
                    "Los nombres de sitio derivan de la geometría real de la región "
                    "(ver pipeline/run_site_comparison.py). El archivo anterior tenía "
                    "e2 y e3 cruzados -- CRIT-6 de la revisión adversarial."
                ),
                "sitios": {k: {"offset_rel": i - v, "tipo": t} for k, (i, t) in sites.items()},
                "pesos": out,
            },
            fh,
            indent=2,
            ensure_ascii=False,
        )
    print(f"\n-> {os.path.relpath(args.out, REPO_ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
