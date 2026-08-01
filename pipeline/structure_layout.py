"""Estructura secundaria real del ARN diana, con coordenadas para dibujarla.

Pliega la región alrededor de la variante con ViennaRNA y devuelve las
coordenadas 2D del layout `naview` (el mismo que usan los diagramas clásicos
de estructura de ARN en la literatura), más la probabilidad de que cada base
esté desapareada.

El objetivo es didáctico pero **con datos reales**: en vez de dibujar un
"ARN genérico" de ilustración, se muestra el plegado calculado de esta
secuencia concreta, para que se vea por qué unas zonas son alcanzables por
el ASO y otras no.

Limitación: es el plegado de energía mínima (MFE) del modelo de ViennaRNA
sobre una ventana aislada. En una célula real el ARN es dinámico, tiene
proteínas unidas y el contexto es mucho más largo. Es un modelo, no una
fotografía.
"""

from dataclasses import dataclass

import RNA


@dataclass
class StructurePoint:
    index: int  # offset 0-based dentro de la ventana
    base: str
    x: float
    y: float
    paired: bool
    unpaired_prob: float | None


@dataclass
class FoldedRegion:
    window_start: int  # offset 0-based en la secuencia completa
    window_end: int
    variant_index: int  # offset dentro de la ventana
    structure: str  # notación dot-bracket
    mfe: float
    paired_fraction: float
    points: list[StructurePoint]


def fold_region(
    sequence: str,
    variant_offset: int,
    half_window: int = 150,
) -> FoldedRegion:
    """Pliega una ventana centrada en la variante y devuelve su layout 2D."""
    start = max(0, variant_offset - half_window)
    end = min(len(sequence), variant_offset + half_window)
    sub = sequence[start:end].upper().replace("T", "U")

    structure, mfe = RNA.fold(sub)
    coords = RNA.naview_xy_coordinates(structure)

    # Probabilidad de que CADA base individual esté desapareada.
    # (ulength=1 -> por nucleótido; es lo que da un color continuo legible)
    try:
        up = RNA.pfl_fold_up(sub, 1, 80, 40)
    except Exception:  # noqa: BLE001 — si falla, seguimos sin color de accesibilidad
        up = None

    points = []
    for i, base in enumerate(sub):
        prob = None
        if up is not None:
            try:
                value = up[i + 1][1]  # matriz 1-based
                prob = float(value) if value is not None else None
            except (IndexError, TypeError):
                prob = None
        points.append(
            StructurePoint(
                index=i,
                base=base,
                x=coords[i].X,
                y=coords[i].Y,
                paired=structure[i] != ".",
                unpaired_prob=prob,
            )
        )

    paired_fraction = sum(1 for c in structure if c != ".") / len(structure)

    return FoldedRegion(
        window_start=start,
        window_end=end,
        variant_index=variant_offset - start,
        structure=structure,
        mfe=mfe,
        paired_fraction=paired_fraction,
        points=points,
    )
