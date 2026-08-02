# In silico design of antisense oligonucleotides for ABCA4 c.161-395G>A

[![tests](https://img.shields.io/badge/tests-224%20passing-brightgreen)](#tests)
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

## How this project was built, and who decided what

This section exists because the honest answer changes how the rest should be read.

**Timeline.** The whole project — seven modules, the web platform, the documentation vault, the
adversarial review and the corrections that followed — was built between **28 July and 2 August
2026**. Six days.

**AI assistance was extensive and is disclosed deliberately.** An AI agent (Claude, Anthropic)
wrote the implementation, ran the pipelines and drafted the documentation. That is not a footnote:
it is the reason this repository is organised the way it is, and it is also why the adversarial
review exists.

**What the authors decided, and the agent did not:**

- **The chemistry.** PMO was a scope decision by the project owner, made against the retinal
  literature precedent (2'-MOE/PS), and documented as such with its costs.
- **Commissioning an adversarial review.** Six independent reviewers were tasked with attacking
  the work, precisely because the agent that built it could not be trusted to audit itself. That
  review found 7 critical issues and returned *"reject with invitation to major resubmission"*.
- **Pushing back when the agent was wrong.** Three of the highest-impact errors in this project —
  a binary declared missing while installed, a crash that reached production, and a type-check
  command that verified nothing — surfaced because the authors asked, not because the agent
  noticed. So did the discovery that PMO force-field parameters *do* exist, after the agent had
  asserted they did not.
- **The methodological calls**, taken on the agent's recommendation but with the reasoning made
  explicit first: converting the melting-temperature filter into an annotation (ADR 0014),
  choosing a Pareto front over weighted scoring (ADR 0011), and not publishing the vault.

**What this means for a reader.** The engineering here is agent-produced and should be judged on
its tests and its reproducibility, both of which are open. The *judgement* — what to build, what to
distrust, what to check again — is the authors'. The adversarial review report is the evidence for
which is which, and it is unflattering by design.

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
| 4 | `thermodynamics.py` | Which bind well and reach the target? | 276 → **78** |
| 5 | `off_target.py` | Which resemble other human genes? | 78 annotated by severity |
| 6 | `splice_neural.py` | Does the variant really create a false site? | Cryptic donor +1, acceptor −89 → 91 bp |
| 6b | `aso_masking.py` | Does each patch switch the false site off? | **12** abolish the pseudoexon |
| 7 | `ranking.py` | Which are worth synthesising first? | Pareto front: **3** candidates |

### Strongest result

The predicted pseudoexon measures **91 bp**, matching *exactly* the PE1b measured by minigene assay
in Wang et al. (IOVS 2025) — two fully independent methods converging on the same number. This is
the claim that survived adversarial review untouched.

### Four predictors — and why their agreement proves less than it seems

| Predictor | Trained on | Verdict (abolish / no effect / harms) |
|---|---|---|
| SpliceAI (Illumina) | tissue-agnostic | 12 / 66 / 0 |
| Pangolin (U. Penn) | 4 tissues, no retina | 12 / 66 / 0 |
| Retina-SpliceAI (Radboud UMC) | 503 human retina samples | 12 / 66 / 0 |
| **GTEx control** | **deliberately the wrong tissue** | **11 / 67 / 0** |

The four **no longer agree exactly**: 12 / 11 / 11 / 11, with a common core of 11 and one candidate seen only by SpliceAI. The earlier perfect agreement was partly an artefact of small, heavily filtered candidate sets.

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

# Kaltak 2023 AON sequences (not versioned — see NOTICE)
scripts/run-in-env.sh python pipeline/extract_kaltak_aons.py

# Calibration against AONs with published efficacy
scripts/run-in-env.sh python pipeline/run_calibration.py --predictor spliceai

# Documentation vault integrity
python3 scripts/lint_vault.py
```

### Tests

```bash
scripts/run-in-env.sh python -m pytest tests/ -q
```

**224 passing, 0 failing, 0 skipped.** Values asserted in tests are the **measured** results of
documented runs, not invented — several tests exist specifically to catch a refactor silently
changing an already-published result. A mutation-testing audit during review killed 23 of 29
injected bugs (79%).

---

## Known issues (from adversarial review)

The project was submitted to a panel of 6 independent reviewers (splicing biology, statistics,
reproducibility, ASO therapeutics, code integrity, and a hostile red team). **These remain open:**

| ID | Issue | Impact |
|---|---|---|
| ~~CRIT-4~~ | ✅ **FIXED (2026-08-01).** Tm now computed on the RNA strand, as Biopython documents | Funnel went 44 → **16**. `cand_5882` (previously in the Pareto front) eliminated. Pre-fix results archived in `data/results/pre-crit4-fix/`. **This dissolved the empirical finding behind CRIT-2** — see below |
| **CRIT-1** | The calibration does not apply the pipeline's selection criterion, and runs in the opposite direction | The 0.974 AUC measures the masking proxy, not the selection criterion |
| **CRIT-2** | The "two borders" rule is operationally a one-border rule | No candidate abolishes only the donor, in any predictor. **Verified.** |
| **CRIT-3** | p = 5.96×10⁻⁵ assumes independence | The 5 known-effective AONs overlap a single site; corrected p is **0.03–0.11** |
| **CRIT-6** | Mislabelled sites in `retina_comparacion.json` | Normalisation used the exon-2 donor labelled as exon 3. **Verified.** |
| **CRIT-5** | The 4 masking controls are scale-invariant | A predictor with no biology at all passes all four |
| **CRIT-7** | The pipeline cannot detect splice-site displacement | It scores 4 fixed offsets and discards the rest of the profile |

> **Consequence of fixing CRIT-4, worth stating plainly:** the 7 candidates that abolished the
> acceptor without covering it — the finding that motivated the project's verdict criterion — were
> produced by a thermodynamic filter with the strands inverted. **None survives the corrected
> calculation.** The mechanistic argument stands; its own empirical evidence does not. A bug in
> Module 4 travelled four modules upward and generated a finding, a design record and a published
> conclusion.

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
tests/           224 tests
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

## Manuscript

A methodological preprint covering the pipeline, the equations behind each module, and the
adversarial review as a primary result:

| | |
|---|---|
| English | [`docs/preprint_en/preprint_en.pdf`](docs/preprint_en/preprint_en.pdf) |
| Español | [`docs/preprint_es/preprint_es.pdf`](docs/preprint_es/preprint_es.pdf) |

Both are generated from the same data. The four figures are produced from `data/results/` by
`pipeline/make_figures.py`, so text and figure cannot silently diverge:

```bash
scripts/run-in-env.sh python pipeline/make_figures.py
```

An earlier Spanish progress report is kept at [`docs/articulo_es/`](docs/articulo_es/); it predates
the Tm correction and is retained for the record, not as the current statement of results.

---

## Sources this work builds on

Every citation below was resolved against Crossref or PubMed Central. The full reference list, with
DOIs, is in the preprint.

- **Wang Y, Wang P, Yi Z, et al.** *IOVS* 2025;66(1):65 — minigene measurement of PE1b/PE1c/PE1d.
  [doi:10.1167/iovs.66.1.65](https://doi.org/10.1167/iovs.66.1.65)
- **Kaltak M, de Bruijn P, Piccolo D, et al.** *Mol Ther Nucleic Acids* 2023;31:674–688 — the 32-AON
  oligo-walk that produced QR-1011, used here as the calibration set.
  [doi:10.1016/j.omtn.2023.02.020](https://doi.org/10.1016/j.omtn.2023.02.020)
- **Jaganathan K, et al.** *Cell* 2019;176(3):535–548 — SpliceAI.
  [doi:10.1016/j.cell.2018.12.015](https://doi.org/10.1016/j.cell.2018.12.015)
- **Zeng T, Li YI.** *Genome Biol* 2022;23:103 — Pangolin.
  [doi:10.1186/s13059-022-02664-4](https://doi.org/10.1186/s13059-022-02664-4)
- **Riepe TV, de Bruijn SE, Roosing S, et al.** bioRxiv 2025 — Retina-SpliceAI
  (`github.com/cmbi/Retina-SpliceAI`, GPL-3.0).
  [doi:10.1101/2025.02.10.637427](https://doi.org/10.1101/2025.02.10.637427)
- **Sugimoto N, et al.** *Biochemistry* 1995;34:11211–11216 — the RNA/DNA hybrid nearest-neighbour
  table used for Tm. [doi:10.1021/bi00035a029](https://doi.org/10.1021/bi00035a029)
- **Summerton J, Weller D.** *Antisense Nucleic Acid Drug Dev* 1997;7:187–195 — PMO chemistry.
  [doi:10.1089/oli.1.1997.7.187](https://doi.org/10.1089/oli.1.1997.7.187)
- **Scharner J, et al.** *Nucleic Acids Res* 2020;48(2):802–816 — what BLAST-based off-target
  prediction does and does not capture.
  [doi:10.1093/nar/gkz1132](https://doi.org/10.1093/nar/gkz1132)

---

## Authors

**Sergio Mauricio Nuñez** · **Amyra Sanchez** — YAIS Lab

Built with AI-agent assistance (Claude, Anthropic) for software implementation, pipeline execution
and drafting, under author supervision.

## Licence

**Code: [MIT](LICENSE).** Chosen over Apache-2.0 deliberately: Apache grants an express patent
licence, and this project designs therapeutic candidates in a space with documented
freedom-to-operate questions. MIT is silent on patents.

**Data generated by the pipeline** (`data/results/`) and the report (`docs/`): **CC BY 4.0**.

See [`NOTICE`](NOTICE) for third-party dependencies — including the GPL-3.0 ones, which are **not
distributed** here — and the provenance of external data.

The MIT licence covers the **software**. It grants no rights over the oligonucleotide sequences the
pipeline produces as output, nor over any patent.
