"""Tests del Módulo 5 (off-target contra el transcriptoma humano).

Dos grupos de tests:

1. Tests unitarios puros (parseo de salida BLAST, regla de corte, exclusión
   del gen diana, carga del mapeo transcrito->gen) — no requieren blastn
   instalado ni datos descargados, corren siempre.
2. Tests marcados `@pytest.mark.blast` — construyen una mini base BLAST al
   vuelo (unos pocos transcritos sintéticos) y corren blastn real de punta
   a punta. Requieren blastn/makeblastdb instalados (entorno `bio-oligo`);
   se saltan automáticamente si no están disponibles.
"""

import os
import shutil
import subprocess

import pytest

from pipeline.off_target import (
    MAX_MISMATCHES,
    MIN_ALIGNMENT_LENGTH,
    SEVERITY_ALTO,
    SEVERITY_LEVE,
    SEVERITY_MODERADO,
    SEVERITY_SIN_SENAL,
    TARGET_GENE_SYMBOL,
    OffTargetResult,
    TranscriptHit,
    analyze_off_target,
    classify_severity,
    load_gene_map,
    longest_perfect_run,
    parse_blast_output,
)
from pipeline.oligo_walk import OligoCandidate
from pipeline.utils import revcomp

BLASTN_AVAILABLE = shutil.which("blastn") is not None and shutil.which("makeblastdb") is not None


def _candidate(aso: str, start: int = 0) -> OligoCandidate:
    return OligoCandidate(
        start=start,
        end=start + len(aso),
        length=len(aso),
        target_window=revcomp(aso),
        aso_sequence=aso,
        covers_variant=False,
        distance_to_variant=0,
    )


def _hit(
    transcript_id: str = "ENST00000000001.1",
    gene_symbol: str | None = "GENEX",
    length: int = 20,
    mismatches: int = 0,
    btop: str = "",
) -> TranscriptHit:
    return TranscriptHit(
        transcript_id=transcript_id,
        gene_id="ENSG00000000001.1",
        gene_symbol=gene_symbol,
        pident=100.0,
        length=length,
        mismatches=mismatches,
        gapopen=0,
        evalue=0.001,
        bitscore=40.0,
        btop=btop,
    )


# --------------------------------------------------------------------------
# Regla de corte (Módulo 5): >=15 pb contiguos, <=4 mismatches
# --------------------------------------------------------------------------


def test_hit_meets_off_target_rule_at_exact_thresholds():
    assert _hit(length=MIN_ALIGNMENT_LENGTH, mismatches=MAX_MISMATCHES).meets_off_target_rule


def test_hit_below_length_threshold_does_not_meet_rule():
    assert not _hit(length=MIN_ALIGNMENT_LENGTH - 1, mismatches=0).meets_off_target_rule


def test_hit_above_mismatch_threshold_does_not_meet_rule():
    assert not _hit(length=20, mismatches=MAX_MISMATCHES + 1).meets_off_target_rule


# --------------------------------------------------------------------------
# Exclusión del gen diana (ABCA4): un hit contra el propio gen no cuenta
# como off-target, sea cual sea su longitud/mismatches.
# --------------------------------------------------------------------------


def test_hit_against_target_gene_is_not_off_target():
    hit = _hit(gene_symbol=TARGET_GENE_SYMBOL, length=20, mismatches=0)
    assert hit.is_target_gene
    result = OffTargetResult(candidate=_candidate("A" * 20), hits=[hit])
    assert result.severity == SEVERITY_SIN_SENAL
    assert result.off_target_count == 0


def test_hit_against_other_gene_counts_as_off_target():
    hit = _hit(gene_symbol="OTHERGENE", length=20, mismatches=0)
    result = OffTargetResult(candidate=_candidate("A" * 20), hits=[hit])
    assert result.severity == SEVERITY_ALTO  # 0 mismatches = homología perfecta
    assert result.off_target_count == 1
    assert "OTHERGENE" in result.reasons[0]


def test_mixed_hits_only_non_target_gene_hits_count():
    hits = [
        _hit(transcript_id="ENST_A", gene_symbol=TARGET_GENE_SYMBOL, length=20, mismatches=0),
        _hit(transcript_id="ENST_B", gene_symbol="OTHERGENE", length=18, mismatches=1),
        _hit(transcript_id="ENST_C", gene_symbol="OTHERGENE", length=16, mismatches=0),
    ]
    result = OffTargetResult(candidate=_candidate("A" * 20), hits=hits)
    assert result.off_target_count == 2
    assert result.distinct_genes_hit == 1  # ambos hits no-diana son del mismo gen


def test_hits_below_rule_threshold_are_ignored_even_against_other_genes():
    hit = _hit(gene_symbol="OTHERGENE", length=10, mismatches=0)  # < MIN_ALIGNMENT_LENGTH
    result = OffTargetResult(candidate=_candidate("A" * 20), hits=[hit])
    assert result.severity == SEVERITY_SIN_SENAL


def test_worst_hit_prefers_longer_alignment_then_fewer_mismatches():
    hits = [
        _hit(transcript_id="ENST_SHORT", gene_symbol="G1", length=15, mismatches=0),
        _hit(transcript_id="ENST_LONG", gene_symbol="G2", length=19, mismatches=3),
    ]
    result = OffTargetResult(candidate=_candidate("A" * 20), hits=hits)
    assert result.worst_hit.transcript_id == "ENST_LONG"


def test_candidate_with_no_hits_has_sin_senal_severity():
    result = OffTargetResult(candidate=_candidate("A" * 20), hits=[])
    assert result.severity == SEVERITY_SIN_SENAL
    assert result.off_target_count == 0
    assert result.worst_hit is None
    assert result.reasons == []


# --------------------------------------------------------------------------
# Tramo contiguo perfecto (btop): la base del cálculo de severidad.
# --------------------------------------------------------------------------


def test_longest_perfect_run_all_matches():
    assert longest_perfect_run("20") == 20


def test_longest_perfect_run_mismatch_in_the_middle_splits_the_alignment():
    # "12GT4" = 12 apareadas, mismatch, 4 apareadas -> el tramo real es 12,
    # aunque BLAST reporte una ventana de 17 pb con 1 mismatch.
    assert longest_perfect_run("12GT4") == 12


def test_longest_perfect_run_mismatch_at_the_edge_keeps_long_run():
    # Mismo conteo de mismatches que el caso anterior (1), pero al borde:
    # '12GT4' parte el alineamiento en tramos de 12 y 4; '1AG16' deja 1 y 16.
    # (Los largos totales difieren: 17 pb vs 18 pb. Lo que se compara acá es
    # el efecto de la POSICIÓN del mismatch, no el largo de la ventana.)
    assert longest_perfect_run("1AG16") == 16


def test_longest_perfect_run_empty_btop():
    assert longest_perfect_run("") == 0


def test_hit_falls_back_to_length_minus_mismatches_without_btop():
    # Sin traceback, el mejor caso posible es que todos los mismatches estén
    # juntos en un extremo -> length - mismatches.
    hit = _hit(length=20, mismatches=2, btop="")
    assert hit.longest_perfect_run == 18


def test_hit_uses_btop_when_available():
    hit = _hit(length=17, mismatches=1, btop="12GT4")
    assert hit.longest_perfect_run == 12


# --------------------------------------------------------------------------
# Severidad (Módulo 5, ADR 0006): reemplaza el gate binario. classify_severity
# usa el TRAMO CONTIGUO PERFECTO más largo, no el conteo de mismatches.
# --------------------------------------------------------------------------


def test_classify_severity_no_hits_is_sin_senal():
    assert classify_severity([]) == SEVERITY_SIN_SENAL


def test_classify_severity_long_perfect_run_is_alto():
    hits = [_hit(gene_symbol="OTHERGENE", length=20, mismatches=0, btop="20")]
    assert classify_severity(hits) == SEVERITY_ALTO


def test_classify_severity_medium_run_is_moderado():
    # 16 pb perfectos contiguos -> moderado (>=16, <18)
    assert classify_severity([_hit(gene_symbol="G", length=20, mismatches=1, btop="16AG3")]) == SEVERITY_MODERADO


def test_classify_severity_short_run_is_leve():
    # 15 pb perfectos contiguos -> leve (>=13, <16); justo el umbral de la
    # regla heredada MIN_ALIGNMENT_LENGTH.
    assert classify_severity([_hit(gene_symbol="G", length=15, mismatches=0, btop="15")]) == SEVERITY_LEVE


def test_classify_severity_very_short_run_is_sin_senal():
    # Un hit cuya ventana pasa la regla (17 pb, 1 mismatch) pero cuyo tramo
    # contiguo real es de solo 12 pb no constituye señal relevante.
    assert classify_severity([_hit(gene_symbol="G", length=17, mismatches=1, btop="12GT4")]) == SEVERITY_SIN_SENAL


def test_classify_severity_uses_worst_hit_among_several():
    # Se clasifica por el hit de tramo contiguo MÁS LARGO (el más
    # preocupante), no por el promedio ni por el primero.
    hits = [
        _hit(transcript_id="A", gene_symbol="G1", length=17, mismatches=1, btop="12GT4"),
        _hit(transcript_id="B", gene_symbol="G2", length=20, mismatches=0, btop="20"),
    ]
    assert classify_severity(hits) == SEVERITY_ALTO


def test_severity_prefers_contiguous_run_over_raw_mismatch_count():
    # Este es el caso que motivó el rediseño: por conteo de mismatches el
    # hit A (0 mismatches) parecería el peor, pero su tramo contiguo es
    # corto (15 pb); el hit B tiene 1 mismatch al borde y 19 pb seguidos,
    # que termodinámicamente une más fuerte.
    solo_a = [_hit(transcript_id="A", gene_symbol="G1", length=15, mismatches=0, btop="15")]
    solo_b = [_hit(transcript_id="B", gene_symbol="G2", length=20, mismatches=1, btop="19AG")]
    assert classify_severity(solo_a) == SEVERITY_LEVE
    assert classify_severity(solo_b) == SEVERITY_ALTO


def test_off_target_result_no_candidate_is_discarded_by_severity():
    # Ningún nivel de severidad implica descarte automático -- todos los
    # niveles son valores válidos de OffTargetResult.severity, no un gate.
    cases = [
        ("20", SEVERITY_ALTO),
        ("16AG3", SEVERITY_MODERADO),
        ("15", SEVERITY_LEVE),
    ]
    for btop, expected in cases:
        hit = _hit(gene_symbol="OTHERGENE", length=20, mismatches=1, btop=btop)
        result = OffTargetResult(candidate=_candidate("A" * 20), hits=[hit])
        assert result.severity == expected
        # La API no expone (ya no existe) ningún atributo `passed` binario.
        assert not hasattr(result, "passed")


# --------------------------------------------------------------------------
# Parseo de la salida tabular de blastn (outfmt 6)
# --------------------------------------------------------------------------


def test_parse_blast_output_maps_hits_to_candidate_index():
    raw = (
        "cand_0\tENST00000370225.4\t100.000\t20\t0\t0\t1\t20\t100\t119\t1e-05\t40.1\n"
        "cand_2\tENST00000999999.1\t94.444\t18\t1\t0\t1\t18\t50\t67\t7.4\t28.2\n"
    )
    gene_map = {
        "ENST00000370225.4": ("ENSG00000198691.14", "ABCA4"),
        "ENST00000999999.1": ("ENSG00000999999.1", "OTHERGENE"),
    }
    parsed = parse_blast_output(raw, gene_map)
    assert set(parsed.keys()) == {0, 2}
    assert parsed[0][0].gene_symbol == "ABCA4"
    assert parsed[0][0].length == 20
    assert parsed[2][0].gene_symbol == "OTHERGENE"
    assert parsed[2][0].mismatches == 1


def test_parse_blast_output_handles_unmapped_transcript():
    raw = "cand_0\tENST_UNKNOWN.1\t100.000\t20\t0\t0\t1\t20\t1\t20\t1e-05\t40.1\n"
    parsed = parse_blast_output(raw, gene_map={})
    assert parsed[0][0].gene_symbol is None
    assert parsed[0][0].gene_id is None


def test_parse_blast_output_ignores_blank_lines():
    raw = "cand_0\tENST_A\t100.000\t20\t0\t0\t1\t20\t1\t20\t1e-05\t40.1\n\n"
    parsed = parse_blast_output(raw, gene_map={})
    assert len(parsed[0]) == 1


# --------------------------------------------------------------------------
# Carga del mapeo transcript_id -> (gene_id, gene_symbol)
# --------------------------------------------------------------------------


def test_load_gene_map_parses_tsv(tmp_path):
    tsv = tmp_path / "map.tsv"
    tsv.write_text(
        "transcript_id\tgene_id\tgene_symbol\n"
        "ENST00000370225.4\tENSG00000198691.14\tABCA4\n"
        "ENST00000999999.1\t\t\n"
    )
    mapping = load_gene_map(str(tsv))
    assert mapping["ENST00000370225.4"] == ("ENSG00000198691.14", "ABCA4")
    assert mapping["ENST00000999999.1"] == (None, None)


def test_load_gene_map_returns_empty_dict_when_path_missing():
    assert load_gene_map("/no/existe/este/archivo.tsv") == {}


def test_load_gene_map_falls_back_to_repo_default_when_no_path_and_no_env(monkeypatch):
    # Sin parámetro ni variable de entorno, cae al default del repo
    # (data/reference/transcript_gene_map.tsv) — si ese archivo de datos de
    # referencia está presente, debe cargarlo con éxito; si no, dict vacío.
    monkeypatch.delenv("OFF_TARGET_GENE_MAP", raising=False)
    from pipeline.off_target import DEFAULT_GENE_MAP

    mapping = load_gene_map(None)
    if os.path.exists(DEFAULT_GENE_MAP):
        assert mapping.get("ENST00000370225.4") == (
            mapping.get("ENST00000370225.4", (None, None))[0],
            TARGET_GENE_SYMBOL,
        )
    else:
        assert mapping == {}


# --------------------------------------------------------------------------
# Integración real con blastn (Módulo 5 completo) — se saltan si no hay BLAST+
# --------------------------------------------------------------------------


@pytest.fixture(scope="module")
def mini_blast_db(tmp_path_factory):
    """Construye una mini base BLAST con 3 transcritos sintéticos: uno es el
    "gen diana" (simula ABCA4), otro comparte una subsecuencia con un
    candidato ASO (simula un off-target real) y un tercero no comparte nada.
    """
    if not BLASTN_AVAILABLE:
        pytest.skip("blastn/makeblastdb no están instalados en este entorno")

    workdir = tmp_path_factory.mktemp("mini_blast_db")
    fasta_path = workdir / "mini_transcriptome.fa"

    # El candidato ASO de prueba será el complemento reverso de esta ventana.
    target_window = "ACGTACGTACGTACGTACGT"  # 20 nt
    off_target_window = "ACGTACGTACGTACGTACGA"  # comparte 19/20 con el anterior (1 mismatch)
    unrelated_window = "TTTTGGGGCCCCAAAATTTT"  # sin relación

    fasta_path.write_text(
        f">ENST_TARGET_GENE.1 gene:ENSG_TARGET.1 gene_symbol:{TARGET_GENE_SYMBOL}\n"
        f"{target_window}\n"
        ">ENST_OFFTARGET_GENE.1 gene:ENSG_OFF.1 gene_symbol:OTHERGENE\n"
        f"{off_target_window}\n"
        ">ENST_UNRELATED_GENE.1 gene:ENSG_UNREL.1 gene_symbol:UNRELATEDGENE\n"
        f"{unrelated_window}\n"
    )

    db_path = workdir / "mini_db"
    subprocess.run(
        ["makeblastdb", "-in", str(fasta_path), "-dbtype", "nucl", "-out", str(db_path)],
        capture_output=True,
        text=True,
        check=True,
    )

    gene_map_path = workdir / "gene_map.tsv"
    gene_map_path.write_text(
        "transcript_id\tgene_id\tgene_symbol\n"
        f"ENST_TARGET_GENE.1\tENSG_TARGET.1\t{TARGET_GENE_SYMBOL}\n"
        "ENST_OFFTARGET_GENE.1\tENSG_OFF.1\tOTHERGENE\n"
        "ENST_UNRELATED_GENE.1\tENSG_UNREL.1\tUNRELATEDGENE\n"
    )

    return {
        "db_path": str(db_path),
        "gene_map_path": str(gene_map_path),
        "target_window": target_window,
    }


@pytest.mark.blast
def test_analyze_off_target_flags_candidate_matching_other_gene(mini_blast_db):
    # El candidato ASO es el complemento reverso EXACTO de target_window: por
    # diseño hibrida perfecto contra el "gen diana" (ABCA4 simulado) y casi
    # perfecto (1 mismatch) contra el transcrito off-target simulado.
    aso_sequence = revcomp(mini_blast_db["target_window"])
    candidate = _candidate(aso_sequence)

    results = analyze_off_target(
        [candidate],
        blast_db=mini_blast_db["db_path"],
        gene_map_path=mini_blast_db["gene_map_path"],
    )
    assert len(results) == 1
    result = results[0]

    # Debe pegar contra el gen diana pero NO contarlo como off-target.
    target_hits = [h for h in result.hits if h.gene_symbol == TARGET_GENE_SYMBOL]
    assert len(target_hits) >= 1

    # Debe anotar severidad != sin_señal por el hit contra OTHERGENE (1
    # mismatch por diseño de la fixture -> severidad moderada), sin
    # descartar el candidato (ya no existe un veredicto binario).
    assert result.severity != SEVERITY_SIN_SENAL
    assert result.off_target_count >= 1
    assert any(h.gene_symbol == "OTHERGENE" for h in result.off_target_hits)
    assert not any(h.gene_symbol == "UNRELATEDGENE" for h in result.off_target_hits)


@pytest.mark.blast
def test_analyze_off_target_no_severity_for_candidate_with_no_homology(mini_blast_db):
    # Un ASO sin ninguna relación con los 3 transcritos sintéticos no debería
    # generar hits que activen la regla de corte -> severidad sin_señal.
    candidate = _candidate("GGGGGCCCCCTTTTTAAAAA")

    results = analyze_off_target(
        [candidate],
        blast_db=mini_blast_db["db_path"],
        gene_map_path=mini_blast_db["gene_map_path"],
    )
    assert results[0].severity == SEVERITY_SIN_SENAL


@pytest.mark.blast
def test_run_blast_raises_clear_error_for_missing_db():
    from pipeline.off_target import run_blast

    with pytest.raises(RuntimeError, match="No se encontró el índice BLAST"):
        run_blast([_candidate("A" * 20)], blast_db="/ruta/que/no/existe/db_falsa")


@pytest.mark.blast
def test_run_blast_uses_repo_default_db_when_none_specified():
    # Sin blast_db explícito, debe caer al default del repo
    # (data/reference/human_transcriptome_db) — que en este entorno de
    # desarrollo ya está construido (ver data/reference/README.md).
    from pipeline.off_target import DEFAULT_BLAST_DB, run_blast

    if not os.path.exists(DEFAULT_BLAST_DB + ".nsq"):
        pytest.skip("data/reference/human_transcriptome_db no está construido en este entorno")

    raw = run_blast([_candidate("A" * 20)], blast_db=None)
    assert isinstance(raw, str)
