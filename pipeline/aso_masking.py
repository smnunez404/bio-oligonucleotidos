"""Módulo 6b — simulación del bloqueo de un ASO por enmascarado de secuencia.

EL PROBLEMA CONCEPTUAL
----------------------
Los predictores de splicing reciben ADN y devuelven, por posición, la probabilidad
de que ahí haya un sitio de splicing. No tienen ninguna representación de "un
oligonucleótido pegado al ARN": su entrada es una sola hebra de secuencia, sin
ligandos.

Un PMO no corta el ARN ni lo modifica — se pega por complementariedad y TAPA esa
región, de modo que la maquinaria de splicing no puede leerla (bloqueo estérico).
Por eso no se puede modelar como una mutación.

LA SOLUCIÓN ADOPTADA
--------------------
La codificación one-hot mapea A/C/G/T a vectores unitarios y cualquier otra letra
(N) al vector nulo — literalmente "acá no hay información de secuencia legible".
Eso es un proxy directo del bloqueo estérico.

**Verificado en los dos predictores** (2026-07-30): SpliceAI mapea N al vector de
ceros en `pipeline.splice_neural.one_hot_encode`, y Pangolin hace lo mismo en su
`IN_MAP` upstream (fila 0 = [0,0,0,0], y su `one_hot_encode` traduce 'N' -> '0').
El método transfiere entre predictores porque ambos comparten esa convención; si
un predictor futuro codificara N de otra forma, este método NO aplicaría y habría
que verificarlo antes de usarlo.

Se descartaron dos alternativas:
  - Mutar la ventana a una secuencia arbitraria: introduce señales espurias
    (el modelo ve un motivo nuevo, no una ausencia).
  - Recortar la ventana: corre todas las coordenadas y cambia el contexto,
    contaminando el resultado con un artefacto de posición.

POR QUÉ EL CRITERIO ES RELATIVO Y NO ABSOLUTO
---------------------------------------------
La primera versión de este módulo usaba un umbral absoluto de caída del score
(-0,43), calibrado sobre la escala de SpliceAI (baseline del donador críptico
0,5595). Ese número es **inalcanzable** en la escala de Pangolin, cuyo baseline
para el mismo sitio es 0,2829: ningún candidato podría bajar 0,43 desde 0,2829,
así que el módulo habría clasificado a los 44 como "sin efecto" sin fallar
ruidosamente.

El criterio correcto es la **fracción del baseline que el sitio retiene**. En la
corrida documentada de SpliceAI (n=44) los deltas se separan en dos grupos con un
hueco enorme entre medio:
  - los 3 que cubren el sitio: retención 0,0 % (score final exactamente 0,000)
  - el más bajo de los 41 que NO lo cubren: retención 45,8 % (cand_5881)
El umbral va en 25 %, dentro de ese hueco vacío y lejos de ambos bordes. Un
umbral relativo es además interpretable: "el sitio conserva menos de un cuarto de
su señal original", frase que significa lo mismo en cualquier escala.

DOS NIVELES DE LECTURA
----------------------
`classify()` responde por SITIO ("¿esta ventana anula el donador críptico?").
`pseudoexon_verdict()` responde la pregunta del proyecto ("¿elimina el
pseudoexón, sin dañar el splicing normal?"), que necesita mirar los DOS bordes
más el sitio canónico. Ver el bloque de comentarios sobre el veredicto.

Esa distinción no es cosmética: con el criterio de un solo sitio, SpliceAI y
Pangolin concuerdan en 35/44 candidatos; con el veredicto a nivel pseudoexón
concuerdan en 44/44. Los desacuerdos del criterio por sitio eran, en su mayoría,
el mismo grupo de candidatos que ataca el aceptor y que el donador no veía.

LO QUE ESTE MÉTODO NO ES
------------------------
No es una medición de eficacia. Enmascarar es binario y total: asume ocupación
del 100 % de las moléculas y bloqueo perfecto. Un ASO real tiene afinidad finita,
compite con proteínas de unión a ARN, y su ocupación depende de dosis y
accesibilidad. El resultado es una condición NECESARIA (si enmascarar no baja el
score, el ASO difícilmente funcione) pero NO SUFICIENTE.

Los controles que validan el método están en `tests/test_aso_masking.py`; las
corridas documentadas, en wiki/decisiones/0008, 0010 y las bitácoras del
2026-07-30.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Protocol

MASK_CHAR = "N"

# --- Criterio de clasificación, relativo al baseline del predictor ------------

BLOCK_RETENTION = 0.25
"""Un candidato BLOQUEA si el sitio retiene menos de esta fracción del baseline.

Calibrado sobre el hueco vacío de la corrida de SpliceAI (0 % vs 45,8 %). Ver el
docstring del módulo.
"""

COUNTERPRODUCTIVE_GAIN = 0.18
"""Un candidato es CONTRAPRODUCENTE si SUBE el score en esta fracción del baseline.

Equivale al umbral absoluto original de +0,10 sobre el baseline 0,5595 de SpliceAI
(0,10 / 0,5595 = 0,1787), redondeado a 0,18.
"""

# Umbrales absolutos de la corrida original de SpliceAI. Se conservan solo para
# retrocompatibilidad de la clasificación ya publicada; el criterio vivo es el
# relativo de arriba. NO usar con otro predictor.
SPLICEAI_BASELINE_DONOR = 0.5595
BLOCK_DELTA = -0.43
COUNTERPRODUCTIVE_DELTA = 0.10

BLOCKS = "bloquea"
NO_EFFECT = "sin_efecto"
COUNTERPRODUCTIVE = "contraproducente"


def classify(score: float, baseline: float) -> str:
    """Clasifica un candidato por el efecto de su ventana sobre un sitio.

    Es la ÚNICA función de clasificación del módulo: el router y el runner la
    usan, para que no puedan divergir. Trabaja en fracción del baseline, así que
    sirve para cualquier predictor.
    """
    if baseline <= 0:
        raise ValueError(
            f"baseline={baseline}: sin señal en el sitio no hay nada que bloquear"
        )
    retention = score / baseline
    if retention < BLOCK_RETENTION:
        return BLOCKS
    if retention - 1.0 >= COUNTERPRODUCTIVE_GAIN:
        return COUNTERPRODUCTIVE
    return NO_EFFECT


# --- Veredicto a nivel pseudoexón ---------------------------------------------
#
# POR QUÉ HACE FALTA UN SEGUNDO NIVEL
# -----------------------------------
# `classify()` responde "¿esta ventana anula ESTE sitio?". Pero la pregunta
# biológica del proyecto es otra: "¿esta ventana elimina el pseudoexón?".
#
# Para que la maquinaria de splicing incluya un pseudoexón necesita RECONOCER SUS
# DOS BORDES: el aceptor (dónde empieza) y el donador (dónde termina). Es como una
# grapa: alcanza con romper una de las dos patas. Anular CUALQUIERA de los dos
# bordes elimina el pseudoexón.
#
# Mirar solo el donador —como hacía la primera versión de este módulo— subestima
# el número de candidatos útiles. En la corrida documentada del 2026-07-30, siete
# candidatos que el criterio "solo donador" clasificaba como `sin_efecto` aniquilan
# el ACEPTOR críptico (retención 0,009-0,077 en SpliceAI y 0,002-0,034 en Pangolin)
# sin siquiera cubrirlo: caen 9-14 nt aguas arriba, sobre el tracto de
# polipirimidina que el aceptor necesita para ser reconocido.
#
# Y hay un requisito de seguridad que no puede faltar: el ASO no debe dañar el
# donador CANÓNICO del exón 3. Si lo dañara, arreglaría el pseudoexón rompiendo
# el splicing normal — peor que la enfermedad.

USEFUL = "anula_pseudoexon"
HARMFUL = "daña_canonico"
INEFFECTIVE = "sin_efecto"

CANONICAL_SAFE_RETENTION = 0.80
"""El sitio canónico debe retener al menos esta fracción de su señal.

En la corrida documentada los candidatos útiles lo dejan entre 1,000 y 1,070 (o
sea intacto), y el control que lo tapa a propósito lo lleva a 0,000. El umbral en
0,80 está lejos de ambos extremos.
"""


def pseudoexon_verdict(
    retention: dict[str, float],
    donor_site: str = "donador_criptico",
    acceptor_site: str = "aceptor_criptico",
    canonical_site: str = "donador_canonico_e3",
) -> tuple[str, list[str]]:
    """¿Esta ventana elimina el pseudoexón, y sin dañar el splicing normal?

    Devuelve (veredicto, bordes_anulados). El veredicto es:
      - HARMFUL   si daña el sitio canónico (se descarta, sin importar lo demás)
      - USEFUL    si anula al menos uno de los dos bordes del pseudoexón
      - INEFFECTIVE en cualquier otro caso

    Trabaja sobre retenciones (fracción del baseline), así que sirve para
    cualquier predictor. Ver el bloque de comentarios de arriba.
    """
    for site in (donor_site, acceptor_site, canonical_site):
        if site not in retention:
            raise KeyError(f"falta la retención del sitio {site!r}; se midieron {sorted(retention)}")

    if retention[canonical_site] < CANONICAL_SAFE_RETENTION:
        return HARMFUL, []

    borders = [
        label
        for label, site in (("donador", donor_site), ("aceptor", acceptor_site))
        if retention[site] < BLOCK_RETENTION
    ]
    return (USEFUL if borders else INEFFECTIVE), borders


def mask_window(sequence: str, start: int, end: int) -> str:
    """Reemplaza [start, end) por N. No cambia la longitud, así que todas las
    coordenadas del resto de la secuencia se mantienen."""
    if not 0 <= start < end <= len(sequence):
        raise ValueError(f"ventana [{start}, {end}) fuera de la secuencia de {len(sequence)} nt")
    return sequence[:start] + MASK_CHAR * (end - start) + sequence[end:]


# --- Abstracción del predictor ------------------------------------------------


class SiteScorer(Protocol):
    """Lo único que el enmascarado necesita de un predictor de splicing.

    Cada predictor tiene su propia convención de alineación entre la secuencia de
    entrada y el array de scores (SpliceAI auto-rellena y devuelve un score por
    base de la entrada; Pangolin solo puntúa las bases centrales tras restar su
    contexto). El adaptador se hace cargo de eso, y este módulo trabaja siempre
    en coordenadas de la secuencia que recibe.
    """

    name: str

    def score_sites(self, sequence: str) -> dict[str, float]:
        """Devuelve {nombre_del_sitio: score} para la secuencia dada."""
        ...


@dataclass
class CallableScorer:
    """Adaptador genérico: envuelve una función y le pone nombre.

    Existe para que los tests puedan inyectar un scorer determinista sin cargar
    177 MB de pesos, y para que agregar un tercer predictor sea escribir una
    función, no tocar este módulo.
    """

    name: str
    fn: Callable[[str], dict[str, float]]

    def score_sites(self, sequence: str) -> dict[str, float]:
        return self.fn(sequence)


@dataclass
class MaskEffect:
    """Efecto de enmascarar una ventana sobre los sitios de interés."""

    name: str
    start: int
    end: int
    scores: dict[str, float]  # nombre del sitio -> score con la ventana enmascarada
    deltas: dict[str, float] = field(default_factory=dict)  # vs. sin enmascarar
    retention: dict[str, float] = field(default_factory=dict)  # score / baseline

    def classification(self, site: str) -> str:
        """Clasificación de esta ventana respecto de `site`."""
        r = self.retention.get(site)
        if r is None:
            raise KeyError(f"sitio {site!r} no evaluado en esta ventana")
        if r < BLOCK_RETENTION:
            return BLOCKS
        if r - 1.0 >= COUNTERPRODUCTIVE_GAIN:
            return COUNTERPRODUCTIVE
        return NO_EFFECT

    def verdict(self, **sites: str) -> tuple[str, list[str]]:
        """¿Elimina el pseudoexón sin dañar el canónico? Ver `pseudoexon_verdict`."""
        return pseudoexon_verdict(self.retention, **sites)

    def blocks(self, site: str) -> bool:
        return self.classification(site) == BLOCKS

    def counterproductive_for(self, site: str) -> bool:
        return self.classification(site) == COUNTERPRODUCTIVE


def evaluate_masks(
    sequence: str,
    scorer: SiteScorer,
    windows: list[tuple[str, int, int]],
) -> tuple[dict[str, float], list[MaskEffect]]:
    """Evalúa el efecto de enmascarar cada ventana sobre cada sitio.

    - `scorer`: adaptador del predictor (ver `SiteScorer`). Sabe qué sitios mira y
      cómo alinear sus scores con `sequence`.
    - `windows`: lista de (nombre, start, end) en coordenadas de `sequence`.

    Devuelve (scores_sin_enmascarar, lista de MaskEffect). La primera corrida es
    siempre el baseline sin enmascarar, así que los deltas y retenciones salen
    del mismo predictor y la misma secuencia — nunca de un número escrito a mano.
    """
    if not windows:
        raise ValueError("hace falta al menos una ventana a evaluar")

    baseline = scorer.score_sites(sequence)
    if not baseline:
        raise ValueError("el scorer no devolvió ningún sitio")

    effects = []
    for nm, start, end in windows:
        sc = scorer.score_sites(mask_window(sequence, start, end))
        missing = set(baseline) - set(sc)
        if missing:
            raise ValueError(f"la ventana {nm} no devolvió los sitios {sorted(missing)}")
        effects.append(
            MaskEffect(
                name=nm,
                start=start,
                end=end,
                scores=sc,
                deltas={k: sc[k] - baseline[k] for k in baseline},
                retention={
                    k: (sc[k] / baseline[k]) if baseline[k] > 0 else float("nan")
                    for k in baseline
                },
            )
        )
    return baseline, effects
