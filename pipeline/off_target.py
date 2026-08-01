"""Módulo 5 — off-target: cribado de candidatos ASO contra el transcriptoma humano.

Corre BLAST+ (`blastn-short`) de cada candidato ASO contra una base de datos
local del transcriptoma humano completo (Ensembl GRCh38, cDNA + ncRNA, ver
wiki/decisiones/0005 en el vault) y marca como "tóxico" a todo candidato que
tenga homología significativa contra un transcrito que NO sea el propio gen
diana (ABCA4).

===========================  QUÉ SE ESTÁ MIDIENDO  ===========================
Un ASO se une a su ARN diana por complementariedad de bases (Watson-Crick),
igual que una llave que encaja en una cerradura. Este módulo busca "cerraduras
ajenas" donde esa misma llave también podría encajar: otros ARN mensajeros o
no codificantes del cuerpo humano con una secuencia parecida a la región que
el ASO fue diseñado para reconocer. Encajar en una cerradura ajena es el
mecanismo por el que un ASO puede alterar el splicing o la expresión de un
gen que no es el que se quiere corregir (efecto "fuera de blanco").
===============================================================================

===========================  SEVERIDAD, NO GATE BINARIO  =====================
Hasta el 2026-07-29 este módulo aplicaba la regla de las fuentes ingeridas
como filtro binario (≥15 pb de homología contigua + ≤4 mismatches en otro
gen → "tóxico", se descarta). Aplicada a los 44 candidatos que llegaban acá,
el resultado era 0/44 aprobados: la regla no discriminaba, marcaba a todos
por igual.

Investigando por qué (ver wiki/decisiones/0006 en el vault, con evidencia de
literatura real citada), la razón es que esa regla viene de la lógica de
"gapmers" (ASOs que reclutan la RNasa H1 para cortar el ARN — ahí cualquier
homología corta ya es peligrosa, sin importar dónde caiga). Nuestro PMO NO
corta nada: bloquea físicamente una región del ARN. Que se pegue en
cualquier parte de un gen ajeno solo importa si esa parte es funcionalmente
relevante (splicing, codón de inicio, región reguladora) — no toda
homología es igual de tóxica. Además, ni siquiera para ASOs de splicing
existe un rasgo individual que prediga bien el off-target real (Scharner
et al. 2020, Nucleic Acids Research, doi:10.1093/nar/gkz1132).

Por eso este módulo ya NO descarta candidatos automáticamente. En su lugar,
anota cada candidato con un nivel de SEVERIDAD (ver `classify_severity`),
pensado como insumo para el futuro Módulo 7 (ranking), no como veredicto.

La severidad se calcula sobre el TRAMO CONTIGUO PERFECTO más largo que el
candidato forma con un gen ajeno (ver `longest_perfect_run`), no sobre el
conteo de mismatches del alineamiento. Razón: la regla heredada de las
fuentes habla de homología *contigua*, y BLAST reporta cuántos mismatches
hay en la ventana pero no dónde caen. Un mismatch en el medio parte el
alineamiento en dos tramos cortos (unión débil); el mismo mismatch pegado
al borde deja un tramo largo intacto (unión fuerte). Clasificar por conteo
de mismatches trata ambos casos igual, y en la práctica resultó estar
invertido: un hit corto pero perfecto quedaba por encima de uno más largo
con una sola diferencia (ver wiki/decisiones/0006, "Corrección
post-implementación", con la distribución medida antes y después).
===============================================================================

===========================  LIMITACIONES DECLARADAS  ========================
1. Se compara contra el TRANSCRIPTOMA (ARNm/ARN ya maduro y empalmado), no
   contra el genoma completo — ver wiki/decisiones/0005. No captura
   homología con regiones intrónicas o intergénicas que nunca se transcriben
   maduras, pero esas regiones no son un blanco de unión real para un ASO.
2. Los umbrales de tramo contiguo (18 / 16 / 13 pb) están anclados en el
   mínimo de homología contigua de la regla original de las fuentes
   ingeridas (15 pb — que a su vez no especifican con qué herramienta se
   calibró), repartido en escalones alrededor de ese piso. Mismo patrón de
   opacidad ya visto en los umbrales termodinámicos del Módulo 4. No están
   calibrados contra química PMO ni contra un control positivo real (ver
   wiki/decisiones/0006).
6. La severidad mide cuán fuerte PODRÍA unirse el candidato a un gen ajeno,
   no si eso causaría daño. Un tramo largo contra un gen no expresado en
   retina, o fuera de una región funcional, puede ser irrelevante; este
   módulo no lo distingue (queda para el Módulo 7).
3. BLAST penaliza gaps/bulges y no considera pares G:U wobble, subestimando
   posibles sitios de unión biológicamente plausibles con estructura
   irregular (Scharner et al. 2020) — limitación heredada, no resuelta.
4. El transcriptoma de referencia representa isoformas conocidas y anotadas;
   un ASO podría en teoría unirse a un transcrito real no anotado o
   específico de un tejido/individuo no representado en el ensamblado.
5. No hay un ASO publicado para esta variante con el que calibrar si esta
   severidad es la adecuada para química PMO real (ver
   wiki/riesgos/riesgo-ausencia-control-positivo.md) — sigue pendiente.
===============================================================================
"""

from __future__ import annotations

import os
import re
import shutil
import subprocess
import tempfile
from dataclasses import dataclass, field

from .oligo_walk import OligoCandidate

# --- Regla de corte heredada de las fuentes (ver wiki/decisiones/0005) ---
MIN_ALIGNMENT_LENGTH = 15  # pb de homología contigua
MAX_MISMATCHES = 4

# --- Parámetros de sensibilidad de BLAST ---
# word_size bajo (7) para no perder hits cortos de ~15-20 pb (el largo típico
# de un ASO): con word_size por defecto de blastn-short (11) se pierden
# variantes con mismatches cerca de los extremos del oligo.
BLAST_WORD_SIZE = 7
BLAST_EVALUE = 1000  # laxo a propósito: el filtro real es longitud+mismatches, no e-value
# `btop` (Blast Trace-back Operations) trae el alineamiento posición por
# posición: los números son corridas de bases apareadas y los pares de letras
# son mismatches/gaps. Ej: "12GT4" = 12 apareadas, un mismatch G/T, 4
# apareadas. Lo necesitamos para medir el TRAMO CONTIGUO PERFECTO más largo,
# que es lo que la regla de las fuentes llama "homología contigua" -- BLAST
# por sí solo solo reporta el largo de la ventana y cuántos mismatches tiene
# adentro, sin decir si están al borde o parten el alineamiento al medio.
BLAST_OUTFMT = (
    "6 qseqid sseqid pident length mismatch gapopen qstart qend sstart send evalue bitscore btop"
)

# Variables de entorno que apuntan a los datos de referencia (ver
# wiki/decisiones/0005-usar-blast-local-contra-transcriptoma-cdna-ncrna.md
# para cómo construirlos con makeblastdb sobre Ensembl cDNA + ncRNA). Si no
# se setean, se usa la ruta relativa al repo `data/reference/` (ver
# data/reference/README.md para cómo regenerar estos archivos — no se
# versionan en git por su tamaño, ~400 MB).
ENV_BLAST_DB = "OFF_TARGET_BLAST_DB"
ENV_GENE_MAP = "OFF_TARGET_GENE_MAP"

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_BLAST_DB = os.path.join(_REPO_ROOT, "data", "reference", "human_transcriptome_db")
DEFAULT_GENE_MAP = os.path.join(_REPO_ROOT, "data", "reference", "transcript_gene_map.tsv")

TARGET_GENE_SYMBOL = "ABCA4"

# --- Niveles de severidad (ver wiki/decisiones/0006) ---
# La severidad se calcula sobre el TRAMO CONTIGUO PERFECTO más largo que el
# candidato forma con un gen ajeno (no sobre el conteo de mismatches del
# alineamiento completo -- ver más abajo por qué). NO están calibrados
# específicamente para química PMO: ver limitaciones en el docstring del
# módulo. Se usan como insumo para el futuro Módulo 7 (ranking), no para
# descartar candidatos automáticamente.
#
# Puntos de corte, anclados en la regla heredada de las fuentes
# (MIN_ALIGNMENT_LENGTH = 15 pb de "homología contigua"):
#   >= 18 pb perfectos  -> alto      (supera holgadamente el umbral heredado)
#   16-17 pb perfectos  -> moderado  (por encima del umbral)
#   13-15 pb perfectos  -> leve      (en el umbral o apenas por debajo)
#   <= 12 pb perfectos  -> sin_señal (por debajo de lo que las fuentes
#                                     consideran homología relevante)
SEVERITY_MIN_RUN_ALTO = 18
SEVERITY_MIN_RUN_MODERADO = 16
SEVERITY_MIN_RUN_LEVE = 13

SEVERITY_ALTO = "alto"
SEVERITY_MODERADO = "moderado"
SEVERITY_LEVE = "leve"
SEVERITY_SIN_SENAL = "sin_señal"

# Orden de más a menos preocupante -- útil para ordenar tablas por severidad.
SEVERITY_ORDER = [SEVERITY_ALTO, SEVERITY_MODERADO, SEVERITY_LEVE, SEVERITY_SIN_SENAL]

SEVERITY_LABELS = {
    SEVERITY_ALTO: "Severidad alta",
    SEVERITY_MODERADO: "Severidad moderada",
    SEVERITY_LEVE: "Severidad leve",
    SEVERITY_SIN_SENAL: "Sin señal de off-target",
}


def longest_perfect_run(btop: str) -> int:
    """Tramo de bases apareadas consecutivas más largo dentro de un alineamiento.

    `btop` es el formato de traceback de BLAST: los números son corridas de
    bases apareadas y los pares de letras son mismatches o gaps.
    Ej: "12GT4" = 12 apareadas, un mismatch (G en query / T en subject), 4
    apareadas -> el tramo perfecto más largo es 12, NO 17.

    Esto importa porque la regla heredada de las fuentes habla de "homología
    CONTIGUA", pero el conteo de mismatches de BLAST no distingue entre un
    mismatch que parte el alineamiento al medio (deja dos tramos cortos) y
    uno pegado al borde (deja un tramo largo intacto). Termodinámicamente
    son muy distintos: lo que estabiliza un duplex es la corrida de bases
    apiladas sin interrumpir.
    """
    runs = [int(x) for x in re.findall(r"\d+", btop or "")]
    return max(runs) if runs else 0


def classify_severity(off_target_hits: list["TranscriptHit"]) -> str:
    """Clasifica la severidad de un candidato a partir de sus hits off-target
    (ya filtrados: pasan la regla de largo/mismatches Y no son el gen diana).

    Usa el TRAMO CONTIGUO PERFECTO más largo entre todos los hits (ver
    longest_perfect_run y los umbrales SEVERITY_MIN_RUN_*). No usa el conteo
    de mismatches del alineamiento completo: ese conteo trata igual a un hit
    de 20 pb con 1 mismatch al borde (19 pb perfectos seguidos, unión fuerte)
    que a uno con el mismatch al medio (dos tramos de ~10 pb, unión débil).
    """
    if not off_target_hits:
        return SEVERITY_SIN_SENAL
    best_run = max(h.longest_perfect_run for h in off_target_hits)
    if best_run >= SEVERITY_MIN_RUN_ALTO:
        return SEVERITY_ALTO
    if best_run >= SEVERITY_MIN_RUN_MODERADO:
        return SEVERITY_MODERADO
    if best_run >= SEVERITY_MIN_RUN_LEVE:
        return SEVERITY_LEVE
    return SEVERITY_SIN_SENAL


@dataclass
class TranscriptHit:
    """Un alineamiento BLAST entre un candidato ASO y un transcrito humano."""

    transcript_id: str
    gene_id: str | None
    gene_symbol: str | None
    pident: float
    length: int
    mismatches: int
    gapopen: int
    evalue: float
    bitscore: float
    # Traceback de BLAST (campo `btop`): permite reconstruir dónde caen los
    # mismatches dentro del alineamiento. Default "" para no romper llamadas
    # que construyan el hit a mano (tests) sin este dato.
    btop: str = ""

    @property
    def longest_perfect_run(self) -> int:
        """Tramo de bases apareadas consecutivas más largo de este hit.

        Si no hay traceback disponible (btop vacío), cae al caso conservador
        `length - mismatches`, que es el mejor valor posible: asume que todos
        los mismatches están juntos en un extremo.
        """
        if not self.btop:
            return max(self.length - self.mismatches, 0)
        return longest_perfect_run(self.btop)

    @property
    def is_target_gene(self) -> bool:
        return self.gene_symbol == TARGET_GENE_SYMBOL

    @property
    def meets_off_target_rule(self) -> bool:
        """True si este hit por sí solo activa la regla de corte (Módulo 5)."""
        return self.length >= MIN_ALIGNMENT_LENGTH and self.mismatches <= MAX_MISMATCHES


@dataclass
class OffTargetResult:
    candidate: OligoCandidate
    hits: list[TranscriptHit] = field(default_factory=list)

    @property
    def off_target_hits(self) -> list[TranscriptHit]:
        """Hits que cuentan como off-target: pasan la regla de corte Y no son el gen diana."""
        return [h for h in self.hits if h.meets_off_target_rule and not h.is_target_gene]

    @property
    def off_target_count(self) -> int:
        return len(self.off_target_hits)

    @property
    def distinct_genes_hit(self) -> int:
        genes = {h.gene_symbol or h.gene_id for h in self.off_target_hits}
        return len(genes)

    @property
    def worst_hit(self) -> TranscriptHit | None:
        """El hit off-target más preocupante: mayor longitud, luego menos mismatches."""
        if not self.off_target_hits:
            return None
        return max(self.off_target_hits, key=lambda h: (h.length, -h.mismatches))

    @property
    def severity(self) -> str:
        """Nivel de severidad (ver wiki/decisiones/0006) -- NO es un gate:
        ningún candidato se descarta automáticamente por este valor, es
        anotación para revisión humana / futuro ranking (Módulo 7)."""
        return classify_severity(self.off_target_hits)

    @property
    def severity_label(self) -> str:
        return SEVERITY_LABELS[self.severity]

    @property
    def reasons(self) -> list[str]:
        if self.severity == SEVERITY_SIN_SENAL:
            return []
        worst = self.worst_hit
        gene = worst.gene_symbol or worst.gene_id or worst.transcript_id
        best_run = max((h.longest_perfect_run for h in self.off_target_hits), default=0)
        return [
            f"{self.severity_label}: {self.off_target_count} hit(s) en {self.distinct_genes_hit} "
            f"gen(es) distinto(s) de {TARGET_GENE_SYMBOL}; tramo contiguo perfecto más largo = "
            f"{best_run} pb (peor hit: {gene}, ventana {worst.length} pb con "
            f"{worst.mismatches} mismatch(es)) -- señal para revisión, no descarte automático"
        ]


def _require_blast_binary() -> str:
    path = shutil.which("blastn")
    if path is None:
        raise RuntimeError(
            "blastn no está instalado en este entorno. Instalar BLAST+ (bioconda: "
            "`blast`) en el entorno usado para correr el Módulo 5."
        )
    return path


def _resolve_blast_db(blast_db: str | None) -> str:
    # Prioridad: parámetro explícito > variable de entorno > default del repo
    # (data/reference/, ver data/reference/README.md).
    db = blast_db or os.environ.get(ENV_BLAST_DB) or DEFAULT_BLAST_DB
    if not os.path.exists(db + ".nsq") and not os.path.exists(db + ".00.nsq"):
        raise RuntimeError(
            f"No se encontró el índice BLAST en '{db}' (falta el archivo .nsq). "
            f"¿Se corrió `makeblastdb -dbtype nucl`? Ver data/reference/README.md "
            "para regenerarlo, o pasar `blast_db=` / setear la variable de entorno "
            f"{ENV_BLAST_DB} para apuntar a otra ubicación."
        )
    return db


def load_gene_map(path: str | None = None) -> dict[str, tuple[str | None, str | None]]:
    """Carga el mapeo transcript_id -> (gene_id, gene_symbol) desde un TSV.

    El TSV tiene columnas `transcript_id\tgene_id\tgene_symbol` (ver
    wiki/decisiones/0005 para cómo generarlo a partir de los headers FASTA
    de Ensembl). Prioridad de resolución de ruta: parámetro explícito >
    variable de entorno > default del repo (data/reference/). Devuelve un
    dict vacío (sin fallar) si ninguna de esas rutas existe — en ese caso
    los hits quedan sin anotar por gen (gene_id/gene_symbol = None), lo
    cual degrada la exclusión del gen diana a nivel de transcript_id exacto
    solamente.
    """
    resolved = path or os.environ.get(ENV_GENE_MAP) or DEFAULT_GENE_MAP
    mapping: dict[str, tuple[str | None, str | None]] = {}
    if not resolved or not os.path.exists(resolved):
        return mapping
    with open(resolved, encoding="utf-8") as f:
        f.readline()  # descartar encabezado
        for line in f:
            parts = line.rstrip("\n").split("\t")
            if len(parts) < 1:
                continue
            transcript_id = parts[0]
            gene_id = parts[1] if len(parts) > 1 and parts[1] else None
            gene_symbol = parts[2] if len(parts) > 2 and parts[2] else None
            mapping[transcript_id] = (gene_id, gene_symbol)
    return mapping


def run_blast(
    candidates: list[OligoCandidate],
    blast_db: str | None = None,
    word_size: int = BLAST_WORD_SIZE,
    evalue: float = BLAST_EVALUE,
) -> str:
    """Corre blastn-short de todos los candidatos (una sola invocación) contra
    la base indexada del transcriptoma. Devuelve la salida cruda en formato
    tabular (outfmt 6) como string.
    """
    _require_blast_binary()
    db = _resolve_blast_db(blast_db)

    with tempfile.NamedTemporaryFile(mode="w", suffix=".fa", delete=False) as query_file:
        for i, c in enumerate(candidates):
            query_file.write(f">cand_{i}\n{c.aso_sequence}\n")
        query_path = query_file.name

    try:
        result = subprocess.run(
            [
                "blastn",
                "-task",
                "blastn-short",
                "-query",
                query_path,
                "-db",
                db,
                "-outfmt",
                BLAST_OUTFMT,
                "-word_size",
                str(word_size),
                "-evalue",
                str(evalue),
                "-num_threads",
                str(min(4, os.cpu_count() or 1)),
            ],
            capture_output=True,
            text=True,
            timeout=600,
        )
    finally:
        os.unlink(query_path)

    if result.returncode != 0:
        raise RuntimeError(f"blastn falló (código {result.returncode}): {result.stderr}")

    return result.stdout


def parse_blast_output(
    raw_output: str,
    gene_map: dict[str, tuple[str | None, str | None]],
) -> dict[int, list[TranscriptHit]]:
    """Parsea la salida tabular (outfmt 6) de blastn a hits por índice de candidato."""
    hits_by_candidate: dict[int, list[TranscriptHit]] = {}
    for line in raw_output.splitlines():
        if not line.strip():
            continue
        cols = line.split("\t")
        qseqid, sseqid, pident, length, mismatch, gapopen = cols[0:6]
        evalue, bitscore = cols[10], cols[11]
        # btop es la columna 13 (índice 12) del BLAST_OUTFMT de este módulo.
        # Se lee de forma tolerante: si la salida viene de un formato viejo
        # sin btop, el hit queda con btop="" y longest_perfect_run cae al
        # cálculo conservador length-mismatches.
        btop = cols[12] if len(cols) > 12 else ""
        cand_idx = int(qseqid.removeprefix("cand_"))
        gene_id, gene_symbol = gene_map.get(sseqid, (None, None))
        hit = TranscriptHit(
            transcript_id=sseqid,
            gene_id=gene_id,
            gene_symbol=gene_symbol,
            pident=float(pident),
            length=int(length),
            mismatches=int(mismatch),
            gapopen=int(gapopen),
            evalue=float(evalue),
            bitscore=float(bitscore),
            btop=btop,
        )
        hits_by_candidate.setdefault(cand_idx, []).append(hit)
    return hits_by_candidate


def analyze_off_target(
    candidates: list[OligoCandidate],
    blast_db: str | None = None,
    gene_map_path: str | None = None,
) -> list[OffTargetResult]:
    """Corre el Módulo 5 completo: BLAST + parseo + regla de corte, para todos
    los candidatos de una sola vez (una sola invocación a blastn, no una por
    candidato — evita pagar el costo de arranque de BLAST N veces).
    """
    gene_map = load_gene_map(gene_map_path)
    raw_output = run_blast(candidates, blast_db=blast_db)
    hits_by_candidate = parse_blast_output(raw_output, gene_map)

    return [
        OffTargetResult(candidate=c, hits=hits_by_candidate.get(i, []))
        for i, c in enumerate(candidates)
    ]
