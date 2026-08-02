"""Tests del módulo 6 (validación neural del splicing).

Se prueban las partes puras: codificación one-hot, umbrales, y la aritmética de la hipótesis
de pseudoexón. La inferencia en sí no se testea acá porque requiere cargar TensorFlow y los
5 modelos (~11 s por corrida); eso se verifica con el control positivo de sitios canónicos
documentado en la bitácora 2026-07-30.
"""

import numpy as np
import pytest

from pipeline.splice_neural import (
    CONTEXT,
    THRESHOLDS,
    PseudoexonHypothesis,
    SpliceSiteChange,
    one_hot_encode,
)


def test_one_hot_encode_orden_de_bases():
    x = one_hot_encode("ACGT")
    assert np.array_equal(x, np.eye(4, dtype="float32"))


def test_one_hot_encode_n_es_vector_de_ceros():
    """El padding usa N; debe codificar como ausencia de base, no como una base cualquiera."""
    x = one_hot_encode("ANA")
    assert x[1].sum() == 0.0
    assert x[0].sum() == 1.0 and x[2].sum() == 1.0


def test_one_hot_encode_minusculas():
    assert np.array_equal(one_hot_encode("acgt"), one_hot_encode("ACGT"))


def test_contexto_es_el_declarado_por_el_modelo():
    """SpliceAI usa 10 kb de contexto (5 kb por lado). Si esto cambia, el padding rompe."""
    assert CONTEXT == 10_000
    assert CONTEXT % 2 == 0


def test_delta_es_mutante_menos_wildtype():
    c = SpliceSiteChange(offset=1, kind="donador", score_wt=0.194, score_mut=0.560)
    assert c.delta == pytest.approx(0.366, abs=1e-9)


def test_umbrales_cruzados_reporta_solo_los_superados():
    """El donador críptico real: pasa 0,2 pero no 0,5. No debe reportarse como fuerte."""
    c = SpliceSiteChange(offset=1, kind="donador", score_wt=0.194, score_mut=0.560)
    cruzados = c.crosses
    assert "alta_sensibilidad" in cruzados
    assert "recomendado" in cruzados
    assert "alta_precision" not in cruzados


def test_umbral_no_se_cuenta_si_el_wildtype_ya_lo_superaba():
    """Un sitio canónico fuerte en ambas versiones no es una ganancia."""
    c = SpliceSiteChange(offset=536, kind="donador", score_wt=0.991, score_mut=0.991)
    assert c.crosses == []


def test_umbrales_publicados_sin_alterar():
    assert THRESHOLDS == {
        "alta_sensibilidad": 0.2,
        "recomendado": 0.5,
        "alta_precision": 0.8,
    }


def test_pseudoexon_pe1b_reproduce_los_91_pb_medidos():
    """Control cruzado: el aceptor -89 con el donador +1 debe dar los 91 pb del PE1b
    confirmado por minigén en Wang et al. 2025 (Fig. 2B)."""
    pe1b = PseudoexonHypothesis(acceptor_offset=-89, donor_offset=1)
    assert pe1b.length == 91


def test_pe1b_corre_el_marco_de_lectura():
    """91 no es múltiplo de 3, así que la inserción produce corrimiento de marco."""
    assert PseudoexonHypothesis(acceptor_offset=-89, donor_offset=1).in_frame is False


def test_pe1c_medido_es_in_frame():
    """PE1c mide 255 pb (múltiplo de 3): se inserta sin correr el marco."""
    pe1c = PseudoexonHypothesis(acceptor_offset=-253, donor_offset=1)
    assert pe1c.length == 255
    assert pe1c.in_frame is True


def test_pe1d_medido_corre_el_marco():
    pe1d = PseudoexonHypothesis(acceptor_offset=-263, donor_offset=1)
    assert pe1d.length == 265
    assert pe1d.in_frame is False
