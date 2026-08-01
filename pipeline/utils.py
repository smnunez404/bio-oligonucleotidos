"""Utilidades compartidas entre módulos del pipeline."""

_COMPLEMENT = str.maketrans("ACGTNacgtn", "TGCANtgcan")


def revcomp(seq: str) -> str:
    """Complemento reverso de una secuencia de ADN/ARN (sentido 5'->3')."""
    return seq.translate(_COMPLEMENT)[::-1]
