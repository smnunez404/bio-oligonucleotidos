"""Genera las figuras del preprint a partir de los datos vigentes.

POR QUÉ EXISTE
--------------
Las figuras del informe anterior se generaron el 2026-07-30, con el embudo de 44
candidatos. Tras corregir CRIT-4 y aplicar el ADR 0014 el embudo es de 78, así
que aquellas figuras **contradicen el texto actual**. Este script las regenera
desde `data/results/`, de modo que figura y texto no puedan divergir otra vez.

Todos los conteos salen de los CSV. Nada está escrito a mano: la versión anterior
tenía un 3/3/3 fijo en la figura del control de tejido que ya no correspondía a
los datos, y nadie lo habría notado.

CÓMO CORRERLO
-------------
    scripts/run-in-env.sh python pipeline/make_figures.py            # inglés y español
    scripts/run-in-env.sh python pipeline/make_figures.py --idioma es

Escribe PNG a 300 dpi en `docs/preprint_en/figs/` y `docs/preprint_es/figs/`.
"""

from __future__ import annotations

import argparse
import csv
import json
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from matplotlib.patches import Polygon

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RESULTS = os.path.join(REPO, "data", "results")

SALIDAS = {
    "en": os.path.join(REPO, "docs", "preprint_en", "figs"),
    "es": os.path.join(REPO, "docs", "preprint_es", "figs"),
}

# Paleta sobria, legible en escala de grises y con contraste suficiente.
AZUL, VERDE, NARANJA, GRIS = "#2c5f8a", "#0f766e", "#b45309", "#94a3b8"
ROJO = "#b91c1c"

plt.rcParams.update({
    "font.size": 9, "axes.spines.top": False, "axes.spines.right": False,
    "figure.dpi": 300, "savefig.bbox": "tight", "savefig.dpi": 300,
})

# Los textos van acá y no incrustados, porque el preprint existe en dos idiomas y
# una figura en inglés dentro del PDF en español es exactamente el tipo de
# desprolijidad que este proyecto viene documentando.
T = {
    "en": {
        "etapas": ["Oligo-walk windows", "Heuristic filter", "Thermodynamics",
                   "Abolish pseudoexon", "Pareto front"],
        "x_ventana": "ASO window centre, relative to the variant (nt)",
        "y_retencion": "Cryptic donor signal retained\n(fraction of baseline)",
        "umbral": "block threshold τ = 0.25",
        "donador": "cryptic donor (+1)",
        "aceptor": "cryptic acceptor (−89)",
        "leg_ambos": "abolishes both borders ({n})",
        "leg_aceptor": "abolishes acceptor only ({n})",
        "leg_nada": "no effect ({n})",
        "estados": ["Before review\n(Tm bug)", "Bug fixed\n(Tm still a gate)",
                    "Tm as annotation\n(ADR 0014)"],
        "salida_m4": "Module 4 output",
        "anulan": "abolish pseudoexon",
        "candidatos": "candidates",
        "t_conteos": "Candidate counts",
        "t_solo_acc": "Abolish acceptor without covering it",
        "pesos": ["SpliceAI\n(tissue-agnostic)", "Retina-SpliceAI\n(retina)",
                  "GTEx control\n(wrong tissue)"],
        "wt": "wild type", "mut": "mutant",
        "y_score": "cryptic donor score",
        "t_crea": "The variant strengthens the site in all three",
        "y_anulan": "candidates that abolish\nthe pseudoexon",
        "t_mismo": "...and the wrong tissue picks the same ones",
        "t_casi": "...and the wrong tissue picks nearly the same ones",
        "identicos": "identical sets ({n}/{n})",
    },
    "es": {
        "etapas": ["Ventanas del oligo-walk", "Filtros heurísticos", "Termodinámica",
                   "Anulan el pseudoexón", "Frente de Pareto"],
        "x_ventana": "Centro de la ventana del ASO, relativo a la variante (nt)",
        "y_retencion": "Señal del donador críptico retenida\n(fracción del basal)",
        "umbral": "umbral de bloqueo τ = 0,25",
        "donador": "donador críptico (+1)",
        "aceptor": "aceptor críptico (−89)",
        "leg_ambos": "anula los dos bordes ({n})",
        "leg_aceptor": "anula solo el aceptor ({n})",
        "leg_nada": "sin efecto ({n})",
        "estados": ["Antes de la revisión\n(bug de Tm)", "Bug corregido\n(Tm sigue siendo gate)",
                    "Tm como anotación\n(ADR 0014)"],
        "salida_m4": "salida del Módulo 4",
        "anulan": "anulan el pseudoexón",
        "candidatos": "candidatos",
        "t_conteos": "Conteo de candidatos",
        "t_solo_acc": "Anulan el aceptor sin cubrirlo",
        "pesos": ["SpliceAI\n(agnóstico de tejido)", "Retina-SpliceAI\n(retina)",
                  "Control GTEx\n(tejido equivocado)"],
        "wt": "silvestre", "mut": "mutante",
        "y_score": "score del donador críptico",
        "t_crea": "La variante refuerza el sitio en los tres",
        "y_anulan": "candidatos que anulan\nel pseudoexón",
        "t_mismo": "...y el tejido equivocado elige los mismos",
        "t_casi": "...y el tejido equivocado elige casi los mismos",
        "identicos": "conjuntos idénticos ({n}/{n})",
    },
}


def _load(name):
    with open(os.path.join(RESULTS, name), encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def _guardar(fig, out, nombre):
    os.makedirs(out, exist_ok=True)
    fig.savefig(os.path.join(out, nombre))
    plt.close(fig)
    return nombre


# --- figura 1: el embudo ------------------------------------------------------


def fig_funnel(t, out):
    """Embudo del pipeline con los números vigentes.

    Se dibuja como un embudo que se estrecha de verdad (trapecios apilados) en
    vez de barras de igual altura: con barras, las dos últimas etapas quedaban
    tan finas que el número no entraba adentro y se salía del bloque.
    """
    n_por_etapa = [381, 276, 78, 12, 3]
    etapas = list(zip(t["etapas"], n_por_etapa))
    n0 = n_por_etapa[0]
    # Raíz: con escala lineal las últimas etapas serían invisibles; con log, la
    # primera dejaría de dominar y el embudo no se leería como embudo.
    anchos = [(n / n0) ** 0.38 for n in n_por_etapa]
    anchos.append(anchos[-1] * 0.82)  # la boca de salida

    alto_banda = 1.0
    fig, ax = plt.subplots(figsize=(6.4, 3.4))
    for i, (nombre, n) in enumerate(etapas):
        y0, y1 = -i * alto_banda, -(i + 1) * alto_banda
        w0, w1 = anchos[i] / 2, anchos[i + 1] / 2
        ax.add_patch(Polygon(
            [(-w0, y0), (w0, y0), (w1, y1), (-w1, y1)],
            facecolor=AZUL if i < 3 else VERDE, edgecolor="white", linewidth=1.6))
        # Etiquetas SIEMPRE fuera de la figura: así no dependen del ancho de la
        # banda, que es justo lo que rompía la versión anterior.
        ax.text(-0.62, (y0 + y1) / 2, nombre, ha="right", va="center", fontsize=9)
        ax.text(0.62, (y0 + y1) / 2, str(n), ha="left", va="center",
                fontsize=11, fontweight="bold", color=AZUL if i < 3 else VERDE)

    ax.set_xlim(-2.05, 1.05)
    ax.set_ylim(-len(etapas) * alto_banda - 0.1, 0.1)
    ax.axis("off")
    return _guardar(fig, out, "fig1_funnel.png")


# --- figura 2: el enmascarado -------------------------------------------------


def fig_masking(t, out):
    """Efecto de enmascarar cada ventana sobre el pseudoexón (78 candidatos)."""
    rows = _load("modulo6b_masking.csv")
    fig, ax = plt.subplots(figsize=(6.4, 3.2))

    n_ambos = n_acc = n_nada = 0
    for r in rows:
        x = (int(r["start_rel"]) + int(r["end_rel"])) / 2
        y = float(r["retencion_donador"])
        util = r["veredicto"] == "anula_pseudoexon"
        ambos = r["bordes_anulados"] == "donador+aceptor"
        n_ambos += util and ambos
        n_acc += util and not ambos
        n_nada += not util
        ax.scatter(x, y, s=46 if util else 22,
                   c=VERDE if ambos else (NARANJA if util else "white"),
                   edgecolors=VERDE if util else GRIS,
                   linewidths=1.4 if util else 0.8, zorder=3 if util else 2)

    ax.axhline(0.25, color=VERDE, ls="--", lw=1, zorder=1)
    ax.text(178, 0.29, t["umbral"], fontsize=7.5, color=VERDE, ha="right")
    # Las dos verticales están a 90 nt una de otra; con las etiquetas a la misma
    # altura se pisaban, así que se escalonan hacia afuera.
    ax.axvline(1, color=ROJO, ls=":", lw=1)
    ax.text(6, 1.46, t["donador"], fontsize=7.5, color=ROJO)
    ax.axvline(-89, color=AZUL, ls=":", lw=1)
    ax.text(-94, 1.46, t["aceptor"], fontsize=7.5, color=AZUL, ha="right")

    ax.set_xlabel(t["x_ventana"])
    ax.set_ylabel(t["y_retencion"])
    ax.set_ylim(-0.06, 1.60)

    # La leyenda va FUERA del área de datos: dentro, en cualquier esquina, se
    # montaba sobre el cúmulo de −110 o sobre la línea de umbral.
    ax.legend(handles=[
        Line2D([], [], marker="o", ls="", mfc=VERDE, mec=VERDE, ms=7,
               label=t["leg_ambos"].format(n=n_ambos)),
        Line2D([], [], marker="o", ls="", mfc=NARANJA, mec=VERDE, ms=7,
               label=t["leg_aceptor"].format(n=n_acc)),
        Line2D([], [], marker="o", ls="", mfc="white", mec=GRIS, ms=5,
               label=t["leg_nada"].format(n=n_nada)),
    ], fontsize=7.5, loc="lower center", bbox_to_anchor=(0.5, 1.01), ncol=3,
       frameon=False, handletextpad=0.4, columnspacing=1.6)
    return _guardar(fig, out, "fig2_masking.png")


# --- figura 3: qué cambió la revisión -----------------------------------------


def fig_review_impact(t, out):
    """La figura que sostiene la tesis: qué cambió la revisión adversarial.

    Los dos primeros estados son históricos (están en `data/results/pre-crit4-fix/`
    y en la bitácora); el tercero es el vigente y se lee del CSV actual.
    """
    rows = _load("modulo6b_masking.csv")
    utiles_hoy = sum(r["veredicto"] == "anula_pseudoexon" for r in rows)
    solo_acc_hoy = sum(r["bordes_anulados"] == "aceptor" for r in rows)

    embudo = [44, 16, len(rows)]
    utiles = [10, 3, utiles_hoy]
    solo_acc = [7, 0, solo_acc_hoy]

    fig, axes = plt.subplots(1, 2, figsize=(6.4, 2.9))
    x = range(3)

    axes[0].bar([i - 0.2 for i in x], embudo, 0.4, color=AZUL, label=t["salida_m4"])
    axes[0].bar([i + 0.2 for i in x], utiles, 0.4, color=VERDE, label=t["anulan"])
    for i, (e, u) in enumerate(zip(embudo, utiles)):
        axes[0].text(i - 0.2, e + 1.8, str(e), ha="center", fontsize=8)
        axes[0].text(i + 0.2, u + 1.8, str(u), ha="center", fontsize=8)
    axes[0].set_xticks(list(x)); axes[0].set_xticklabels(t["estados"], fontsize=6.5)
    axes[0].set_ylabel(t["candidatos"]); axes[0].set_ylim(0, max(embudo) * 1.25)
    axes[0].legend(fontsize=7, frameon=False)
    axes[0].set_title(t["t_conteos"], fontsize=9)

    axes[1].bar(x, solo_acc, 0.5, color=NARANJA)
    for i, v in enumerate(solo_acc):
        axes[1].text(i, v + 0.25, str(v), ha="center", fontsize=8)
    axes[1].set_xticks(list(x)); axes[1].set_xticklabels(t["estados"], fontsize=6.5)
    axes[1].set_ylabel(t["candidatos"]); axes[1].set_ylim(0, max(solo_acc) * 1.25)
    axes[1].set_title(t["t_solo_acc"], fontsize=9)

    fig.tight_layout()
    return _guardar(fig, out, "fig3_review_impact.png")


# --- figura 4: el control de tejido -------------------------------------------


def fig_tissue_control(t, out):
    """El control que mostró que la concordancia era trivial."""
    with open(os.path.join(RESULTS, "retina_comparacion.json"), encoding="utf-8") as fh:
        d = json.load(fh)["pesos"]

    pesos = ["spliceai", "retina", "gtex"]
    fig, axes = plt.subplots(1, 2, figsize=(6.4, 2.9))

    wt = [d[p]["donador_criptico"]["wt"] for p in pesos]
    mu = [d[p]["donador_criptico"]["mut"] for p in pesos]
    x = range(len(pesos))
    axes[0].bar([i - 0.2 for i in x], wt, 0.4, color=GRIS, label=t["wt"])
    axes[0].bar([i + 0.2 for i in x], mu, 0.4, color=AZUL, label=t["mut"])
    axes[0].set_xticks(list(x)); axes[0].set_xticklabels(t["pesos"], fontsize=6.5)
    axes[0].set_ylabel(t["y_score"]); axes[0].legend(fontsize=7, frameon=False)
    axes[0].set_title(t["t_crea"], fontsize=9)

    archivos = {"spliceai": "modulo6b_masking.csv",
                "retina": "modulo6b_masking_retina.csv",
                "gtex": "modulo6b_masking_gtex.csv"}
    conjuntos = {
        p: {r["candidato"] for r in _load(f) if r["veredicto"] == "anula_pseudoexon"}
        for p, f in archivos.items()
    }
    n = [len(conjuntos[p]) for p in pesos]

    axes[1].bar(x, n, 0.5, color=[VERDE, VERDE, NARANJA])
    for i, v in enumerate(n):
        axes[1].text(i, v + 0.25, str(v), ha="center", fontsize=9, fontweight="bold")
    axes[1].set_xticks(list(x)); axes[1].set_xticklabels(t["pesos"], fontsize=6.5)
    axes[1].set_ylabel(t["y_anulan"]); axes[1].set_ylim(0, max(n) * 1.35)

    identicos = conjuntos["retina"] == conjuntos["gtex"]
    axes[1].set_title(t["t_mismo"] if identicos else t["t_casi"], fontsize=9)
    if identicos:
        axes[1].annotate(t["identicos"].format(n=len(conjuntos["gtex"])),
                         xy=(1.5, max(n) * 1.16), ha="center", fontsize=7.5, color=NARANJA)
        axes[1].annotate("", xy=(0.85, max(n) * 1.10), xytext=(2.15, max(n) * 1.10),
                         arrowprops=dict(arrowstyle="<->", color=NARANJA, lw=1))

    fig.tight_layout()
    return _guardar(fig, out, "fig4_tissue_control.png")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--idioma", choices=["en", "es"], action="append",
                    help="por defecto genera los dos")
    args = ap.parse_args()

    for idioma in args.idioma or ["en", "es"]:
        out = SALIDAS[idioma]
        print(f"[{idioma}]")
        for fn in (fig_funnel, fig_masking, fig_review_impact, fig_tissue_control):
            print(f"  {fn(T[idioma], out)}")
        print(f"  -> {os.path.relpath(out, REPO)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
