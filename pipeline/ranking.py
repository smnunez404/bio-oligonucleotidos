"""Módulo 7 — ranking multicriterio de los candidatos que anulan el pseudoexón.

POR QUÉ FRENTE DE PARETO Y NO UNA SUMA PONDERADA
------------------------------------------------
Las tres dimensiones que importan tienen unidades incomparables: una fracción de
señal de splicing retenida, una longitud en pares de bases de homología con otro
gen, y un percentil relativo de propiedades fisicoquímicas. Promediarlas exige
inventar una tasa de cambio entre ellas ("cuántos pb de off-target valen 0,01 de
bloqueo") que **ningún dato de este proyecto respalda**: no hay un solo candidato
validado en célula contra el cual calibrar esa tasa.

Un frente de Pareto no necesita esa tasa. Devuelve los candidatos que **no son
superados por ningún otro en las tres dimensiones a la vez**. Es una afirmación
más débil pero verdadera, en vez de un número único que parece preciso y no lo es.

El costo es que devuelve un conjunto, no un ganador. Eso es honesto: con la
evidencia disponible, elegir uno de los tres del frente es una decisión de
criterio humano sobre qué trade-off se prefiere, no un resultado del pipeline.
Ver wiki/decisiones/0011.

LAS TRES DIMENSIONES (todas "más alto = mejor")
-----------------------------------------------
1. `block_strength` — cuánto cae la señal del borde que el ASO anula, promediado
   entre los dos predictores. Se toma el borde MEJOR anulado (la retención mínima
   entre donador y aceptor crípticos), porque anular cualquiera de los dos
   desarma el pseudoexón (ver wiki/decisiones/0012).
2. `offtarget_safety` — negativo del tramo contiguo perfecto más largo contra
   otro gen (Módulo 5). Menos homología contigua = más seguro = valor más alto.
3. `thermo_quality` — media de los percentiles de accesibilidad y de
   no-autodimerización del Módulo 4.

LA CONVENCIÓN QUE HAY QUE DECLARAR
-----------------------------------
Colapsar accesibilidad y homodímero en un solo promedio ES una ponderación
implícita 50/50, o sea exactamente lo que este módulo dice evitar. Se hace igual,
por una razón medida y no estética: con las dos separadas (4 dimensiones) el
frente pasa de 3 a **9 de 10** candidatos, y un frente que no descarta nada no
informa nada. `sensitivity_note()` reporta ese número para que la decisión quede
a la vista y no escondida en el código.

LO QUE ESTE RANKING NO ES
--------------------------
No es una predicción de eficacia. Ordena candidatos por propiedades calculadas in
silico, ninguna validada experimentalmente, sobre una diana sin control positivo
publicado. El frente identifica qué candidatos vale la pena sintetizar primero si
alguna vez se sintetiza alguno — no cuál va a funcionar.
"""

from __future__ import annotations

from dataclasses import dataclass, field

# Dimensiones del ranking, en el orden en que se comparan. El orden no afecta al
# frente de Pareto (la dominancia es simétrica entre dimensiones); está para que
# la salida sea estable y legible.
DIMENSIONS = ("block_strength", "offtarget_safety", "thermo_quality")

# Solo entran al ranking los candidatos que anulan el pseudoexón según AMBOS
# predictores. No es una dimensión más: es la puerta de entrada. Un candidato que
# no anula el pseudoexón no compite por estar mejor rankeado -- no sirve.
ELIGIBLE_VERDICT = "anula_pseudoexon"


@dataclass(frozen=True)
class Objectives:
    """Vector de objetivos de un candidato. Todos "más alto = mejor"."""

    block_strength: float
    offtarget_safety: float
    thermo_quality: float

    def as_tuple(self) -> tuple[float, ...]:
        return tuple(getattr(self, d) for d in DIMENSIONS)


@dataclass
class RankedCandidate:
    name: str
    objectives: Objectives
    in_front: bool
    dominated_by: list[str] = field(default_factory=list)
    # Trazabilidad: los valores crudos de los que salió cada objetivo, para que
    # la UI pueda mostrar POR QUÉ un candidato quedó donde quedó.
    raw: dict = field(default_factory=dict)


def block_strength(retention_by_predictor: dict[str, dict[str, float]]) -> float:
    """Fuerza de bloqueo: 1 − (retención media del borde mejor anulado).

    `retention_by_predictor` es {predictor: {"donador": r, "aceptor": r}}. Por
    cada predictor se toma la retención MÍNIMA de los dos bordes (el que el ASO
    anula mejor) y después se promedian los predictores.

    Promediar los dos predictores acá SÍ es legítimo, a diferencia de promediar
    las tres dimensiones: ambas son la misma magnitud (fracción de señal retenida
    en el mismo sitio), solo que medida por dos instrumentos.
    """
    if not retention_by_predictor:
        raise ValueError("hace falta al menos un predictor para medir el bloqueo")

    per_predictor = []
    for predictor, borders in retention_by_predictor.items():
        if not borders:
            raise ValueError(f"{predictor}: sin retenciones de ningún borde")
        per_predictor.append(min(borders.values()))

    return 1.0 - sum(per_predictor) / len(per_predictor)


def thermo_quality(accessibility_percentile: float, homodimer_percentile: float) -> float:
    """Media de los dos percentiles del Módulo 4. Ver la nota sobre la convención
    50/50 en el docstring del módulo — no es neutral y está medido cuánto pesa."""
    return (accessibility_percentile + homodimer_percentile) / 2.0


def offtarget_safety(longest_perfect_run: int) -> float:
    """Negativo del tramo contiguo perfecto más largo contra otro gen.

    Se niega para que la dimensión sea "más alto = mejor" como las otras dos, y
    así la dominancia se compare igual en las tres sin casos especiales.
    """
    return float(-longest_perfect_run)


def dominates(a: Objectives, b: Objectives) -> bool:
    """¿`a` domina a `b`? Mejor o igual en todo, y estrictamente mejor en algo."""
    ta, tb = a.as_tuple(), b.as_tuple()
    return all(x >= y for x, y in zip(ta, tb)) and any(x > y for x, y in zip(ta, tb))


def pareto_front(objectives_by_name: dict[str, Objectives]) -> list[str]:
    """Nombres no dominados por ningún otro, en orden alfabético (estable)."""
    return sorted(
        name
        for name, obj in objectives_by_name.items()
        if not any(dominates(other, obj) for n, other in objectives_by_name.items() if n != name)
    )


def rank(candidates: list[dict]) -> dict:
    """Rankea candidatos elegibles con un frente de Pareto de tres dimensiones.

    Cada elemento de `candidates` necesita:
      - `name`
      - `verdict_by_predictor`: {predictor: veredicto}
      - `retention_by_predictor`: {predictor: {"donador": r, "aceptor": r}}
      - `longest_perfect_run`: int (Módulo 5)
      - `accessibility_percentile`, `homodimer_percentile`: float (Módulo 4)

    Devuelve el frente, los dominados con quién los domina, y la sensibilidad.
    """
    eligible, rejected = [], []
    for c in candidates:
        verdicts = c.get("verdict_by_predictor") or {}
        if verdicts and all(v == ELIGIBLE_VERDICT for v in verdicts.values()):
            eligible.append(c)
        else:
            rejected.append(c["name"])

    objectives = {
        c["name"]: Objectives(
            block_strength=block_strength(c["retention_by_predictor"]),
            offtarget_safety=offtarget_safety(c["longest_perfect_run"]),
            thermo_quality=thermo_quality(
                c["accessibility_percentile"], c["homodimer_percentile"]
            ),
        )
        for c in eligible
    }

    front = pareto_front(objectives)
    ranked = []
    for c in eligible:
        name = c["name"]
        obj = objectives[name]
        ranked.append(
            RankedCandidate(
                name=name,
                objectives=obj,
                in_front=name in front,
                dominated_by=sorted(
                    n for n, o in objectives.items() if n != name and dominates(o, obj)
                ),
                raw={
                    "longest_perfect_run": c["longest_perfect_run"],
                    "accessibility_percentile": c["accessibility_percentile"],
                    "homodimer_percentile": c["homodimer_percentile"],
                    "retention_by_predictor": c["retention_by_predictor"],
                },
            )
        )

    # El frente primero, y dentro de cada grupo por fuerza de bloqueo descendente.
    ranked.sort(key=lambda r: (not r.in_front, -r.objectives.block_strength, r.name))

    return {
        "front": front,
        "candidates": ranked,
        "n_eligible": len(eligible),
        "n_rejected": len(rejected),
        "rejected": sorted(rejected),
        "sensitivity": sensitivity_note(eligible),
    }


def sensitivity_note(eligible: list[dict]) -> dict:
    """Cuánto cambia el frente si NO se colapsan los dos percentiles térmicos.

    Es el análisis de sensibilidad explícito: si separar accesibilidad de
    homodímero hace que el frente se coma casi todo el conjunto, entonces el
    colapso 50/50 es la decisión que está haciendo el trabajo, y hay que decirlo.
    """
    if not eligible:
        return {"n_front_3d": 0, "n_front_4d": 0, "n_eligible": 0}

    obj3 = {
        c["name"]: Objectives(
            block_strength=block_strength(c["retention_by_predictor"]),
            offtarget_safety=offtarget_safety(c["longest_perfect_run"]),
            thermo_quality=thermo_quality(
                c["accessibility_percentile"], c["homodimer_percentile"]
            ),
        )
        for c in eligible
    }

    # Variante de 4 dimensiones, comparada con tuplas crudas (sin el dataclass,
    # que está fijado a tres).
    obj4 = {
        c["name"]: (
            block_strength(c["retention_by_predictor"]),
            offtarget_safety(c["longest_perfect_run"]),
            float(c["accessibility_percentile"]),
            float(c["homodimer_percentile"]),
        )
        for c in eligible
    }

    def dom4(a, b):
        return all(x >= y for x, y in zip(a, b)) and any(x > y for x, y in zip(a, b))

    front4 = sorted(
        n for n, o in obj4.items() if not any(dom4(p, o) for m, p in obj4.items() if m != n)
    )

    return {
        "n_eligible": len(eligible),
        "n_front_3d": len(pareto_front(obj3)),
        "n_front_4d": len(front4),
        "front_4d": front4,
        "note": (
            "con accesibilidad y homodímero como dimensiones separadas el frente "
            "se ensancha y deja de discriminar. Por eso se colapsan en una sola "
            "dimensión, aceptando que ese promedio 50/50 es una convención "
            "declarada y no un resultado."
        ),
    }
