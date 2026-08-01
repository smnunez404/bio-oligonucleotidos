"""Módulo 4 — termodinámica y accesibilidad estructural (ViennaRNA + Biopython).

Para cada candidato ASO calcula cuatro magnitudes, siguiendo el modelo de las
fuentes ingeridas (ver wiki/conceptos/pipeline-bioinformatico-diseno-aso.md):

1. `tm`               — temperatura de fusión del dúplex ASO:ARN.
2. `dg_hybridization` — energía del dúplex ASO:ARN diana (cuánto "quiere" pegarse).
3. `dg_self_structure`— energía de plegado del ASO sobre sí mismo (horquilla).
4. `dg_homodimer`     — energía de dos copias del ASO pegándose entre sí.
5. `accessibility`    — probabilidad de que la ventana diana esté desapareada
                        en el pre-ARNm plegado (si está escondida, el ASO no llega).

=========================  LIMITACIÓN IMPORTANTE  =========================
El proyecto usa química **PMO** (ver wiki/decisiones/0001 en el vault), que
tiene un esqueleto neutro sin carga. **No existen tablas termodinámicas de
vecino-más-cercano públicas y estandarizadas para PMO.** Por lo tanto:

- La Tm se calcula con parámetros de híbrido **ARN/ADN** (`R_DNA_NN1`), el
  proxy publicado más cercano — NO son parámetros de PMO.
- Las energías ΔG se calculan con el modelo de **ARN** de ViennaRNA.

Los valores son por lo tanto una **aproximación basada en la composición de
bases**, útil para comparar candidatos ENTRE SÍ (ranking relativo), pero no
para afirmar valores absolutos de un PMO real. Esto debe declararse en
cualquier resultado derivado — es una limitación conocida y aceptada, no un
descuido.
==========================================================================
"""

from dataclasses import dataclass
from functools import lru_cache

import RNA
from Bio.SeqUtils import MeltingTemp as mt

from .oligo_walk import OligoCandidate

# --- Umbrales heurísticos propuestos por las fuentes ingeridas ---
#
# ⚠️ ADVERTENCIA METODOLÓGICA (verificada empíricamente el 2026-07-28):
# las fuentes dan estos umbrales SIN especificar con qué herramienta se
# calcularon. Distintas herramientas (IDT OligoAnalyzer, mfold, ViennaRNA
# duplexfold) computan cosas distintas bajo el mismo nombre "self-dimer ΔG"
# y dan valores sistemáticamente diferentes. Aplicados a la salida de
# `RNA.duplexfold` sobre esta diana concreta, el umbral de homodímero
# descarta el 69% de los candidatos (mediana observada: -8.9 kcal/mol).
#
# Por eso estos umbrales se usan como SEÑALES, no como verdad absoluta, y
# además se reporta el percentil relativo de cada candidato — que sí es
# comparable porque todos se midieron con el mismo método.
TM_MIN = 50.0  # °C
TM_MAX = 65.0  # °C
HAIRPIN_DG_LIMIT = -3.0  # más negativo que esto = horquilla demasiado estable
HOMODIMER_DG_LIMIT = -6.0  # más negativo que esto = tiende a autoensamblarse

# --- Parámetros de plegado local (estilo RNAplfold) ---
PLFOLD_WINDOW = 80  # ventana de plegado local
PLFOLD_MAX_BP_SPAN = 40  # máxima distancia de apareamiento


def _to_rna(seq: str) -> str:
    return seq.upper().replace("T", "U")


@lru_cache(maxsize=8)
def _unpaired_probabilities(rna_seq: str, ulength: int):
    """Matriz de probabilidad de estar desapareado (RNAplfold), cacheada.

    Se calcula UNA vez sobre toda la secuencia diana y luego se consulta por
    ventana — calcularla por candidato sería redundante y mucho más lento.
    Devuelve la matriz 1-based de ViennaRNA: `m[i][u]` = probabilidad de que
    el segmento de longitud `u` que TERMINA en la posición `i` esté desapareado.
    """
    return RNA.pfl_fold_up(rna_seq, ulength, PLFOLD_WINDOW, PLFOLD_MAX_BP_SPAN)


@dataclass
class ThermoResult:
    candidate: OligoCandidate
    tm: float
    dg_hybridization: float
    dg_self_structure: float
    dg_homodimer: float
    accessibility: float | None  # None si no se pudo calcular para esa ventana
    passed: bool
    reasons: list[str]
    # Percentiles relativos (0-100) dentro del lote analizado. Son más
    # interpretables que los valores absolutos, porque todos los candidatos
    # se midieron con el mismo método (ver advertencia metodológica arriba).
    # 100 = el mejor del lote en esa métrica.
    accessibility_percentile: float | None = None
    homodimer_percentile: float | None = None


def _assign_percentiles(results: list["ThermoResult"]) -> None:
    """Asigna percentiles relativos in-place. Mejor = percentil más alto.

    - Accesibilidad: más alta es mejor (la diana está más expuesta).
    - Homodímero: MENOS negativo es mejor (se autoensambla menos).
    """
    if not results:
        return

    def rank(values: list[float], higher_is_better: bool) -> list[float]:
        order = sorted(range(len(values)), key=lambda i: values[i], reverse=not higher_is_better)
        pct = [0.0] * len(values)
        n = len(values)
        for position, idx in enumerate(order):
            # position 0 = peor -> percentil 0 ; position n-1 = mejor -> 100
            pct[idx] = round(100 * position / (n - 1), 1) if n > 1 else 100.0
        return pct

    homodimer_pct = rank([r.dg_homodimer for r in results], higher_is_better=True)
    for r, p in zip(results, homodimer_pct):
        r.homodimer_percentile = p

    with_acc = [r for r in results if r.accessibility is not None]
    if with_acc:
        acc_pct = rank([r.accessibility for r in with_acc], higher_is_better=True)
        for r, p in zip(with_acc, acc_pct):
            r.accessibility_percentile = p


def tm_rna_oriented(candidate: OligoCandidate) -> float:
    """Tm con la orientación que documenta Biopython (la hebra de ARN).

    Es la versión CORRECTA de lo que hoy calcula `analyze_candidate`. No está
    cableada al pipeline a propósito: activarla cambia el conjunto de candidatos
    de entrada de todos los módulos siguientes. Ver el comentario de CRIT-4.

    Para activarla hay que reemplazar en `analyze_candidate`:
        tm = mt.Tm_NN(aso, nn_table=mt.R_DNA_NN1)
    por:
        tm = tm_rna_oriented(candidate)
    y regenerar todos los resultados de `data/results/`.
    """
    return mt.Tm_NN(_to_rna(candidate.target_window), nn_table=mt.R_DNA_NN1)


def analyze_candidate(
    candidate: OligoCandidate,
    unpaired: object | None = None,
) -> ThermoResult:
    """Calcula las magnitudes termodinámicas de un candidato."""
    aso = candidate.aso_sequence.upper()
    aso_rna = _to_rna(aso)
    target_rna = _to_rna(candidate.target_window)

    # 1. Tm del dúplex ASO:ARN (proxy híbrido ARN/ADN — ver limitación arriba).
    #
    # ⚠️ BUG CONOCIDO Y NO CORREGIDO — CRIT-4 de la revisión adversarial.
    #
    # Biopython documenta, para `R_DNA_NN1`: "For RNA/DNA hybridizations seq must
    # be the RNA sequence". Acá se pasa `aso` (la hebra ASO), teniendo
    # `target_rna` ya calculada dos líneas más arriba. La tabla es ASIMÉTRICA
    # (AA/TT = (-7.8, -21.9) vs TT/AA = (-11.5, -36.4)), así que el orden cambia
    # el número: no es una diferencia cosmética.
    #
    # IMPACTO MEDIDO (verificado el 2026-08-01): usar `target_rna` en vez de
    # `aso` mueve el embudo del Módulo 4 de **44 a 16 candidatos**, con solo 6 en
    # común. `cand_5882` -- uno de los 3 del frente de Pareto final -- pasa de
    # 51,40 °C a 37,98 °C y quedaría fuera de rango.
    #
    # POR QUÉ NO SE CORRIGIÓ TODAVÍA: corregirlo no es voltear un argumento, es
    # rehacer el análisis completo (módulos 5, 6b, 6c y 7 corren sobre otro
    # conjunto de entrada). Y hay una pregunta previa sin resolver: este gate
    # absoluto de 50-65 °C descansa sobre DOS supuestos que no aplican a un PMO
    # -- no hay tablas nearest-neighbor para esqueleto neutro, y la corrección
    # salina de Biopython supone un esqueleto cargado. Antes de rehacer el
    # análisis hay que decidir si el gate debe existir para esta química o si Tm
    # debe pasar a percentil relativo, como ya se hizo con accesibilidad y
    # homodímero. Esa decisión es de los autores, no del código.
    #
    # `tm_rna_oriented()` de abajo implementa la versión correcta; el test
    # `test_crit4_bug_de_orientacion_sigue_presente_y_medido` fija el impacto
    # para que no se pierda de vista.
    tm = mt.Tm_NN(aso, nn_table=mt.R_DNA_NN1)

    # 2. Hibridación ASO:diana.
    dg_hybridization = RNA.duplexfold(aso_rna, target_rna).energy

    # 3. Estructura propia del ASO (horquilla). MFE >= 0 significa "sin estructura".
    _, dg_self_structure = RNA.fold(aso_rna)

    # 4. Homodímero: dos copias del mismo ASO.
    dg_homodimer = RNA.duplexfold(aso_rna, aso_rna).energy

    # 5. Accesibilidad de la ventana diana dentro del pre-ARNm plegado.
    accessibility = None
    if unpaired is not None:
        length = candidate.end - candidate.start
        end_1based = candidate.end  # última base 0-based (end-1) -> 1-based = end
        try:
            value = unpaired[end_1based][length]
            # ViennaRNA devuelve None/NaN donde no aplica.
            accessibility = float(value) if value is not None else None
        except (IndexError, TypeError):
            accessibility = None

    reasons = []
    if tm < TM_MIN:
        reasons.append(f"Tm baja ({tm:.1f} °C < {TM_MIN:.0f} °C)")
    if tm > TM_MAX:
        reasons.append(f"Tm alta ({tm:.1f} °C > {TM_MAX:.0f} °C)")
    if dg_self_structure <= HAIRPIN_DG_LIMIT:
        reasons.append(
            f"horquilla demasiado estable ({dg_self_structure:.1f} ≤ {HAIRPIN_DG_LIMIT:.0f} kcal/mol)"
        )
    if dg_homodimer < HOMODIMER_DG_LIMIT:
        reasons.append(
            f"homodímero demasiado estable ({dg_homodimer:.1f} < {HOMODIMER_DG_LIMIT:.0f} kcal/mol)"
        )

    return ThermoResult(
        candidate=candidate,
        tm=tm,
        dg_hybridization=dg_hybridization,
        dg_self_structure=dg_self_structure,
        dg_homodimer=dg_homodimer,
        accessibility=accessibility,
        passed=len(reasons) == 0,
        reasons=reasons,
    )


def analyze_candidates(
    candidates: list[OligoCandidate],
    target_sequence: str | None = None,
) -> list[ThermoResult]:
    """Analiza una lista de candidatos.

    Si se pasa `target_sequence` (la secuencia completa sobre la que se
    generaron los candidatos), se calcula además la accesibilidad de cada
    ventana usando plegado local tipo RNAplfold sobre esa secuencia.
    """
    unpaired = None
    if target_sequence and candidates:
        max_len = max(c.end - c.start for c in candidates)
        unpaired = _unpaired_probabilities(_to_rna(target_sequence), max_len)

    results = [analyze_candidate(c, unpaired) for c in candidates]
    _assign_percentiles(results)
    return results
