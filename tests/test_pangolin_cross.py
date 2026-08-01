"""Tests del Módulo 6c (pipeline.pangolin_cross).

No cargan los pesos de Pangolin (177 MB, no están en el repo). Verifican la
aritmética de contexto, la conversión de offsets y el criterio de control
positivo — que es donde estuvo el error de método real: pedir una región
demasiado corta devuelve un único score sin fallar.
"""

import os

import pytest

from pipeline.pangolin_cross import (
    CONTEXT_NT,
    MODEL_NUMS,
    TISSUES,
    SiteComparison,
    offset_to_index,
    one_hot_encode,
    n_scored,
    positive_control_passes,
    rank_peaks,
    require_affinity_disabled,
    required_length,
)

# Valores medidos el 2026-07-30 (ver wiki/decisiones/0009). Promedio de los 4
# tejidos, secuencia mutante, offsets relativos a la variante.
CANONICAL_OFFSETS = [-1092, -999, 395, 536]
CRYPTIC_DONOR_OFFSET = 1
CRYPTIC_ACCEPTOR_OFFSET = -89


def test_contexto_recorta_ambos_lados():
    # La region de 10001 nt que usa SpliceAI daria UN SOLO punto con Pangolin:
    # ese fue el error de metodo que casi paso desapercibido.
    assert n_scored(10001) == 1
    assert n_scored(2 * CONTEXT_NT) == 0
    assert n_scored(100) == 0  # no negativo


def test_required_length_es_inversa_de_n_scored():
    for span in (1, 50, 2401):
        assert n_scored(required_length(span)) == span


def test_required_length_rechaza_span_invalido():
    with pytest.raises(ValueError):
        required_length(0)


def test_padding_6200_cubre_el_rango_de_interes():
    # padding=6200 -> 12401 nt -> 2401 scores, que cubren -1200..+1200.
    seq_len = 2 * 6200 + 1
    assert n_scored(seq_len) == 2401
    variant_offset = 6200
    # los sitios mas extremos que necesitamos puntuar
    for off in CANONICAL_OFFSETS + [CRYPTIC_ACCEPTOR_OFFSET, CRYPTIC_DONOR_OFFSET]:
        i = offset_to_index(off, variant_offset)
        assert 0 <= i < 2401, (off, i)


def test_offset_to_index_ida_y_vuelta():
    variant_offset = 6200
    for off in (-1092, -89, 0, 1, 536):
        i = offset_to_index(off, variant_offset)
        assert i - (variant_offset - CONTEXT_NT) == off


def test_offset_fuera_de_contexto_falla_ruidosamente():
    # con la region de 10001 nt (variant_offset=5000) casi nada es puntuable
    with pytest.raises(IndexError):
        offset_to_index(-1092, 5000)


def _fake_profile(variant_offset=6200, n=2401):
    """Perfil sintetico con los 4 canonicos altos y los 2 cripticos medios."""
    scores = [0.001] * n
    for off, v in [(-1092, 0.55), (-999, 0.62), (395, 0.57), (536, 0.60),
                   (CRYPTIC_DONOR_OFFSET, 0.28), (CRYPTIC_ACCEPTOR_OFFSET, 0.17)]:
        scores[offset_to_index(off, variant_offset)] = v
    return scores


def test_rank_peaks_devuelve_offsets_relativos():
    scores = _fake_profile()
    top = rank_peaks(scores, 6200, top=6)
    offsets = [off for off, _ in top]
    # los 4 canonicos primero (ordenados por score, no por posicion)
    assert set(offsets[:4]) == set(CANONICAL_OFFSETS)
    # luego los 2 cripticos, donador antes que aceptor
    assert offsets[4] == CRYPTIC_DONOR_OFFSET
    assert offsets[5] == CRYPTIC_ACCEPTOR_OFFSET


def test_control_positivo_pasa_con_los_canonicos_arriba():
    assert positive_control_passes(_fake_profile(), 6200, CANONICAL_OFFSETS)


def test_control_positivo_falla_si_un_criptico_supera_a_un_canonico():
    scores = _fake_profile()
    # subir el criptico por encima del canonico mas bajo rompe el control
    scores[offset_to_index(CRYPTIC_DONOR_OFFSET, 6200)] = 0.99
    assert not positive_control_passes(scores, 6200, CANONICAL_OFFSETS)


def test_control_positivo_ignora_magnitudes_absolutas():
    # mismo ranking, escala 10x mas baja: Pangolin da 0,55-0,62 donde SpliceAI
    # da 0,986-0,997 en los MISMOS sitios y ambos son correctos.
    scores = [s / 10 for s in _fake_profile()]
    assert positive_control_passes(scores, 6200, CANONICAL_OFFSETS)


def test_one_hot_trata_N_como_vector_nulo():
    assert one_hot_encode("N") == [[0, 0, 0, 0]]
    assert one_hot_encode("ACGT") == [
        [1, 0, 0, 0], [0, 1, 0, 0], [0, 0, 1, 0], [0, 0, 0, 1]
    ]
    # minusculas y letras raras
    assert one_hot_encode("a") == [[1, 0, 0, 0]]
    assert one_hot_encode("X") == [[0, 0, 0, 0]]


def test_site_comparison_gain_por_tejido():
    sc = SiteComparison(
        label="donador_criptico",
        offset=CRYPTIC_DONOR_OFFSET,
        wildtype={"heart": 0.10, "liver": 0.10, "brain": 0.10, "testis": 0.10},
        mutant={"heart": 0.30, "liver": 0.32, "brain": 0.28, "testis": 0.30},
    )
    assert sc.gain["liver"] == pytest.approx(0.22)
    assert sc.mean_gain == pytest.approx(0.20)
    assert sc.mean_mutant == pytest.approx(0.30)


def test_tejidos_y_modelos_alineados():
    assert len(TISSUES) == len(MODEL_NUMS)
    # ninguno es retina: es una limitacion que hay que seguir declarando
    assert "retina" not in TISSUES


def test_require_affinity_disabled(monkeypatch):
    monkeypatch.delenv("KMP_AFFINITY", raising=False)
    with pytest.raises(RuntimeError, match="KMP_AFFINITY"):
        require_affinity_disabled()
    monkeypatch.setenv("KMP_AFFINITY", "disabled")
    require_affinity_disabled()  # no lanza
