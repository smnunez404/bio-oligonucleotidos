"""Módulo 6c — Pangolin como validación cruzada independiente de SpliceAI.

NO es un ensemble. Ver wiki/decisiones/0009-pangolin-validacion-cruzada-no-ensemble.

Diferencias con SpliceAI que condicionan todo el módulo:

* Pangolin devuelve UNA probabilidad por base ("esto es un sitio de splicing"),
  sin distinguir donador de aceptor. SpliceAI devuelve dos.
* Los pesos publicados cubren 4 tejidos (corazón, hígado, cerebro, testículo).
  Ninguno es retina, así que los valores ABSOLUTOS no son interpretables como
  probabilidad en retina — lo interpretable es la posición de los picos y el
  signo del cambio.
* Solo puntúa las bases centrales: con contexto de CONTEXT_NT por lado, una
  secuencia de N nt produce N - 2*CONTEXT_NT scores. Pedir una región demasiado
  corta devuelve un único punto sin que nada falle ruidosamente.

Requisito de entorno: KMP_AFFINITY=disabled (OpenMP aborta al fijar afinidad de
CPU en sandboxes que no lo permiten).
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Sequence

CONTEXT_NT = 5000
"""Contexto que Pangolin consume de cada lado (no puntúa esas bases)."""

TISSUES = ("heart", "liver", "brain", "testis")
"""Tejidos de los pesos publicados. Ninguno es retina — ver docstring del módulo."""

MODEL_NUMS = (0, 2, 4, 6)
"""Índice del modelo de splice-site por tejido, en el orden de TISSUES."""

ENSEMBLE_REPLICATES = 5
"""Réplicas por tejido que trae el release; se promedian."""

IN_MAP = {"A": 0, "C": 1, "G": 2, "T": 3, "N": 4}


def n_scored(seq_len: int) -> int:
    """Cuántas bases puntúa Pangolin para una secuencia de `seq_len` nt."""
    return max(0, seq_len - 2 * CONTEXT_NT)


def required_length(span_nt: int) -> int:
    """Largo mínimo de secuencia para puntuar `span_nt` bases contiguas."""
    if span_nt < 1:
        raise ValueError("span_nt debe ser >= 1")
    return span_nt + 2 * CONTEXT_NT


def one_hot_encode(seq: str) -> "list[list[int]]":
    """Codifica ACGT como vectores unitarios; cualquier otra letra -> vector nulo.

    Igual criterio que pipeline.splice_neural: N significa "no hay información
    legible acá", que es el proxy del bloqueo estérico del Módulo 6b.
    """
    table = [
        [0, 0, 0, 0],  # N / desconocido
        [1, 0, 0, 0],
        [0, 1, 0, 0],
        [0, 0, 1, 0],
        [0, 0, 0, 1],
    ]
    idx = {"A": 1, "C": 2, "G": 3, "T": 4}
    return [table[idx.get(b.upper(), 0)] for b in seq]


@dataclass(frozen=True)
class SiteComparison:
    """Un sitio comparado entre secuencia sana y mutante, por tejido."""

    label: str
    offset: int
    """Posición relativa a la variante, en nt."""
    wildtype: "dict[str, float]"
    mutant: "dict[str, float]"

    @property
    def gain(self) -> "dict[str, float]":
        return {t: self.mutant[t] - self.wildtype[t] for t in self.mutant}

    @property
    def mean_gain(self) -> float:
        g = self.gain
        return sum(g.values()) / len(g)

    @property
    def mean_mutant(self) -> float:
        return sum(self.mutant.values()) / len(self.mutant)


def offset_to_index(offset: int, variant_offset: int) -> int:
    """Convierte una posición relativa a la variante en índice del array de scores.

    El array empieza en la base CONTEXT_NT de la secuencia, así que el índice de
    la variante misma es `variant_offset - CONTEXT_NT`.
    """
    i = variant_offset - CONTEXT_NT + offset
    if i < 0:
        raise IndexError(
            f"offset {offset:+d} cae antes del primer score "
            f"(hacen falta {CONTEXT_NT} nt de contexto a la izquierda)"
        )
    return i


def rank_peaks(scores: Sequence[float], variant_offset: int, top: int = 8):
    """Devuelve [(offset_relativo, score)] de los `top` picos más altos.

    Es la primitiva del control positivo: los picos más altos de una región que
    contiene sitios canónicos anotados TIENEN que ser esos sitios.
    """
    order = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)
    out = []
    for i in order[:top]:
        out.append((i - (variant_offset - CONTEXT_NT), float(scores[i])))
    return out


def positive_control_passes(
    scores: Sequence[float],
    variant_offset: int,
    canonical_offsets: Sequence[int],
) -> bool:
    """True si los N picos más altos son exactamente los N sitios canónicos.

    No mira magnitudes: Pangolin y SpliceAI están calibrados distinto y comparar
    valores absolutos entre herramientas no significa nada.
    """
    k = len(canonical_offsets)
    top = rank_peaks(scores, variant_offset, top=k)
    return {off for off, _ in top} == set(canonical_offsets)


def require_affinity_disabled() -> None:
    """Falla ruidosamente si falta KMP_AFFINITY=disabled.

    Sin esta variable el proceso muere al importar torch en sandboxes que no
    permiten fijar afinidad de CPU, con un error de OpenMP que no menciona la
    causa.
    """
    if os.environ.get("KMP_AFFINITY") != "disabled":
        raise RuntimeError(
            "Pangolin necesita KMP_AFFINITY=disabled en este entorno "
            "(OpenMP aborta al intentar fijar afinidad de CPU). "
            "Corré: KMP_AFFINITY=disabled python ..."
        )
