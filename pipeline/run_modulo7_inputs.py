"""Genera `data/results/modulo7_inputs.csv` — los insumos del Módulo 7.

POR QUÉ EXISTE ESTE SCRIPT
--------------------------
El CSV se produjo originalmente en una sesión cuyo traspaso quedó incompleto, sin
script generador, y durante un tiempo se documentó como "de procedencia no
verificada". El 2026-07-31 se verificó reproduciendo sus 44 filas contra el
pipeline real, BLAST incluido, y **coinciden exactamente**. Este script es esa
reproducción, ya como código.

DE DÓNDE SALEN LAS 44 VENTANAS
-------------------------------
De `data/results/modulo6b_windows.json`, que produce `run_masking.py --emit-windows`.
No se vuelven a derivar acá a propósito: los candidatos se nombran `cand_<start>`,
o sea por su offset absoluto, así que dependen del `padding` de la región. Si este
script recalculara el embudo con otro padding, los nombres quedarían corridos y
**no cruzarían** contra los CSV del enmascarado — sin dar ningún error, solo un
join vacío. Consumir el artefacto canónico hace que esa consistencia sea
estructural en vez de casual.

LA SUTILEZA DE LOS PERCENTILES
-------------------------------
`analyze_candidates` asigna percentiles sobre TODO el lote que recibe. El router
`/api/thermodynamics` le pasa los 276 que pasaron el filtro heurístico, así que
sus percentiles son relativos a 276.

El Módulo 7 necesita percentiles relativos a los **44 que compiten entre sí**. No
es cosmético: para `cand_5816` la accesibilidad es percentil 44,0 sobre 276 y
**23,3** sobre 44. Usar los de 276 cambiaría el frente de Pareto.

Por eso este script llama a `analyze_candidates` **solo con los 44**. Filtrar la
salida de los 276 habría conservado los percentiles equivocados en silencio.

CÓMO CORRERLO
-------------
Necesita el entorno `bio-oligo` (ViennaRNA + BLAST+) y la base de transcriptoma
indexada en `data/reference/` (ver README):

    PYTHONPATH=. conda run -n bio-oligo python pipeline/run_modulo7_inputs.py

El grueso del tiempo es el BLAST de los 44 candidatos contra los 410.920
transcritos de Ensembl.
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import sys

from pipeline.off_target import analyze_off_target
from pipeline.oligo_walk import OligoCandidate
from pipeline.sequence import fetch_target_region
from pipeline.thermodynamics import analyze_candidates
from pipeline.utils import revcomp

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_RESULTS = os.path.join(_REPO_ROOT, "data", "results")
DEFAULT_WINDOWS = os.path.join(_RESULTS, "modulo6b_windows.json")
DEFAULT_OUT = os.path.join(_RESULTS, "modulo7_inputs.csv")

COLUMNS = [
    "candidato",
    "start_rel",
    "end_rel",
    "severidad_off_target",
    "tramo_contiguo_max",
    "off_target_count",
    "genes_distintos",
    "tm",
    "dg_hibridacion",
    "dg_autoestructura",
    "dg_homodimero",
    "accesibilidad",
    "accesibilidad_percentil",
    "homodimero_percentil",
    "termo_paso_filtro",
]


def load_windows(path: str) -> dict:
    if not os.path.exists(path):
        raise SystemExit(
            f"ABORTA: falta {os.path.relpath(path, _REPO_ROOT)}. Se genera con "
            "`python pipeline/run_masking.py --emit-windows`."
        )
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def build_rows(windows_path: str = DEFAULT_WINDOWS) -> list[dict]:
    blob = load_windows(windows_path)
    padding = blob["padding"]
    region = fetch_target_region(padding=padding)

    if region.variant_offset_sense != blob["variant_offset"]:
        raise SystemExit(
            f"ABORTA: la región tiene la variante en {region.variant_offset_sense} y "
            f"las ventanas se generaron con {blob['variant_offset']}. Regenerá las "
            "ventanas antes de seguir."
        )

    mutant = region.mutant_sense
    variant_offset = region.variant_offset_sense

    candidates = []
    for w in blob["windows"]:
        target = mutant[w["start"]:w["end"]]
        aso = revcomp(target)
        if aso != w["aso_sequence"]:
            raise SystemExit(
                f"ABORTA: {w['name']} no reproduce su secuencia ASO desde la región "
                "descargada. La región o las ventanas cambiaron."
            )
        center = (w["start"] + w["end"]) // 2
        candidates.append(
            OligoCandidate(
                start=w["start"],
                end=w["end"],
                length=w["end"] - w["start"],
                target_window=target,
                aso_sequence=aso,
                covers_variant=w["start"] <= variant_offset < w["end"],
                distance_to_variant=center - variant_offset,
            )
        )

    # Percentiles relativos a estos 44, no a los 276. Ver el docstring.
    termo = analyze_candidates(candidates, target_sequence=mutant)
    off = {o.candidate.start: o for o in analyze_off_target(candidates)}

    rows = []
    for t in termo:
        c = t.candidate
        o = off[c.start]
        rows.append({
            "candidato": f"cand_{c.start}",
            "start_rel": c.start - variant_offset,
            "end_rel": c.end - variant_offset,
            "severidad_off_target": o.severity,
            "tramo_contiguo_max": max(
                (h.longest_perfect_run for h in o.off_target_hits), default=0
            ),
            "off_target_count": o.off_target_count,
            "genes_distintos": o.distinct_genes_hit,
            # Redondeos iguales a los del CSV publicado, para que regenerarlo dé
            # un diff vacío y cualquier cambio real salte a la vista.
            "tm": round(t.tm, 3),
            "dg_hibridacion": round(t.dg_hybridization, 1),
            "dg_autoestructura": round(t.dg_self_structure, 1),
            "dg_homodimero": round(t.dg_homodimer, 1),
            "accesibilidad": round(t.accessibility, 4),
            "accesibilidad_percentil": t.accessibility_percentile,
            "homodimero_percentil": t.homodimer_percentile,
            "termo_paso_filtro": t.passed,
        })
    return rows


def main() -> int:
    ap = argparse.ArgumentParser(description="Genera los insumos del Módulo 7.")
    ap.add_argument("--out", default=DEFAULT_OUT)
    ap.add_argument("--windows", default=DEFAULT_WINDOWS)
    args = ap.parse_args()

    rows = build_rows(args.windows)
    if not rows:
        print("ABORTA: no se generó ninguna fila", file=sys.stderr)
        return 1

    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    with open(args.out, "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=COLUMNS)
        w.writeheader()
        w.writerows(rows)

    print(f"{len(rows)} candidatos -> {os.path.relpath(args.out, _REPO_ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
