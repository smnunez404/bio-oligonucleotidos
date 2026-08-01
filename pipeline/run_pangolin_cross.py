"""Módulo 6c — corre Pangolin sobre la región WT y mutante y valida contra SpliceAI.

Uso:
    KMP_AFFINITY=disabled PYTHONPATH=. python pipeline/run_pangolin_cross.py

Requiere un entorno aparte con PyTorch y el paquete `pangolin` instalado desde
github.com/tkzeng/Pangolin (los pesos vienen en el repo, 177 MB). No se puede
correr en el entorno de SpliceAI: ese es TensorFlow.

Escribe data/results/pangolin_scores.csv y el perfil completo en
data/results/pangolin_profile.json.

Ver wiki/decisiones/0009-pangolin-validacion-cruzada-no-ensemble.
"""

from __future__ import annotations

import json
import os

# La afinidad hay que desactivarla ANTES de importar torch.
from pipeline.pangolin_cross import (  # noqa: E402
    CONTEXT_NT,
    MODEL_NUMS,
    TISSUES,
    offset_to_index,
    n_scored,
    positive_control_passes,
    rank_peaks,
    require_affinity_disabled,
    required_length,
)

require_affinity_disabled()

import numpy as np  # noqa: E402
import torch  # noqa: E402
from pkg_resources import resource_filename  # noqa: E402
from pangolin.model import AR, L, W, Pangolin  # noqa: E402

from pipeline.sequence import fetch_target_region  # noqa: E402

IN_MAP = np.asarray([[0, 0, 0, 0], [1, 0, 0, 0], [0, 1, 0, 0], [0, 0, 1, 0], [0, 0, 0, 1]])
INDEX_MAP = {0: 1, 1: 2, 2: 4, 3: 5, 4: 7, 5: 8, 6: 10, 7: 11}
"""Índice de la salida P(splice) por modelo, del custom_usage.py oficial."""

TISSUE_OF = dict(zip(MODEL_NUMS, TISSUES))

# Sitios de interés, en offsets relativos a la variante c.161-395G>A.
CANONICAL = {"aceptor_E2": -1092, "donador_E2": -999, "aceptor_E3": 395, "donador_E3": 536}
CRYPTIC = {"donador_criptico": 1, "aceptor_criptico": -89, "aceptor_criptico_alt": -95}

# Ganancias ya medidas con SpliceAI (wiki/bitacora/2026-07-30-modulo-6-...).
SPLICEAI_GAIN = {"donador_criptico": 0.560 - 0.194, "aceptor_criptico": 0.271 - 0.061}

PADDING = 6200
"""Cubre −1200..+1200 con contexto real completo. Con el padding por defecto
(región de 10001 nt) Pangolin devolvería UN solo score — ver pangolin_cross."""

RESULTS_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "results")


def one_hot_encode(seq: str) -> np.ndarray:
    """Codifica la secuencia ya en sentido del gen (para Pangolin es strand '+')."""
    s = (seq.upper().replace("A", "1").replace("C", "2")
         .replace("G", "3").replace("T", "4").replace("N", "0"))
    arr = np.asarray(list(map(int, list(s))))
    return IN_MAP[arr.astype("int8")]


def load_models(model_nums=MODEL_NUMS):
    """Carga las 5 réplicas por tejido. ~20 s en CPU."""
    out = {}
    for i in model_nums:
        reps = []
        for j in range(1, 6):
            m = Pangolin(L, W, AR)
            w = torch.load(
                resource_filename("pangolin", "models/final.%s.%s.3" % (j, i)),
                map_location=torch.device("cpu"), weights_only=False,
            )
            m.load_state_dict(w)
            m.eval()
            reps.append(m)
        out[i] = reps
    return out


def score(seq: str, replicates, model_num: int) -> np.ndarray:
    """Promedia las 5 réplicas de un tejido."""
    x = torch.from_numpy(np.expand_dims(one_hot_encode(seq).T, axis=0)).float()
    acc = []
    for m in replicates:
        with torch.no_grad():
            acc.append(m(x)[0][INDEX_MAP[model_num], :].numpy())
    return np.mean(acc, axis=0)


def main() -> None:
    tr = fetch_target_region(padding=PADDING)
    voff = tr.variant_offset_sense
    # Todos los sitios de interés tienen que caer dentro de la ventana puntuable.
    span = max({**CANONICAL, **CRYPTIC}.values()) - min({**CANONICAL, **CRYPTIC}.values()) + 1
    assert len(tr.mutant_sense) >= required_length(span), (
        f"región de {len(tr.mutant_sense)} nt: Pangolin puntuaría "
        f"{n_scored(len(tr.mutant_sense))} bases, hacen falta {span}"
    )

    models = load_models()
    scores = {}
    for tag, seq in (("wildtype", tr.wildtype_sense), ("mutant", tr.mutant_sense)):
        for mn in MODEL_NUMS:
            s = score(seq, models[mn], mn)
            scores[f"{tag}_{TISSUE_OF[mn]}"] = s
            print(f"{tag:9s} {TISSUE_OF[mn]:7s} n={len(s)} max={s.max():.4f}", flush=True)

    # Control positivo OBLIGATORIO: los 4 picos más altos tienen que ser los canónicos.
    prof = np.mean([scores[f"mutant_{t}"] for t in TISSUES], axis=0)
    ok = positive_control_passes(prof, voff, list(CANONICAL.values()))
    print("\ncontrol positivo:", "PASA" if ok else "FALLA")
    for off, v in rank_peaks(prof, voff, top=8):
        print(f"  {off:+6d}  {v:.4f}")
    if not ok:
        raise SystemExit("control positivo FALLA: no interpretar nada de esta corrida")

    os.makedirs(RESULTS_DIR, exist_ok=True)
    import csv

    with open(os.path.join(RESULTS_DIR, "pangolin_scores.csv"), "w",
              encoding="utf-8", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["sitio", "offset_rel_variante", "tejido", "wildtype", "mutant", "delta"])
        for lab, off in {**CANONICAL, **CRYPTIC}.items():
            i = offset_to_index(off, voff)
            for t in TISSUES:
                wt = float(scores[f"wildtype_{t}"][i])
                mu = float(scores[f"mutant_{t}"][i])
                w.writerow([lab, off, t, round(wt, 4), round(mu, 4), round(mu - wt, 4)])

    with open(os.path.join(RESULTS_DIR, "pangolin_profile.json"), "w", encoding="utf-8") as fh:
        json.dump({"variant_offset": voff, "context_nt": CONTEXT_NT,
                   "mean_profile": [round(float(v), 5) for v in prof]}, fh)

    print("\nvalidación cruzada vs SpliceAI (ganancia mutante − sano):")
    for lab, sai in SPLICEAI_GAIN.items():
        i = offset_to_index(CRYPTIC[lab], voff)
        pg = float(np.mean([scores[f"mutant_{t}"][i] - scores[f"wildtype_{t}"][i]
                            for t in TISSUES]))
        print(f"  {lab:22s} SpliceAI {sai:+.3f}  Pangolin {pg:+.3f}")


if __name__ == "__main__":
    main()
