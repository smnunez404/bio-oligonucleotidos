"""Calibración del pipeline contra AONs de eficacia publicada (ADR 0002).

QUÉ RESPONDE
------------
El pipeline no tiene control positivo: no existe ningún ASO publicado para
c.161-395G>A, así que no hay forma de saber si su criterio discrimina un buen
candidato de uno malo. Este módulo lo pone a prueba sobre **otra** variante de
ABCA4 donde sí existen AONs con eficacia medida: c.5461-10T>C (intrón 38), el
oligo-walk de 32 AONs de Kaltak et al. 2023 que dio origen a QR-1011.

La pregunta es: **¿nuestro scoring pone arriba a los AONs que funcionaron?**

POR QUÉ ES UN MÓDULO APARTE Y NO UNA GENERALIZACIÓN
----------------------------------------------------
`pipeline/sequence.py` está cableado a c.161-395G>A: sus constantes de posición,
alelos y bordes exónicos están verificadas contra dos fuentes independientes y
sus resultados ya están publicados en `docs/articulo_es/`. Parametrizarlo para
que sirva a dos variantes obligaría a tocar código verificado y a re-validar
todo lo construido encima.

No hace falta: **las funciones de scoring ya son genéricas**. `evaluate_masks`
recibe secuencia y ventanas arbitrarias, `analyze_candidates` recibe candidatos
arbitrarios y `predict_scores` recibe cualquier secuencia. Lo único específico de
la variante es de dónde sale la secuencia — y eso es lo que aporta este módulo.

Resultado: la calibración usa **exactamente el mismo criterio** que el pipeline
principal, sin modificar una línea de él. Si la calibración sale mal, el
diagnóstico es del criterio, no de un refactor.

LO QUE ESTA CALIBRACIÓN NO ES
------------------------------
Es **otra variante y otro intrón**. Que el método discrimine en el intrón 38 es
evidencia de que el criterio capta algo real, **no** de que acierte en el intrón
2. Calibración, no validación del resultado propio.

Además la eficacia por AON de Kaltak está publicada como **figura de barras**
(Figura S1), no como tabla, así que acá se usa la clasificación cualitativa que
el texto sí afirma explícitamente (ver `KNOWN_EFFECTIVE`).
"""

from __future__ import annotations

import csv
import os
from dataclasses import dataclass

import requests

from pipeline.utils import revcomp

ENSEMBL_REST = "https://rest.ensembl.org"

# --- Variante de calibración: ABCA4 c.5461-10T>C (intrón 38) -----------------
# Resuelta con VariantValidator el 2026-08-01, misma vía que se usó para la
# variante principal: NM_000350.3:c.5461-10T>C -> NC_000001.11:g.94011395A>G,
# posición exónica "38i" (confirma intrón 38). ABCA4 está en hebra menos, así
# que el A>G genómico corresponde al T>C del transcrito.
CHROMOSOME = "1"
VARIANT_POS_GRCH38 = 94_011_395
REF_ALLELE_PLUS_STRAND = "A"
ALT_ALLELE_PLUS_STRAND = "G"

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
AON_CSV = os.path.join(_REPO_ROOT, "data", "reference", "kaltak2023", "aon_sequences.csv")

# AONs que Kaltak et al. 2023 reportan como eficaces, según afirmaciones
# EXPLÍCITAS del texto principal (no inferidas de figuras):
#   - AON31 y AON32 son los "lead candidates" del oligo-walk inicial.
#   - AON44, AON59 y AON60 son versiones cortas que "induce more splicing
#     recovery when compared with the longer AON versions (AON32)".
#   - AON44 fue el seleccionado y renombrado QR-1011.
# Son 5 de 32. Si el scoring no discriminara, esperaríamos verlos repartidos al
# azar en el ranking.
KNOWN_EFFECTIVE = ("AON31", "AON32", "AON44", "AON59", "AON60")
BEST_AON = "AON44"  # = QR-1011


@dataclass
class CalibrationRegion:
    """Región genómica de la variante de calibración, en sentido del transcrito."""

    wildtype_sense: str
    mutant_sense: str
    variant_offset_sense: int
    padding: int


def fetch_calibration_region(padding: int = 6000) -> CalibrationRegion:
    """Descarga la ventana centrada en c.5461-10T>C y la devuelve en sentido del
    transcrito (ABCA4 está en hebra menos, así que se invierte).

    Valida el alelo de referencia antes de devolver nada: si Ensembl no muestra
    la base esperada en esa posición, la coordenada está mal y seguir sería
    construir sobre arena. Es el mismo chequeo que hace `pipeline.sequence`.
    """
    start = VARIANT_POS_GRCH38 - padding
    end = VARIANT_POS_GRCH38 + padding

    url = (
        f"{ENSEMBL_REST}/sequence/region/human/{CHROMOSOME}:{start}-{end}"
        "?content-type=text/x-fasta"
    )
    resp = requests.get(url, timeout=60)
    resp.raise_for_status()
    plus = "".join(resp.text.strip().splitlines()[1:]).upper()

    offset_plus = VARIANT_POS_GRCH38 - start
    observed = plus[offset_plus]
    if observed != REF_ALLELE_PLUS_STRAND:
        raise ValueError(
            f"Ensembl devuelve '{observed}' en chr{CHROMOSOME}:{VARIANT_POS_GRCH38}, "
            f"se esperaba '{REF_ALLELE_PLUS_STRAND}'. Coordenada equivocada."
        )

    mutant_plus = plus[:offset_plus] + ALT_ALLELE_PLUS_STRAND + plus[offset_plus + 1:]

    wt_sense = revcomp(plus)
    mu_sense = revcomp(mutant_plus)
    # Al invertir, el índice se refleja respecto del largo.
    offset_sense = len(plus) - 1 - offset_plus

    if wt_sense[offset_sense] != revcomp(REF_ALLELE_PLUS_STRAND):
        raise ValueError("el offset en sentido del transcrito no cuadra tras revcomp")

    return CalibrationRegion(wt_sense, mu_sense, offset_sense, padding)


def load_aons(path: str = AON_CSV) -> list[dict]:
    """Carga las 32 secuencias de AON extraídas de la Tabla S1 de Kaltak 2023."""
    if not os.path.exists(path):
        raise FileNotFoundError(
            f"faltan las secuencias de AON en {path}. Ver "
            "wiki/fuentes/2026-08-01-kaltak2023-oligo-walk-qr1011 para cómo obtenerlas."
        )
    with open(path, encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def locate_aon(aon_rna: str, sense_sequence: str) -> tuple[int, int] | None:
    """Ubica dónde hibrida un AON sobre la secuencia en sentido del transcrito.

    El AON es antisentido: su diana es su complemento reverso. Se busca esa
    diana como subcadena. Devuelve `(start, end)` en coordenadas de
    `sense_sequence`, o None si no aparece (lo que indicaría que el AON no cae
    en la ventana descargada).
    """
    target = revcomp(aon_rna.upper().replace("U", "T"))
    idx = sense_sequence.find(target)
    if idx < 0:
        return None
    return idx, idx + len(target)


def build_windows(region: CalibrationRegion, aons: list[dict]) -> tuple[list, list]:
    """Convierte los AONs en ventanas de enmascarado. Devuelve (ventanas, no_ubicados)."""
    windows, missing = [], []
    for a in aons:
        loc = locate_aon(a["secuencia_rna"], region.mutant_sense)
        if loc is None:
            missing.append(a["aon"])
            continue
        windows.append((a["aon"], loc[0], loc[1]))
    return windows, missing


def rank_summary(scores: dict[str, float], higher_is_better: bool = True) -> dict:
    """Resume dónde caen los AONs eficaces conocidos dentro del ranking.

    `scores` es {nombre_aon: puntaje}. Devuelve las posiciones de los conocidos y
    un p-valor exacto por test de Mann-Whitney (implementado a mano para no
    sumar scipy como dependencia): la probabilidad de que un ordenamiento al
    azar deje a los conocidos tan arriba o más.
    """
    orden = sorted(scores, key=lambda n: scores[n], reverse=higher_is_better)
    pos = {n: i + 1 for i, n in enumerate(orden)}
    conocidos = [n for n in orden if n in KNOWN_EFFECTIVE]
    otros = [n for n in orden if n not in KNOWN_EFFECTIVE]

    # U de Mann-Whitney: cuántos pares (conocido, otro) están en el orden correcto.
    u = sum(
        1 for c in conocidos for o in otros
        if (scores[c] > scores[o]) == higher_is_better
    ) + 0.5 * sum(1 for c in conocidos for o in otros if scores[c] == scores[o])

    n1, n2 = len(conocidos), len(otros)
    return {
        "n_conocidos": n1,
        "n_otros": n2,
        "posiciones": {n: pos[n] for n in conocidos},
        "rango_medio_conocidos": sum(pos[n] for n in conocidos) / n1 if n1 else None,
        "rango_medio_otros": sum(pos[n] for n in otros) / n2 if n2 else None,
        "U": u,
        "AUC": u / (n1 * n2) if n1 and n2 else None,
        "mejor_aon_posicion": pos.get(BEST_AON),
        "orden": orden,
    }
