"""Tests del módulo 6b (simulación de bloqueo del ASO por enmascarado).

Se prueban las partes puras: el enmascarado en sí y la clasificación de efectos.
La inferencia queda fuera a propósito — cargar los pesos tarda decenas de
segundos y GB de RAM, y no corresponde en una suite de tests. Para lo que sí
necesita un predictor se inyecta `CallableScorer`, que es determinista.

Los valores numéricos que aparecen acá son los MEDIDOS en las corridas
documentadas (bitácoras del 2026-07-30), no inventados.
"""

import pytest

from pipeline.aso_masking import (
    BLOCK_RETENTION,
    CANONICAL_SAFE_RETENTION,
    HARMFUL,
    INEFFECTIVE,
    USEFUL,
    pseudoexon_verdict,
    BLOCKS,
    COUNTERPRODUCTIVE,
    COUNTERPRODUCTIVE_GAIN,
    CallableScorer,
    MASK_CHAR,
    MaskEffect,
    NO_EFFECT,
    SPLICEAI_BASELINE_DONOR,
    classify,
    evaluate_masks,
    mask_window,
)

# Baseline del donador críptico medido por cada predictor (mutante sin enmascarar).
BASE_SPLICEAI = SPLICEAI_BASELINE_DONOR  # 0,5595
BASE_PANGOLIN = 0.2829


# --- enmascarado ---------------------------------------------------------------


def test_mask_window_no_cambia_longitud():
    """Crítico: si cambiara la longitud, todas las coordenadas se correrían."""
    seq = "ACGTACGTACGT"
    out = mask_window(seq, 4, 8)
    assert len(out) == len(seq)
    assert out == "ACGT" + MASK_CHAR * 4 + "ACGT"


def test_mask_window_conserva_los_bordes():
    seq = "AAAACCCCGGGG"
    assert mask_window(seq, 4, 8) == "AAAANNNNGGGG"


@pytest.mark.parametrize("start,end", [(-1, 5), (0, 0), (5, 3), (0, 99)])
def test_mask_window_rechaza_ventanas_invalidas(start, end):
    with pytest.raises(ValueError):
        mask_window("ACGTACGT", start, end)


def test_mask_window_ventana_completa():
    assert mask_window("ACGT", 0, 4) == "NNNN"


def test_el_caracter_de_enmascarado_es_el_que_ambos_predictores_mapean_a_cero():
    """No es cosmético: SpliceAI y Pangolin mapean 'N' al vector nulo. Cambiar
    este carácter por cualquier otro rompería el proxy del bloqueo estérico."""
    assert MASK_CHAR == "N"


# --- clasificación relativa ----------------------------------------------------


def _effect(score, baseline, site="donador"):
    return MaskEffect(
        name="x", start=0, end=20,
        scores={site: score},
        deltas={site: score - baseline},
        retention={site: score / baseline},
    )


def test_los_que_cubren_el_sitio_cuentan_como_bloqueo():
    """Los 3 candidatos que cubren el donador lo llevaron a 0,000 exacto."""
    assert _effect(0.0, BASE_SPLICEAI).blocks("donador")


def test_los_controles_lejanos_no_cuentan_como_bloqueo():
    """Ventanas a ±300 nt dieron 0,5644 y 0,5571: ruido, no efecto."""
    assert not _effect(0.5644, BASE_SPLICEAI).blocks("donador")
    assert not _effect(0.5571, BASE_SPLICEAI).blocks("donador")


def test_el_grupo_a_menos_120_no_alcanza_el_umbral_de_bloqueo():
    """Hallazgo real: hay candidatos que bajan el donador ~0,26-0,30 sin cubrirlo.
    Quedan por debajo del umbral, y eso es deliberado — es un efecto de contexto,
    no un bloqueo del sitio. El más bajo retuvo 45,8 % del baseline."""
    assert not _effect(0.5595 - 0.3032, BASE_SPLICEAI).blocks("donador")
    assert not _effect(0.5595 - 0.2617, BASE_SPLICEAI).blocks("donador")


def test_detecta_candidatos_contraproducentes():
    """Hallazgo real: 10 de 44 SUBEN el score del donador. El peor, +0,2099."""
    assert _effect(0.5595 + 0.2099, BASE_SPLICEAI).counterproductive_for("donador")
    assert not _effect(0.5595 + 0.07, BASE_SPLICEAI).counterproductive_for("donador")


def test_el_criterio_relativo_reproduce_la_clasificacion_publicada_de_spliceai():
    """La razón de ser del refactor: cambiar de umbral absoluto a relativo NO
    debe cambiar el resultado ya publicado (3 bloquean / 31 sin efecto / 10
    contraproducentes). Estos son los tres bordes del hueco de calibración."""
    assert classify(0.0000, BASE_SPLICEAI) == BLOCKS                     # cubre el sitio
    assert classify(0.5595 - 0.3032, BASE_SPLICEAI) == NO_EFFECT         # el más bajo que no cubre
    assert classify(0.5595 + 0.2099, BASE_SPLICEAI) == COUNTERPRODUCTIVE # el que más sube


def test_el_umbral_absoluto_viejo_seria_inalcanzable_en_la_escala_de_pangolin():
    """El bug que motivó el refactor, capturado como test.

    El umbral absoluto era -0,43 sobre un baseline de 0,5595. El baseline de
    Pangolin para el mismo sitio es 0,2829: ni anular el sitio por completo
    (delta = -0,2829) alcanza -0,43, así que el módulo habría clasificado a los
    44 candidatos como 'sin efecto' sin fallar ruidosamente.
    """
    delta_maximo_posible = 0.0 - BASE_PANGOLIN
    assert delta_maximo_posible > -0.43, "el umbral absoluto ya no es inalcanzable"
    # El criterio relativo sí detecta el bloqueo en esa escala:
    assert classify(0.0, BASE_PANGOLIN) == BLOCKS


def test_la_clasificacion_es_invariante_a_la_escala_del_predictor():
    """Misma fracción del baseline -> misma clase, sea cual sea el predictor."""
    for frac, esperado in [(0.0, BLOCKS), (0.1, BLOCKS), (0.5, NO_EFFECT),
                           (1.0, NO_EFFECT), (1.3, COUNTERPRODUCTIVE)]:
        assert classify(frac * BASE_SPLICEAI, BASE_SPLICEAI) == esperado
        assert classify(frac * BASE_PANGOLIN, BASE_PANGOLIN) == esperado


def test_baseline_cero_falla_ruidosamente():
    """Si el sitio no tiene señal no hay nada que bloquear, y dividir por cero
    daría inf o nan silencioso. Debe explotar."""
    with pytest.raises(ValueError):
        classify(0.0, 0.0)


def test_sitio_ausente_explota_en_vez_de_devolver_false():
    """Cambio deliberado respecto de la versión anterior: antes un sitio no
    evaluado devolvía False, que es indistinguible de 'evaluado y no bloquea'.
    Ese silencio es justo el tipo de error que este proyecto no puede permitirse."""
    e = _effect(0.0, BASE_SPLICEAI)
    with pytest.raises(KeyError):
        e.blocks("aceptor")


def test_umbrales_tienen_el_signo_y_el_rango_correctos():
    """Guardia contra invertir los signos al refactorizar."""
    assert 0.0 < BLOCK_RETENTION < 1.0
    assert COUNTERPRODUCTIVE_GAIN > 0.0


def test_bloqueo_y_contraproducente_son_mutuamente_excluyentes():
    for frac in (0.0, 0.2, 0.5, 1.0, 1.2, 1.5):
        c = classify(frac * BASE_SPLICEAI, BASE_SPLICEAI)
        assert c in (BLOCKS, NO_EFFECT, COUNTERPRODUCTIVE)


def test_el_umbral_cae_dentro_del_hueco_medido():
    """El umbral de 0,25 no es arbitrario: en la corrida de SpliceAI los que
    bloquean retuvieron 0 % y el mejor de los que no bloquean retuvo 45,8 %.
    Si alguien mueve el umbral fuera de ese hueco, este test falla."""
    assert 0.0 < BLOCK_RETENTION < 0.4581


# --- evaluate_masks con un predictor inyectado --------------------------------


def _fake_scorer():
    """Scorer determinista: el score del sitio es la fracción de bases legibles
    (no-N) en una ventana de 10 nt alrededor del offset 50. Imita el
    comportamiento cualitativo de un predictor real sin cargar pesos."""

    def fn(seq):
        w = seq[45:55]
        legibles = sum(1 for b in w if b != "N")
        return {"sitio": 0.5 * legibles / len(w)}

    return CallableScorer(name="fake", fn=fn)


def test_evaluate_masks_calcula_baseline_deltas_y_retencion():
    seq = "ACGT" * 30
    base, effects = evaluate_masks(seq, _fake_scorer(), [("tapa", 45, 55), ("lejos", 0, 10)])
    assert base["sitio"] == pytest.approx(0.5)
    tapa, lejos = effects
    assert tapa.scores["sitio"] == pytest.approx(0.0)
    assert tapa.retention["sitio"] == pytest.approx(0.0)
    assert tapa.classification("sitio") == BLOCKS
    assert lejos.retention["sitio"] == pytest.approx(1.0)
    assert lejos.classification("sitio") == NO_EFFECT


def test_evaluate_masks_el_baseline_sale_del_predictor_no_de_una_constante():
    """Garantía de método: los deltas se calculan contra el baseline medido en la
    MISMA corrida y con el MISMO predictor, nunca contra un número escrito a mano.
    Si el scorer devuelve otra escala, el baseline la sigue."""
    escalado = CallableScorer(name="x2", fn=lambda s: {"sitio": 2 * _fake_scorer().fn(s)["sitio"]})
    base, effects = evaluate_masks("ACGT" * 30, escalado, [("tapa", 45, 55)])
    assert base["sitio"] == pytest.approx(1.0)
    assert effects[0].retention["sitio"] == pytest.approx(0.0)
    assert effects[0].classification("sitio") == BLOCKS


def test_evaluate_masks_exige_al_menos_una_ventana():
    with pytest.raises(ValueError):
        evaluate_masks("ACGT" * 30, _fake_scorer(), [])


def test_evaluate_masks_detecta_un_scorer_inconsistente():
    """Si el predictor devuelve distintos sitios entre corridas, los deltas serían
    incomparables. Debe fallar en vez de producir un resultado a medias."""
    estado = {"n": 0}

    def inconsistente(seq):
        estado["n"] += 1
        return {"a": 0.5} if estado["n"] == 1 else {"b": 0.5}

    with pytest.raises(ValueError):
        evaluate_masks("ACGT" * 30, CallableScorer("malo", inconsistente), [("w", 0, 10)])


# --- veredicto a nivel pseudoexón ----------------------------------------------
#
# Los números de estos tests son los MEDIDOS en las corridas del 2026-07-30.


def _ret(donor, acceptor, canonical=1.0):
    return {"donador_criptico": donor, "aceptor_criptico": acceptor,
            "donador_canonico_e3": canonical}


def test_anular_el_donador_elimina_el_pseudoexon():
    """cand_5992: tapa el donador críptico. Ambos predictores lo llevan a ~0."""
    v, borders = pseudoexon_verdict(_ret(0.0000, 0.0000, 1.002))
    assert v == USEFUL
    assert borders == ["donador", "aceptor"]


def test_anular_solo_el_aceptor_tambien_elimina_el_pseudoexon():
    """EL HALLAZGO del 2026-07-30, capturado como test.

    cand_5881 (rel −119..−99) NO cubre ninguno de los dos bordes, y el criterio
    "solo donador" lo clasificaba `sin_efecto` (retención 0,458 en SpliceAI).
    Pero aniquila el ACEPTOR (retención 0,036): cae sobre el tracto de
    polipirimidina, 10 nt aguas arriba. Un pseudoexón sin aceptor no se incluye.
    """
    v, borders = pseudoexon_verdict(_ret(0.458, 0.036, 1.001))
    assert v == USEFUL
    assert borders == ["aceptor"]


def test_una_ventana_lejana_no_hace_nada():
    """Control ctrl_far_upstream: retención ~1 en los tres sitios."""
    v, borders = pseudoexon_verdict(_ret(1.009, 1.000, 1.000))
    assert v == INEFFECTIVE
    assert borders == []


def test_dañar_el_canonico_descarta_el_candidato_aunque_anule_el_pseudoexon():
    """Requisito de seguridad: arreglar el pseudoexón rompiendo el splicing normal
    es peor que la enfermedad. El control ctrl_on_canonical_e3 lo lleva a 0,000."""
    v, borders = pseudoexon_verdict(_ret(0.0, 0.0, 0.000))
    assert v == HARMFUL
    assert borders == []


def test_el_veredicto_es_invariante_entre_los_dos_predictores():
    """El grupo −123..−118, con las retenciones medidas por cada predictor.
    Las escalas difieren mucho y el veredicto coincide: eso es el punto."""
    spliceai = [(0.537, 0.077), (0.529, 0.045), (0.521, 0.012),
                (0.501, 0.021), (0.458, 0.036), (0.532, 0.009)]
    pangolin = [(0.178, 0.034), (0.170, 0.013), (0.178, 0.003),
                (0.156, 0.005), (0.155, 0.011), (0.218, 0.002)]
    for (ds, as_), (dp, ap) in zip(spliceai, pangolin):
        vs, _ = pseudoexon_verdict(_ret(ds, as_, 1.0))
        vp, _ = pseudoexon_verdict(_ret(dp, ap, 1.0))
        assert vs == vp == USEFUL, f"{(ds, as_)} vs {(dp, ap)}"


def test_el_grupo_contraproducente_no_es_util():
    """cand_5942/5943 SUBEN el score del donador (retención 1,61-1,68 en Pangolin).
    No anulan ningún borde, así que no sirven — y el veredicto no los premia."""
    v, borders = pseudoexon_verdict(_ret(1.68, 0.98, 1.0))
    assert v == INEFFECTIVE
    assert borders == []


def test_un_sitio_faltante_explota_en_vez_de_asumir_que_esta_intacto():
    """Si no se midió el aceptor, el veredicto no puede concluir nada: asumirlo
    intacto subestimaría candidatos útiles en silencio."""
    with pytest.raises(KeyError):
        pseudoexon_verdict({"donador_criptico": 0.0, "donador_canonico_e3": 1.0})


def test_el_umbral_del_canonico_cae_lejos_de_los_dos_extremos_medidos():
    """Los candidatos útiles dejan el canónico entre 1,000 y 1,070; el control que
    lo tapa lo lleva a 0,000. Si alguien mueve el umbral fuera de ese hueco, falla."""
    assert 0.0 < CANONICAL_SAFE_RETENTION < 1.000


def test_maskeffect_expone_el_veredicto():
    """El veredicto tiene que salir del objeto, no recalcularse en cada consumidor."""
    e = MaskEffect(
        name="x", start=0, end=20,
        scores={}, deltas={},
        retention=_ret(0.458, 0.036, 1.001),
    )
    v, borders = e.verdict()
    assert v == USEFUL and borders == ["aceptor"]
