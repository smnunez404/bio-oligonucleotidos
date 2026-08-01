"""Módulo 6 — validación neural del splicing con SpliceAI (inferencia local).

Se usan los 5 modelos Keras que trae el paquete `spliceai` DIRECTAMENTE, en vez de la CLI
oficial (`spliceai -I in.vcf -R ref.fa`), porque esa CLI exige un VCF de variantes más el
FASTA completo del genoma (~3 GB) y solo evalúa variantes. Nuestro caso de uso es evaluar
secuencia arbitraria. Los .h5 tienen firma (None, None, 4) -> (None, None, 3), así que
aceptan cualquier secuencia one-hot. Ver ADR 0007 en el vault.

Requiere el entorno `spliceai` (TensorFlow + setuptools==75.8.0 por `pkg_resources`).
NO requiere GPU: ~11 s por secuencia de 12 kb en 4 núcleos de CPU.
"""

from dataclasses import dataclass, field

import os

import numpy as np

# Contexto que SpliceAI usa para predecir cada posición: 5.000 nt a cada lado.
CONTEXT = 10_000

# Canales de salida del modelo.
CH_NULL, CH_ACCEPTOR, CH_DONOR = 0, 1, 2

# Umbrales de Delta Score publicados por Illumina. Se reportan los tres en vez de
# elegir uno: 0,2 es el que usó Peng et al. (IOVS 2025) para las 7 DIVs de su cohorte.
THRESHOLDS = {"alta_sensibilidad": 0.2, "recomendado": 0.5, "alta_precision": 0.8}

_BASE_INDEX = {"A": 0, "C": 1, "G": 2, "T": 3}


def one_hot_encode(seq: str) -> np.ndarray:
    """Codifica ACGT; cualquier otra letra (N incluido) queda como vector de ceros."""
    x = np.zeros((len(seq), 4), dtype="float32")
    for i, base in enumerate(seq.upper()):
        j = _BASE_INDEX.get(base)
        if j is not None:
            x[i, j] = 1.0
    return x


# Variantes de pesos utilizables. TODAS comparten la arquitectura de SpliceAI-10k
# (entrada (None,None,4), salida (None,None,3), 698.915 parámetros), verificado al
# cargarlas: por eso el mismo código de inferencia sirve para las tres.
#
#   spliceai  -> los 5 modelos originales de Illumina, dentro del paquete `spliceai`.
#   retina    -> Retina-SpliceAI (Riepe et al., CMBI/Radboud UMC, GPL-3.0), reentrenado
#                sobre uniones de splicing de 503 muestras de retina humana. Es el único
#                predictor disponible con el tejido correcto para una distrofia retiniana.
#   gtex      -> control del mismo trabajo: misma arquitectura y mismo procedimiento de
#                entrenamiento, pero con datos de GTEx (sin retina). Sirve para aislar el
#                efecto DEL TEJIDO; comparar contra el SpliceAI original mezclaría el
#                efecto del tejido con el del procedimiento de entrenamiento.
_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_RETINA_DIR = os.path.join(_REPO_ROOT, "data", "reference", "retina_spliceai", "models")

WEIGHT_SETS = {
    "spliceai": None,  # se resuelve vía el paquete instalado
    "retina": os.path.join(_RETINA_DIR, "SpliceAI_optimized_retina_{i}.h5"),
    "gtex": os.path.join(_RETINA_DIR, "SpliceAI_dropout0.3_gtex_all_{i}.h5"),
}
DEFAULT_WEIGHTS = "spliceai"


def load_models(weights: str = DEFAULT_WEIGHTS):
    """Carga los 5 modelos del ensemble pedido. Ver `WEIGHT_SETS`.

    Los .h5 se guardaron con Keras 2.x (~2019) y cargan bien con Keras 3.x, con un aviso
    benigno ("No training configuration found in the save file"): solo indica que no traen
    configuración de entrenamiento, irrelevante para inferencia. Es el punto más probable de
    ruptura en un futuro upgrade de TensorFlow.
    """
    if weights not in WEIGHT_SETS:
        raise ValueError(f"weights debe ser uno de {sorted(WEIGHT_SETS)}, no {weights!r}")

    from keras.models import load_model  # import local: TF tarda en cargar

    pattern = WEIGHT_SETS[weights]
    if pattern is None:
        from pkg_resources import resource_filename

        paths = [resource_filename("spliceai", f"models/spliceai{i}.h5") for i in range(1, 6)]
    else:
        paths = [pattern.format(i=i) for i in range(1, 6)]
        faltan = [p for p in paths if not os.path.exists(p)]
        if faltan:
            raise FileNotFoundError(
                f"faltan {len(faltan)} pesos de '{weights}' (p.ej. {faltan[0]}). "
                "Se instalan desde https://github.com/cmbi/Retina-SpliceAI; ver el README."
            )

    return [load_model(p, compile=False) for p in paths]


def predict_scores(seq: str, models=None) -> np.ndarray:
    """Devuelve el promedio del ensemble, shape (len(seq), 3).

    La secuencia se rellena con `CONTEXT // 2` N a cada lado para que el modelo pueda
    predecir también las posiciones de los extremos.
    """
    models = models if models is not None else load_models()
    padded = "N" * (CONTEXT // 2) + seq + "N" * (CONTEXT // 2)
    x = one_hot_encode(padded)[None, ...]
    return np.mean([m.predict(x, verbose=0)[0] for m in models], axis=0)


@dataclass
class SpliceSiteChange:
    """Un sitio de splicing cuyo score cambia entre wild-type y mutante."""

    offset: int  # posición relativa a la variante, en sentido del transcrito
    kind: str  # "donador" | "aceptor"
    score_wt: float
    score_mut: float

    @property
    def delta(self) -> float:
        return self.score_mut - self.score_wt

    @property
    def crosses(self) -> list[str]:
        """Umbrales publicados que el score mutante supera (y el wild-type no)."""
        return [
            name
            for name, thr in THRESHOLDS.items()
            if self.score_mut >= thr > self.score_wt
        ]


def compare_sequences(
    wildtype: str, mutant: str, variant_offset: int, min_delta: float = 0.05, models=None
) -> list[SpliceSiteChange]:
    """Compara wild-type contra mutante y devuelve los cambios que superan `min_delta`.

    `variant_offset` es el índice de la variante dentro de ambas secuencias (deben tener el
    mismo largo); los offsets devueltos son relativos a esa posición.
    """
    if len(wildtype) != len(mutant):
        raise ValueError(
            f"Las secuencias deben tener el mismo largo ({len(wildtype)} != {len(mutant)})"
        )

    models = models if models is not None else load_models()
    p_wt = predict_scores(wildtype, models)
    p_mut = predict_scores(mutant, models)

    changes = []
    for channel, kind in ((CH_DONOR, "donador"), (CH_ACCEPTOR, "aceptor")):
        delta = p_mut[:, channel] - p_wt[:, channel]
        for i in np.flatnonzero(np.abs(delta) >= min_delta):
            changes.append(
                SpliceSiteChange(
                    offset=int(i) - variant_offset,
                    kind=kind,
                    score_wt=float(p_wt[i, channel]),
                    score_mut=float(p_mut[i, channel]),
                )
            )
    return sorted(changes, key=lambda c: -abs(c.delta))


@dataclass
class PseudoexonHypothesis:
    """Hipótesis de pseudoexón formada emparejando un aceptor con un donador.

    IMPORTANTE: es una hipótesis derivada de emparejar dos sitios predichos, NO una
    medición. El pseudoexón real se confirma por ensayo de minigén.
    """

    acceptor_offset: int
    donor_offset: int

    @property
    def length(self) -> int:
        return self.donor_offset - self.acceptor_offset + 1

    @property
    def in_frame(self) -> bool:
        """Si el largo es múltiplo de 3, la inserción no corre el marco de lectura."""
        return self.length % 3 == 0
