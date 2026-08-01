"""Análisis de motivos de splicing: ¿la variante crea o refuerza un sitio críptico?

Heurística simple y transparente: compara la secuencia contra el **consenso
canónico del sitio donador 5' humano** (`MAG | GURAGU`, donde M = C/A y
R = A/G) y cuenta coincidencias posicionales, en wild-type vs. mutante.

ALCANCE Y LIMITACIONES — leer antes de usar los resultados:

- Esto NO es un predictor entrenado. Es un conteo de coincidencias contra un
  consenso degenerado de libro de texto. Un score real requiere MaxEntScan o
  un modelo de deep learning (SpliceAI/Pangolin) — planificado como Módulo 6,
  ver wiki/decisiones/0003 en el vault del proyecto.
- Que un motivo se acerque al consenso NO demuestra que el espliceosoma lo use.
  Sirve para generar una hipótesis localizada y priorizar dónde apuntar el ASO,
  no para concluir nada sobre el mecanismo real.
- La literatura (Peng et al. 2025) reporta TRES pseudoexones (PE1b/c/d) para
  esta variante; un único sitio donador críptico no explica los tres por sí solo.
"""

from dataclasses import dataclass

# Consenso del donador 5': posiciones -3,-2,-1 | +1..+6
DONOR_CONSENSUS: list[tuple[str, str]] = [
    ("M", "CA"),
    ("A", "A"),
    ("G", "G"),
    ("G", "G"),
    ("T", "T"),
    ("R", "AG"),
    ("A", "A"),
    ("G", "G"),
    ("T", "T"),
]
DONOR_EXONIC_LEN = 3  # posiciones -3,-2,-1
DONOR_MOTIF_LEN = len(DONOR_CONSENSUS)  # 9


@dataclass
class DonorMotif:
    """Un sitio donador candidato: corte entre `boundary` y `boundary+1`."""

    boundary: int  # último offset exónico (el corte va justo después)
    motif: str  # 9 nt: 3 exónicos + 6 intrónicos
    score: int  # coincidencias con el consenso (0-9)
    matches: list[bool]  # coincidencia posición a posición


def score_donor(seq: str, boundary: int) -> DonorMotif | None:
    """Puntúa el donador cuyo corte cae justo después de `boundary`.

    Devuelve None si no hay contexto suficiente en la secuencia.
    """
    lo = boundary - DONOR_EXONIC_LEN + 1
    hi = boundary + 1 + (DONOR_MOTIF_LEN - DONOR_EXONIC_LEN)
    if lo < 0 or hi > len(seq):
        return None

    motif = seq[lo:hi].upper()
    matches = [b in allowed for b, (_, allowed) in zip(motif, DONOR_CONSENSUS)]
    return DonorMotif(
        boundary=boundary, motif=motif, score=sum(matches), matches=matches
    )


@dataclass
class DonorComparison:
    """Comparación wild-type vs. mutante de un mismo sitio donador candidato."""

    boundary: int
    offset_from_variant: int  # boundary - variant_offset
    wildtype: DonorMotif
    mutant: DonorMotif

    @property
    def delta(self) -> int:
        return self.mutant.score - self.wildtype.score

    @property
    def has_canonical_gt(self) -> bool:
        """Si el motivo tiene el dinucleótido GT invariante en +1,+2.

        Sin GT en esas posiciones, el sitio no es un donador canónico —
        prácticamente todos los sitios donadores reales lo tienen.
        """
        return self.mutant.motif[DONOR_EXONIC_LEN : DONOR_EXONIC_LEN + 2] == "GT"


def compare_donors_near_variant(
    wildtype: str, mutant: str, variant_offset: int, search_radius: int = 10
) -> list[DonorComparison]:
    """Busca sitios donadores candidatos cerca de la variante y compara WT vs. mutante.

    Devuelve solo los que tienen el GT canónico en +1,+2, ordenados por
    cuánto los refuerza la mutación (delta) y luego por score absoluto.
    """
    results = []
    for boundary in range(
        variant_offset - search_radius, variant_offset + search_radius + 1
    ):
        wt_motif = score_donor(wildtype, boundary)
        mut_motif = score_donor(mutant, boundary)
        if wt_motif is None or mut_motif is None:
            continue
        comparison = DonorComparison(
            boundary=boundary,
            offset_from_variant=boundary - variant_offset,
            wildtype=wt_motif,
            mutant=mut_motif,
        )
        if comparison.has_canonical_gt:
            results.append(comparison)

    results.sort(key=lambda c: (-c.delta, -c.mutant.score))
    return results
