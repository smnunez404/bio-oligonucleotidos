# In silico design of antisense oligonucleotides for ABCA4 c.161-395G>A

[![tests](https://img.shields.io/badge/tests-223%20passing-brightgreen)](#tests)
[![status](https://img.shields.io/badge/status-research%20prototype-orange)](#-what-this-is-not)
[![experimental validation](https://img.shields.io/badge/experimental%20validation-none-red)](#-what-this-is-not)

A reproducible computational pipeline that designs candidate **antisense oligonucleotides (ASOs)**,
**PMO chemistry**, to block the aberrant pseudoexon caused by the deep-intronic variant
**ABCA4 c.161-395G>A** — a cause of Stargardt disease type 1.

> 🇪🇸 **[Versión en español →](README.es.md)**

---

## ⚠️ What this is *not*

Please read this before anything else.

- **No ASO has been synthesised or tested.** Every result here is a computational prediction.
- **The pipeline has known defects.** An adversarial review panel of 6 independent reviewers found
  7 critical issues; its verdict was *"reject with invitation to major resubmission"*. They are
  listed openly under [Known issues](#known-issues-from-adversarial-review).
- **This is not medical advice** and not a therapeutic recommendation.

The project's guiding rule is that **every claim declares its evidence level in the same place the
claim is made** — never in a footnote.

---

## The biological problem, in one paragraph

Stargardt disease type 1 is the most common inherited macular dystrophy, caused by biallelic
variants in **ABCA4**. Some pathogenic alleles are not classic coding variants but **deep-intronic**
ones that activate cryptic splice sites, leading the spliceosome to treat an intronic stretch as an
exon — a **pseudoexon** — introducing a premature stop codon.

Splice-switching ASOs bind the pre-mRNA by base complementarity and **sterically block** access to a
splice site without degrading the transcript. Applied to a pseudoexon, they can in principle restore
normal splicing.

No published or patented ASO targets this specific variant. That gap motivates the work — but it
also means **there is no positive control** with which to validate the pipeline end to end.

---

## Pipeline

| # | Module | Question it answers | Result (default parameters) |
|---|---|---|---|
| 1 | `sequence.py` | Where exactly is the variant? | Coordinate confirmed via two independent routes |
| 2 | `oligo_walk.py` | Which windows could be targeted? | **381** candidates |
| 3 | `heuristic_filters.py` | Which are viable oligos (GC%, G-runs)? | 381 → **276** |
| 4 | `thermodynamics.py` | Which bind well and reach the target? | 276 → **44** ⚠️ *see known issues* |
| 5 | `off_target.py` | Which resemble other human genes? | 44 annotated by severity |
| 6 | `splice_neural.py` | Does the variant really create a false site? | Cryptic donor +1, acceptor −89 → 91 bp |
| 6b | `aso_masking.py` | Does each patch switch the false site off? | **10** abolish the pseudoexon |
| 7 | `ranking.py` | Which are worth synthesising first? | Pareto front: **3** candidates |

### Strongest result

The predicted pseudoexon measures **91 bp**, matching *exactly* the PE1b measured by minigene assay
in Peng et al. (IOVS 2025) — two fully independent methods converging on the same number. This is
the claim that survived adversarial review untouched.

### Four predictors — and why their agreement proves less than it seems

| Predictor | Trained on | Verdict (abolish / no effect / harms) |
|---|---|---|
| SpliceAI (Illumina) | tissue-agnostic | 10 / 34 / 0 |
| Pangolin (U. Penn) | 4 tissues, no retina | 10 / 34 / 0 |
| Retina-SpliceAI (Radboud UMC) | 503 human retina samples | 10 / 34 / 0 |
| **GTEx control** | **deliberately the wrong tissue** | **10 / 34 / 0** |

All four select the **same exact set** of 10 candidates.

The fourth row is a **negative control run after adversarial review**, and it undercuts the
project's own earlier claim. The three-predictor agreement was presented as cross-validation; a
model trained on deliberately wrong tissue reproducing it exactly shows the agreement reflects
**shared architecture and shared training annotations**, not tissue-robust biology.

What still holds: the cryptic sites at +1 and −89 do not rest on this agreement — they rest on the
consensus motif and on Pangolin (a different architecture) placing its argmax at exactly those
positions.

---

## Quick start

### Requirements

Three **non-interchangeable** environments. The two neural predictors use frameworks that conflict
(TensorFlow vs PyTorch, over OpenMP and numpy), and the thermodynamics needs a separate compiled C
library.

| Environment | Runs | Hard dependency |
|---|---|---|
| `bio-oligo` | Modules 1–5, 7, backend, tests | ViennaRNA 2.7.2 + BLAST+ 2.17.0 (conda) |
| `spliceai` | Modules 6, 6b | TensorFlow 2.21, `setuptools==75.8.0` |
| `pangolin` | Modules 6c, 6b | PyTorch 2.13, `KMP_AFFINITY=disabled` |

```bash
conda create -n bio-oligo python=3.11
conda install -n bio-oligo -c conda-forge -c bioconda viennarna blast
conda run -n bio-oligo pip install -r requirements/bio-oligo.txt

conda create -n spliceai python=3.11 && conda run -n spliceai pip install -r requirements/spliceai.txt
conda create -n pangolin python=3.11 && conda run -n pangolin pip install -r requirements/pangolin.txt
```

The `spliceai` environment also runs two extra weight sets sharing the SpliceAI-10k architecture —
`retina` and `gtex`, from [Retina-SpliceAI](https://github.com/cmbi/Retina-SpliceAI) (GPL-3.0),
copied into `data/reference/retina_spliceai/models/`. The `gtex` set is the control that isolates
the **tissue** effect: comparing retina against the original SpliceAI would confound tissue with
training procedure.

### Running anything

`scripts/run-in-env.sh` locates the environment (via `BIO_OLIGO_ENV`, conda, micromamba, or the
usual paths) and exports `PATH`, `PYTHONPATH` and `KMP_AFFINITY`:

```bash
scripts/run-in-env.sh python -m pytest tests/ -q
scripts/run-in-env.sh python pipeline/run_calibration.py --predictor retina
scripts/run-in-env.sh blastn -version
```

**Why the wrapper matters:** having the right interpreter is not enough. Module 5 looks for `blastn`
through `shutil.which`, so a Python with all dependencies but without the environment's `PATH` makes
`/api/off-target` return 503 **even when BLAST is installed**. That exact misdiagnosis happened
during development and cost a full module.

### Web platform

```bash
scripts/run-in-env.sh python -m uvicorn backend.main:app --port 8000 --reload
npm --prefix frontend run dev     # http://localhost:5173
```

Ten tabs — one per module plus an explanatory view built from real data. Every tab displays its own
limitations permanently on screen, not hidden behind a tooltip.

---

## Two traps that silently ruin a run

1. **`KMP_AFFINITY=disabled` is mandatory for Pangolin.** Without it, importing `torch` aborts with
   an OpenMP error that never mentions the cause.
2. **Pangolin only scores the *central* bases**, discarding 5000 nt of context per side. With a
   10 kb region it returns **a single point**, without warning. All runs use `padding >= 6000`.

---

## Reproducibility

Every result in `data/results/` has a regeneration command. `data/reference/` (~490 MB: indexed
transcriptome and predictor weights) is **not** versioned — see `data/reference/README.md`.

```bash
# Module 6b masking, per predictor
scripts/run-in-env.sh python pipeline/run_masking.py --predictor {spliceai|pangolin|retina|gtex}

# Module 7 inputs (reproduces the published CSV byte for byte)
scripts/run-in-env.sh python pipeline/run_modulo7_inputs.py

# Calibration against AONs with published efficacy
scripts/run-in-env.sh python pipeline/run_calibration.py --predictor spliceai

# Documentation vault integrity
python3 scripts/lint_vault.py
```

### Tests

```bash
scripts/run-in-env.sh python -m pytest tests/ -q
```

**223 passing, 0 failing, 0 skipped.** Values asserted in tests are the **measured** results of
documented runs, not invented — several tests exist specifically to catch a refactor silently
changing an already-published result. A mutation-testing audit during review killed 23 of 29
injected bugs (79%).

---

## Known issues (from adversarial review)

The project was submitted to a panel of 6 independent reviewers (splicing biology, statistics,
reproducibility, ASO therapeutics, code integrity, and a hostile red team). **These remain open:**

| ID | Issue | Impact |
|---|---|---|
| **CRIT-4** | **Strand-orientation bug in Tm.** Biopython requires the RNA strand for `R_DNA_NN1`; the code passes the ASO | Module 4 funnel goes from **44 to 16** candidates, only 6 in common. One of the three final candidates would not have survived. **Independently verified.** |
| **CRIT-1** | The calibration does not apply the pipeline's selection criterion, and runs in the opposite direction | The 0.974 AUC measures the masking proxy, not the selection criterion |
| **CRIT-2** | The "two borders" rule is operationally a one-border rule | No candidate abolishes only the donor, in any predictor. **Verified.** |
| **CRIT-3** | p = 5.96×10⁻⁵ assumes independence | The 5 known-effective AONs overlap a single site; corrected p is **0.03–0.11** |
| **CRIT-6** | Mislabelled sites in `retina_comparacion.json` | Normalisation used the exon-2 donor labelled as exon 3. **Verified.** |
| **CRIT-5** | The 4 masking controls are scale-invariant | A predictor with no biology at all passes all four |
| **CRIT-7** | The pipeline cannot detect splice-site displacement | It scores 4 fixed offsets and discards the rest of the profile |

**Nothing downstream of Module 4 should be treated as final until CRIT-4 is resolved.**

### What survived the review

- The cryptic donor `GGG|GTAGGT` → `GAG|GTAGGT`: the variant itself installs the −2 consensus
  adenine over an intact GT. Model-free and threshold-free.
- SpliceAI and Pangolin place their argmax at **exactly** −89 and +1, neighbours at ~1e−5.
- All arithmetic: six reviewers, zero calculation errors.
- `rank_summary` matches `scipy.stats.mannwhitneyu` digit for digit.
- The 50/50 thermodynamic convention is **not** cherry-picking: 61 of 101 weight values give the
  identical Pareto front.

---

## Repository layout

```
pipeline/        the 7 modules + reproducible runners
backend/         FastAPI, one router per module
frontend/        React + TypeScript, one tab per module
tests/           221 tests
scripts/         environment wrapper, documentation linter
docs/            methodological progress report (LaTeX + PDF)
data/results/    generated results (versioned)
data/reference/  external data (~490 MB, NOT versioned)
```

Research documentation — 13 ADRs, 15 lab-notebook entries, the claims dossier and the adversarial
review report — lives in a separate Obsidian vault following the *LLM Wiki* pattern.

---

## Declared limitations

Stated with every result, and not to be omitted when communicating it:

- **No experimental validation.** Zero ASOs synthesised or assayed.
- **The `N`-masking proxy does not measure efficacy.** It is binary and total: it assumes 100%
  occupancy and perfect block. A necessary condition, not a sufficient one.
- **PMO chemistry has no published precedent** for this variant, and no standardised
  nearest-neighbour tables exist: Tm and ΔG use an RNA/DNA hybrid proxy.
- **Off-target severity thresholds are uncalibrated** design choices.
- **Predictor agreement is not fully independent** — they share public annotation databases.
- **Retina-SpliceAI is a preprint**, trained on whole retina rather than isolated photoreceptors.

---

## Sources this work builds on

- Peng et al. *IOVS* 2025;66(1):65 — minigene measurement of PE1b/PE1c/PE1d.
- Kaltak et al. *Mol Ther Nucleic Acids* 2023 — the 32-AON oligo-walk that produced QR-1011.
- Jaganathan et al. *Cell* 2019 — SpliceAI. · Zeng & Li 2022 — Pangolin.
- Riepe et al. — Retina-SpliceAI (`github.com/cmbi/Retina-SpliceAI`, GPL-3.0).

---

## Authors

**Sergio Mauricio Nuñez** · **Amyra Sanchez** — YAIS Lab

Built with AI-agent assistance (Claude, Anthropic) for software implementation, pipeline execution
and drafting, under author supervision.

## Licence

Not yet defined. Until a licence file is added, all rights are reserved by the authors.
