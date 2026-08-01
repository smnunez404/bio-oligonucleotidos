"""Módulo 2 — Oligo-Walk: generación masiva de candidatos ASO por ventana deslizante.

Recorre la secuencia mutante (sentido del transcrito) alrededor de la variante
con una ventana de longitud `length` y paso `step`, generando un candidato por
posición. No filtra ni puntúa nada — eso es el Módulo 3 en adelante (ver
wiki/conceptos/pipeline-bioinformatico-diseno-aso.md en el vault). Este módulo
solo enumera el espacio de búsqueda, tal como describen las fuentes ingeridas
(estrategia "Oligo-Walk").

Para cada ventana sobre el ARNm, el candidato ASO real es el complemento
reverso de esa ventana: el ASO debe ser antiparalelo y complementario para
hibridar con el ARN por apareamiento Watson-Crick.

Seguridad de límites: si se pasa `intron_bounds` (ver
`TargetRegion.intron2_bounds_sense` en pipeline/sequence.py), el rango de
escaneo se recorta para no generar candidatos que invadan un exón sano —
regla explícita de las fuentes ingeridas ("no bloquear exones sanos").
"""

from dataclasses import dataclass

from .utils import revcomp


@dataclass
class OligoCandidate:
    start: int  # offset 0-based en la secuencia de entrada (sentido del transcrito)
    end: int  # offset exclusivo
    length: int
    target_window: str  # secuencia del ARNm mutante cubierta por este candidato
    aso_sequence: str  # complemento reverso del target_window (lo que se sintetiza)
    covers_variant: bool  # si esta ventana incluye la posición exacta de la variante
    distance_to_variant: int  # distancia (nt) del centro de la ventana a la variante (0 = céntrico)


def compute_scan_range(
    variant_offset: int,
    flank: int,
    sequence_length: int,
    intron_bounds: tuple[int, int] | None = None,
) -> tuple[int, int, bool]:
    """Calcula el rango [start, end) a escanear.

    Se recorta primero a los límites de la secuencia disponible y, si se pasa
    `intron_bounds` (rango real del intrón 2, sentido del transcrito), también
    a esos límites — para no generar candidatos que invadan un exón sano.
    Devuelve además `clamped`: si el flank pedido tuvo que recortarse.
    """
    start = max(0, variant_offset - flank)
    end = min(sequence_length, variant_offset + flank)
    clamped = False
    if intron_bounds is not None:
        lo, hi = intron_bounds
        new_start = max(start, lo)
        new_end = min(end, hi)
        clamped = (new_start != start) or (new_end != end)
        start, end = new_start, new_end
    return start, end, clamped


def generate_oligo_walk(
    sequence: str,
    variant_offset: int,
    length: int = 20,
    step: int = 1,
    flank: int = 200,
    intron_bounds: tuple[int, int] | None = None,
) -> list[OligoCandidate]:
    """Genera todos los candidatos ASO por ventana deslizante alrededor de la variante.

    - `sequence`: secuencia completa (sentido del transcrito) de la que se extraen las ventanas
      — normalmente `TargetRegion.mutant_sense` del Módulo 1.
    - `variant_offset`: posición 0-based de la variante dentro de `sequence`.
    - `length`: longitud del oligo en nt (recomendado 16-25, ver wiki/conceptos/oligo-walk.md).
    - `step`: incremento entre ventanas consecutivas (1 = exhaustivo).
    - `flank`: cuántos nt escanear a cada lado de la variante (por defecto ±200,
      el margen recomendado por las fuentes ingeridas).
    - `intron_bounds`: si se pasa, recorta el escaneo a los límites reales del
      intrón 2 (ver `TargetRegion.intron2_bounds_sense`), para no generar
      candidatos que invadan un exón sano.
    """
    if length < 1:
        raise ValueError("length debe ser >= 1")
    if step < 1:
        raise ValueError("step debe ser >= 1")

    scan_start, scan_end, _clamped = compute_scan_range(
        variant_offset, flank, len(sequence), intron_bounds
    )

    candidates = []
    pos = scan_start
    while pos + length <= scan_end:
        window = sequence[pos : pos + length]
        window_end = pos + length
        covers_variant = pos <= variant_offset < window_end
        center = pos + length / 2
        candidates.append(
            OligoCandidate(
                start=pos,
                end=window_end,
                length=length,
                target_window=window,
                aso_sequence=revcomp(window),
                covers_variant=covers_variant,
                distance_to_variant=round(center - variant_offset),
            )
        )
        pos += step

    return candidates
