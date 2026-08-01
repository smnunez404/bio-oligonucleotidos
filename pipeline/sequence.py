"""Módulo 1 — secuencia objetivo: intrón 2 de ABCA4 con la variante c.161-395G>A.

Coordenada confirmada el 2026-07-28 vía VariantValidator (NM_000350.3(ABCA4):c.161-395G>A
-> NC_000001.11:g.94111974C>T, posición exónica "2i" = intrón 2) y verificada contra la
secuencia real de Ensembl (la base de referencia observada coincide con la esperada).
Detalle completo en el vault del proyecto: wiki/entidades/variante-c161-395G-A.md.
"""

import hashlib
import os
from dataclasses import dataclass

import requests

from .utils import revcomp as _revcomp

ENSEMBL_REST = "https://rest.ensembl.org"

# --- Coordenadas confirmadas (GRCh38) ---
# ABCA4 está en la hebra menos del genoma; el alelo transcrito G>A corresponde
# al alelo genómico (hebra plus) C>T en esta posición.
CHROMOSOME = "1"
VARIANT_POS_GRCH38 = 94_111_974  # 1-based, hebra plus
REF_ALLELE_PLUS_STRAND = "C"
ALT_ALLELE_PLUS_STRAND = "T"
GENE_STRAND = -1  # ABCA4 en hebra menos

# --- Límites reales del intrón 2 (confirmados vía Ensembl /overlap/region, 2026-07-28) ---
# Exones flanqueantes del transcrito MANE Select (ENST00000370225 = NM_000350.3),
# coordenadas genómicas GRCh38 (hebra plus): exón rank=2 (94112973-94113066) y
# exón rank=3 (94111438-94111579). El intrón 2 es el tramo entre ambos.
# Verificación cruzada: 94_111_974 (variante) - 94_111_579 (borde del exón rank=3,
# el más cercano) = 395 nt -> coincide exactamente con "c.161-395" del nombre HGVS.
# Segunda confirmación independiente de la coordenada, además del chequeo de
# alelo de referencia ya hecho en fetch_target_region().
EXON_RANK3_END_GRCH38 = 94_111_579  # última base exónica antes del intrón (variante a 395 nt)
EXON_RANK2_START_GRCH38 = 94_112_973  # primera base exónica después del intrón (variante a 999 nt)
# Longitud contando bases inclusive: (94_112_972 - 94_111_580 + 1) = 1393.
# Ojo: la resta simple de los bordes exónicos da 1394 y sobrecuenta en 1 (error
# corregido el 2026-07-28 tras verificar contra intron2_bounds_sense, que sí
# devolvía 1393); `test_intron2_length_is_consistent_with_bounds` lo blinda.
INTRON2_LENGTH = (EXON_RANK2_START_GRCH38 - 1) - (EXON_RANK3_END_GRCH38 + 1) + 1  # 1393 nt


@dataclass
class TargetRegion:
    chrom: str
    start: int  # 1-based, hebra plus, inclusive
    end: int  # 1-based, hebra plus, inclusive
    genomic_plus: str  # secuencia cruda tal como la devuelve Ensembl (hebra plus)
    variant_offset_plus: int  # índice 0-based del nt variante dentro de genomic_plus

    @property
    def wildtype_sense(self) -> str:
        """Secuencia wild-type en sentido del transcrito (5'->3'), lista para Oligo-Walk."""
        return _revcomp(self.genomic_plus) if GENE_STRAND == -1 else self.genomic_plus

    @property
    def mutant_sense(self) -> str:
        """Secuencia con la variante introducida in silico, en sentido del transcrito."""
        mutated_plus = (
            self.genomic_plus[: self.variant_offset_plus]
            + ALT_ALLELE_PLUS_STRAND
            + self.genomic_plus[self.variant_offset_plus + 1 :]
        )
        return _revcomp(mutated_plus) if GENE_STRAND == -1 else mutated_plus

    @property
    def variant_offset_sense(self) -> int:
        """Índice 0-based de la variante dentro de la secuencia en sentido del transcrito."""
        return self._sense_offset(self.variant_offset_plus)

    def _sense_offset(self, plus_offset: int) -> int:
        if GENE_STRAND == -1:
            return len(self.genomic_plus) - 1 - plus_offset
        return plus_offset

    @property
    def intron2_bounds_sense(self) -> tuple[int, int]:
        """Rango [start, end) en offsets 0-based (sentido del transcrito) que
        corresponde al intrón 2 real — excluye los exones flanqueantes —,
        recortado a los límites de la secuencia efectivamente descargada.

        Cualquier ventana de Oligo-Walk fuera de este rango caería, total o
        parcialmente, en un exón sano y no debería usarse para diseñar un ASO
        (ver wiki/backlog en el vault del proyecto).
        """
        exon3_end_plus = EXON_RANK3_END_GRCH38 - self.start
        exon2_start_plus = EXON_RANK2_START_GRCH38 - self.start
        intron_plus_lo = exon3_end_plus + 1
        intron_plus_hi = exon2_start_plus  # exclusivo, en offsets "plus"

        s1 = self._sense_offset(intron_plus_hi - 1)
        s2 = self._sense_offset(intron_plus_lo)
        lo, hi = min(s1, s2), max(s1, s2) + 1
        return max(0, lo), min(len(self.genomic_plus), hi)


CACHE_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "reference", "regions"
)
"""Caché local de las regiones descargadas de Ensembl.

POR QUÉ EXISTE: sin caché, cada corrida del pipeline depende de que el servicio
REST de Ensembl esté disponible y siga devolviendo la misma secuencia. Las dos
cosas fallaron en la práctica: una corrida de este pipeline abortó con HTTP 500
del servidor. Para que un resultado publicado sea reproducible dentro de cinco
años, la secuencia de entrada tiene que estar en el repo, no detrás de una API.

Cada archivo se guarda junto a su SHA-256. Si el contenido cambiara, el checksum
no coincide y la carga falla ruidosamente en vez de correr sobre otra secuencia.
"""


def _cache_paths(start: int, end: int) -> tuple[str, str]:
    stem = f"GRCh38_chr{CHROMOSOME}_{start}_{end}"
    return (os.path.join(CACHE_DIR, stem + ".fa"),
            os.path.join(CACHE_DIR, stem + ".sha256"))


def _read_cached(start: int, end: int) -> str | None:
    fa, digest_path = _cache_paths(start, end)
    if not (os.path.exists(fa) and os.path.exists(digest_path)):
        return None
    with open(fa, encoding="utf-8") as fh:
        seq = "".join(line.strip() for line in fh if not line.startswith(">"))
    expected = open(digest_path, encoding="utf-8").read().split()[0]
    actual = hashlib.sha256(seq.encode("ascii")).hexdigest()
    if actual != expected:
        raise ValueError(
            f"La secuencia cacheada en {fa} no coincide con su checksum "
            f"(esperado {expected[:12]}…, calculado {actual[:12]}…). El archivo se "
            "modificó o se corrompió: borralo para volver a descargarlo de Ensembl."
        )
    return seq


def _write_cache(start: int, end: int, seq: str) -> None:
    fa, digest_path = _cache_paths(start, end)
    os.makedirs(CACHE_DIR, exist_ok=True)
    with open(fa, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(f">GRCh38 chr{CHROMOSOME}:{start}-{end} (hebra plus, Ensembl REST)\n")
        for i in range(0, len(seq), 60):
            fh.write(seq[i : i + 60] + "\n")
    with open(digest_path, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(f"{hashlib.sha256(seq.encode('ascii')).hexdigest()}  {os.path.basename(fa)}\n")


def fetch_target_region(padding: int = 5000, refresh: bool = False) -> TargetRegion:
    """Devuelve la ventana genómica (hebra plus) centrada en la variante confirmada.

    `padding` nt a cada lado (por defecto 5000, para cubrir la ventana de 10 kb
    recomendada para el ensemble SpliceAI/Pangolin — ver ADR 0003 en el vault).
    Valida que la base observada coincida con el alelo de referencia esperado
    antes de devolver la región, para no construir el pipeline sobre una
    coordenada equivocada.

    Usa la caché local con checksum de `data/reference/regions/` si está; si no,
    la descarga de Ensembl y la guarda. `refresh=True` fuerza la descarga (sirve
    para verificar que Ensembl sigue devolviendo la misma secuencia).
    """
    start = VARIANT_POS_GRCH38 - padding
    end = VARIANT_POS_GRCH38 + padding

    seq = None if refresh else _read_cached(start, end)
    if seq is None:
        url = (
            f"{ENSEMBL_REST}/sequence/region/human/{CHROMOSOME}:{start}-{end}"
            "?content-type=text/x-fasta"
        )
        resp = requests.get(url, timeout=30)
        resp.raise_for_status()
        lines = resp.text.strip().splitlines()
        seq = "".join(lines[1:])  # descartar encabezado FASTA
        _write_cache(start, end, seq)

    variant_offset_plus = VARIANT_POS_GRCH38 - start  # 0-based

    observed = seq[variant_offset_plus]
    if observed != REF_ALLELE_PLUS_STRAND:
        raise ValueError(
            f"La base observada en Ensembl ({observed}) no coincide con el alelo de "
            f"referencia esperado ({REF_ALLELE_PLUS_STRAND}) en chr{CHROMOSOME}:{VARIANT_POS_GRCH38}. "
            "Verificar coordenadas antes de continuar."
        )

    return TargetRegion(
        chrom=CHROMOSOME,
        start=start,
        end=end,
        genomic_plus=seq,
        variant_offset_plus=variant_offset_plus,
    )


if __name__ == "__main__":
    region = fetch_target_region()
    print(f"Ventana: chr{region.chrom}:{region.start}-{region.end} ({len(region.genomic_plus)} nt)")
    print(f"Variante en el sentido del transcrito, offset {region.variant_offset_sense}")
    print()
    print("Wild-type (sentido del transcrito, 40 nt alrededor de la variante):")
    v = region.variant_offset_sense
    print(region.wildtype_sense[v - 20 : v + 20])
    print()
    print("Mutante   (sentido del transcrito, 40 nt alrededor de la variante):")
    print(region.mutant_sense[v - 20 : v + 20])
