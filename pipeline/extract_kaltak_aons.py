"""Extrae las secuencias de AON de la Tabla S1 de Kaltak et al. 2023.

POR QUÉ ES UN SCRIPT Y NO UN CSV VERSIONADO
--------------------------------------------
Las secuencias vienen del material suplementario de un artículo publicado bajo
**CC BY-NC-ND**. Las secuencias en sí son hechos y los hechos no son
copyrightables, pero redistribuir la tabla como compilación es zona gris — y la
cláusula "NC" (no comercial) chocaría con la licencia MIT de este repositorio.

Así que el repo **no versiona el CSV**: versiona el código que lo extrae. Quien
quiera reproducir la calibración baja el suplemento (que es de acceso abierto) y
corre esto. Beneficio secundario: la extracción queda auditable en vez de ser un
dato opaco que alguien pegó a mano.

CÓMO OBTENER EL SUPLEMENTO
---------------------------
PMC devuelve un reCAPTCHA en la ruta `/bin/`. La vía que funciona:

    # 1. Obtener el PII real desde el XML del artículo
    curl -s "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi?db=pmc&id=9999166&retmode=xml" \\
      | grep -oE '<article-id pub-id-type="pii">[^<]+'
    #    -> S2162-2531(23)00040-9  ->  S2162253123000409

    # 2. Descargar del CDN de Elsevier
    curl -L -o data/reference/kaltak2023/kaltak2023_supplementary_S1-S6.pdf \\
      "https://ars.els-cdn.com/content/image/1-s2.0-S2162253123000409-mmc1.pdf"

CÓMO CORRERLO
-------------
    python pipeline/extract_kaltak_aons.py

Requiere `pdftotext` (paquete `poppler-utils`).

REFERENCIA
----------
Kaltak M, de Bruijn P, Piccolo D, et al. *Antisense oligonucleotide therapy
corrects splicing in the common Stargardt disease type 1-causing variant.*
Mol Ther Nucleic Acids (2023). DOI 10.1016/j.omtn.2023.02.020 · PMC9999166.
"""

from __future__ import annotations

import argparse
import csv
import os
import re
import shutil
import subprocess
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_DIR = os.path.join(REPO_ROOT, "data", "reference", "kaltak2023")
DEFAULT_PDF = os.path.join(_DIR, "kaltak2023_supplementary_S1-S6.pdf")
DEFAULT_OUT = os.path.join(_DIR, "aon_sequences.csv")

# `AON12   5'-CCCAGGGCCCAUGCUCCAUGGGC-3'`
# El PDF mezcla comillas rectas y tipográficas, de ahí la clase de caracteres.
AON_RE = re.compile(r"^\s*(AON\d+)\s+5['’]-([ACGU]+)-3['’]", re.MULTILINE)

# Verificación cruzada contra el texto principal del paper, que afirma que AON44
# es "AON60 and its 1-nt longer version". Si la extracción se rompiera, esto lo
# detecta sin necesidad de comparar contra un archivo previo.
EXPECTED_AON44 = "AUGCUCCAUGGGCCUCGG"
EXPECTED_MIN = 30


def extract(pdf_path: str) -> list[dict]:
    if not shutil.which("pdftotext"):
        raise SystemExit(
            "ABORTA: falta `pdftotext`. Instalar poppler-utils "
            "(apt: poppler-utils · conda: -c conda-forge poppler)."
        )
    if not os.path.exists(pdf_path):
        raise SystemExit(
            f"ABORTA: no está {os.path.relpath(pdf_path, REPO_ROOT)}.\n"
            "Ver el docstring de este script para cómo obtenerlo (acceso abierto)."
        )

    txt = subprocess.run(
        ["pdftotext", "-layout", pdf_path, "-"],
        capture_output=True, text=True, check=True,
    ).stdout

    rows = [
        {"aon": m.group(1), "secuencia_rna": m.group(2), "longitud_nt": len(m.group(2))}
        for m in AON_RE.finditer(txt)
    ]

    if len(rows) < EXPECTED_MIN:
        raise SystemExit(
            f"ABORTA: se extrajeron {len(rows)} AONs y se esperaban al menos "
            f"{EXPECTED_MIN}. El PDF cambió o `pdftotext` cambió su salida."
        )

    by_name = {r["aon"]: r["secuencia_rna"] for r in rows}
    if by_name.get("AON44") != EXPECTED_AON44:
        raise SystemExit(
            f"ABORTA: AON44 salió '{by_name.get('AON44')}' y se esperaba "
            f"'{EXPECTED_AON44}'. La extracción no es fiable."
        )
    # El texto del paper dice que AON44 es AON60 más 1 nt. Verificación cruzada
    # tabla-vs-prosa: si no se cumple, algo se leyó mal.
    if "AON60" in by_name and not (
        by_name["AON44"].endswith(by_name["AON60"])
        and len(by_name["AON44"]) == len(by_name["AON60"]) + 1
    ):
        raise SystemExit("ABORTA: AON44 no es AON60 + 1 nt, como afirma el paper.")

    return rows


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--pdf", default=DEFAULT_PDF)
    ap.add_argument("--out", default=DEFAULT_OUT)
    args = ap.parse_args()

    rows = extract(args.pdf)
    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    with open(args.out, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=["aon", "secuencia_rna", "longitud_nt"])
        w.writeheader()
        w.writerows(rows)

    print(f"{len(rows)} AONs -> {os.path.relpath(args.out, REPO_ROOT)}")
    print(f"  longitudes: {sorted({r['longitud_nt'] for r in rows})}")
    print(f"  AON44 (= QR-1011): {rows and dict((r['aon'], r['secuencia_rna']) for r in rows).get('AON44')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
