"""Tests HTTP del router /api/off-target (Módulo 5).

No hay tests HTTP previos para los demás routers en este repo (solo del
pipeline en sí) -- estos se agregan porque el router es un entregable
explícito del Módulo 5. Requieren blastn/makeblastdb y los datos de
referencia en data/reference/ (ver data/reference/README.md); se saltan
automáticamente si no están disponibles, igual que los tests `blast` del
pipeline.
"""

import os
import shutil

import pytest
from fastapi.testclient import TestClient

from backend.main import app
from pipeline.off_target import DEFAULT_BLAST_DB

BLASTN_AVAILABLE = shutil.which("blastn") is not None
REFDATA_AVAILABLE = os.path.exists(DEFAULT_BLAST_DB + ".nsq")

pytestmark = pytest.mark.blast

client = TestClient(app)


def _skip_if_no_blast_infra():
    if not BLASTN_AVAILABLE:
        pytest.skip("blastn no está instalado en este entorno")
    if not REFDATA_AVAILABLE:
        pytest.skip("data/reference/human_transcriptome_db no está construido en este entorno")


@pytest.mark.network
def test_get_off_target_returns_200_and_full_funnel():
    _skip_if_no_blast_infra()
    response = client.get("/api/off-target", params={"length": 20, "step": 1, "flank": 200})
    assert response.status_code == 200
    data = response.json()

    assert "funnel" in data
    funnel = data["funnel"]
    assert set(funnel.keys()) == {
        "generated",
        "passed_heuristic",
        "passed_thermo",
        "annotated_off_target",
    }
    # El embudo debe ser monótono no creciente: cada etapa filtra, nunca agrega.
    # El Módulo 5 ya no filtra (ADR 0006): "annotated_off_target" cuenta a
    # TODOS los que llegaron acá, por eso es igual a passed_thermo, no menor.
    assert funnel["generated"] >= funnel["passed_heuristic"] >= funnel["passed_thermo"]
    assert funnel["annotated_off_target"] == funnel["passed_thermo"]

    assert data["analyzed_count"] == funnel["passed_thermo"]
    assert data["analyzed_count"] == funnel["annotated_off_target"]

    # severity_counts debe sumar exactamente al total anotado, y solo usar
    # los 4 niveles válidos (ver pipeline.off_target.SEVERITY_ORDER).
    severity_counts = data["severity_counts"]
    assert set(severity_counts.keys()) == {"alto", "moderado", "leve", "sin_señal"}
    assert sum(severity_counts.values()) == data["analyzed_count"]


@pytest.mark.network
def test_get_off_target_includes_method_caveat_and_rule():
    _skip_if_no_blast_infra()
    response = client.get("/api/off-target", params={"length": 20, "step": 1, "flank": 200})
    assert response.status_code == 200
    data = response.json()

    assert "method_caveat" in data and len(data["method_caveat"]) > 0
    assert data["rule"]["target_gene_symbol"] == "ABCA4"
    assert data["rule"]["min_alignment_length"] == 15
    assert data["rule"]["max_mismatches"] == 4
    assert data["rule"]["severity_levels"] == ["alto", "moderado", "leve", "sin_señal"]
    assert set(data["rule"]["severity_labels"].keys()) == {"alto", "moderado", "leve", "sin_señal"}


@pytest.mark.network
def test_get_off_target_candidate_shape():
    _skip_if_no_blast_infra()
    response = client.get("/api/off-target", params={"length": 20, "step": 1, "flank": 200})
    data = response.json()
    if not data["candidates"]:
        pytest.skip("Ningún candidato sobrevivió los filtros previos con estos parámetros")

    candidate = data["candidates"][0]
    expected_keys = {
        "start",
        "end",
        "aso_sequence",
        "covers_variant",
        "distance_to_variant",
        "severity",
        "severity_label",
        "longest_perfect_run",
        "off_target_count",
        "distinct_genes_hit",
        "worst_hit",
        "hits",
        "reasons",
    }
    assert expected_keys.issubset(candidate.keys())
    assert "passed" not in candidate  # gate binario eliminado (ADR 0006)
    assert candidate["severity"] in {"alto", "moderado", "leve", "sin_señal"}

    # La severidad debe ser consistente con el tramo contiguo reportado
    # (ADR 0006, corrección post-implementación): son la misma magnitud
    # vista de dos formas, no dos cálculos independientes.
    run = candidate["longest_perfect_run"]
    expected_severity = (
        "alto" if run >= 18 else
        "moderado" if run >= 16 else
        "leve" if run >= 13 else
        "sin_señal"
    )
    assert candidate["severity"] == expected_severity

    if candidate["severity"] != "sin_señal":
        assert candidate["worst_hit"] is not None
        assert len(candidate["reasons"]) > 0
        # El tramo contiguo nunca puede superar la ventana del peor hit.
        assert run <= max(h["length"] for h in candidate["hits"])


def test_get_off_target_rejects_invalid_length():
    # No requiere BLAST -- la validación de parámetros ocurre antes de tocar
    # la secuencia o correr blastn (comparte validate_walk_params con M2/M4).
    response = client.get("/api/off-target", params={"length": 999, "step": 1, "flank": 200})
    assert response.status_code == 400
