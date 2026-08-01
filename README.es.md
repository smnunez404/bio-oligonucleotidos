# Diseño in silico de oligonucleótidos antisentido para ABCA4 c.161-395G>A

[![tests](https://img.shields.io/badge/tests-221%20pasando-brightgreen)](#tests)
[![estado](https://img.shields.io/badge/estado-prototipo%20de%20investigación-orange)](#️-lo-que-esto-no-es)
[![validación](https://img.shields.io/badge/validación%20experimental-ninguna-red)](#️-lo-que-esto-no-es)

Pipeline computacional reproducible que diseña candidatos a **oligonucleótido antisentido (ASO)**,
química **PMO**, para bloquear el pseudoexón aberrante causado por la variante intrónica profunda
**ABCA4 c.161-395G>A** — causa de enfermedad de Stargardt tipo 1.

> 🇬🇧 **[English version →](README.md)** — el README principal del proyecto está en inglés.

---

## ⚠️ Lo que esto NO es

Leer esto antes que nada.

- **Ningún ASO fue sintetizado ni ensayado.** Todo resultado acá es una predicción computacional.
- **El pipeline tiene defectos conocidos.** Un panel de revisión adversarial de 6 revisores
  independientes encontró 7 problemas críticos; su veredicto fue *"rechazo con invitación a
  resubmisión mayor"*. Están listados abiertamente en
  [Problemas conocidos](#problemas-conocidos-de-la-revisión-adversarial).
- **No es consejo médico** ni una recomendación terapéutica.

La regla que guía el proyecto es que **cada afirmación declara su nivel de evidencia en el mismo
lugar donde se hace** — nunca en una nota al pie.

---

## El problema biológico, en un párrafo

La enfermedad de Stargardt tipo 1 es la distrofia macular hereditaria más frecuente, causada por
variantes bialélicas en **ABCA4**. Algunos alelos patogénicos no son variantes codificantes clásicas
sino **intrónicas profundas**, que activan sitios de splicing crípticos y llevan al espliceosoma a
tratar un tramo intrónico como si fuera un exón — un **pseudoexón** — introduciendo un codón de
parada prematuro.

Los ASO de tipo *splice-switching* se unen al pre-ARNm por complementariedad de bases y **bloquean
estéricamente** el acceso a un sitio de splicing, sin degradar el transcrito. Aplicados sobre un
pseudoexón, pueden en principio restaurar el splicing normal.

No existe ningún ASO publicado ni patentado contra esta variante específica. Ese vacío motiva el
trabajo — pero también significa que **no hay control positivo** con el cual validar el pipeline de
punta a punta.

---

## Pipeline

| # | Módulo | Qué pregunta responde | Resultado (parámetros por defecto) |
|---|---|---|---|
| 1 | `sequence.py` | ¿Dónde está exactamente la variante? | Coordenada confirmada por dos vías independientes |
| 2 | `oligo_walk.py` | ¿Qué ventanas se podrían apuntar? | **381** candidatos |
| 3 | `heuristic_filters.py` | ¿Cuáles son oligos viables (GC%, G-runs)? | 381 → **276** |
| 4 | `thermodynamics.py` | ¿Cuáles se pegan bien y alcanzan la diana? | 276 → **44** ⚠️ *ver problemas conocidos* |
| 5 | `off_target.py` | ¿Cuáles se parecen a otros genes humanos? | 44 anotados por severidad |
| 6 | `splice_neural.py` | ¿La variante crea realmente un sitio falso? | Donador críptico +1, aceptor −89 → 91 pb |
| 6b | `aso_masking.py` | ¿Cada parche apaga el sitio falso? | **10** anulan el pseudoexón |
| 7 | `ranking.py` | ¿Cuáles conviene sintetizar primero? | Frente de Pareto: **3** candidatos |

### El resultado más fuerte

El pseudoexón predicho mide **91 pb**, coincidiendo *exactamente* con el PE1b medido por ensayo de
minigén en Peng et al. (IOVS 2025) — dos métodos completamente independientes convergiendo en el
mismo número. Es la afirmación que salió intacta de la revisión adversarial.

### Tres predictores, uno con el tejido correcto

| Predictor | Entrenado sobre | Veredicto (anula / sin efecto / daña) |
|---|---|---|
| SpliceAI (Illumina) | agnóstico de tejido | 10 / 34 / 0 |
| Pangolin (U. Penn) | 4 tejidos, sin retina | 10 / 34 / 0 |
| **Retina-SpliceAI** (Radboud UMC) | **503 muestras de retina humana** | **10 / 34 / 0** |

Los tres seleccionan **el mismo conjunto exacto** de 10 candidatos. Ver
[Problemas conocidos](#problemas-conocidos-de-la-revisión-adversarial) para entender por qué esa
concordancia es evidencia más débil de lo que parece.

---

## Puesta en marcha

### Requisitos

Tres entornos **no intercambiables**. Los dos predictores neuronales usan frameworks que no conviven
(TensorFlow vs PyTorch, con conflictos de OpenMP y numpy), y la termodinámica necesita una librería
C compilada aparte.

| Entorno | Qué corre | Dependencia dura |
|---|---|---|
| `bio-oligo` | Módulos 1–5, 7, backend, tests | ViennaRNA 2.7.2 + BLAST+ 2.17.0 (conda) |
| `spliceai` | Módulos 6, 6b | TensorFlow 2.21, `setuptools==75.8.0` |
| `pangolin` | Módulos 6c, 6b | PyTorch 2.13, `KMP_AFFINITY=disabled` |

```bash
conda create -n bio-oligo python=3.11
conda install -n bio-oligo -c conda-forge -c bioconda viennarna blast
conda run -n bio-oligo pip install -r requirements/bio-oligo.txt

conda create -n spliceai python=3.11 && conda run -n spliceai pip install -r requirements/spliceai.txt
conda create -n pangolin python=3.11 && conda run -n pangolin pip install -r requirements/pangolin.txt
```

El entorno `spliceai` corre además dos juegos de pesos extra que comparten la arquitectura
SpliceAI-10k — `retina` y `gtex`, de [Retina-SpliceAI](https://github.com/cmbi/Retina-SpliceAI)
(GPL-3.0), copiados a `data/reference/retina_spliceai/models/`. El juego `gtex` es el control que
aísla el efecto del **tejido**: comparar retina contra el SpliceAI original mezclaría el tejido con
el procedimiento de entrenamiento.

### Cómo correr cualquier cosa

`scripts/run-in-env.sh` encuentra el entorno (por `BIO_OLIGO_ENV`, conda, micromamba o las rutas
habituales) y exporta `PATH`, `PYTHONPATH` y `KMP_AFFINITY`:

```bash
scripts/run-in-env.sh python -m pytest tests/ -q
scripts/run-in-env.sh python pipeline/run_calibration.py --predictor retina
scripts/run-in-env.sh blastn -version
```

**Por qué importa el wrapper:** no alcanza con tener el intérprete correcto. El Módulo 5 busca
`blastn` con `shutil.which`, así que un Python con todas las dependencias pero sin el `PATH` del
entorno hace que `/api/off-target` devuelva 503 **aunque BLAST esté instalado**. Ese error de
diagnóstico ocurrió durante el desarrollo y costó un módulo entero.

### Plataforma web

```bash
scripts/run-in-env.sh python -m uvicorn backend.main:app --port 8000 --reload
npm --prefix frontend run dev     # http://localhost:5173
```

Diez pestañas — una por módulo más una vista explicativa construida con datos reales. Cada pestaña
muestra sus propias limitaciones de forma permanente en pantalla, no escondidas en un tooltip.

---

## Dos trampas que arruinan una corrida sin avisar

1. **`KMP_AFFINITY=disabled` es obligatorio para Pangolin.** Sin esa variable, importar `torch`
   aborta con un error de OpenMP que nunca menciona la causa.
2. **Pangolin solo puntúa las bases *centrales***, descontando 5000 nt de contexto por lado. Con una
   región de 10 kb devuelve **un único punto**, sin avisar. Todas las corridas usan
   `padding >= 6000`.

---

## Reproducibilidad

Cada resultado de `data/results/` tiene su comando de regeneración. `data/reference/` (~490 MB:
transcriptoma indexado y pesos de predictores) **no** se versiona — ver `data/reference/README.md`.

```bash
# Enmascarado del Módulo 6b, por predictor
scripts/run-in-env.sh python pipeline/run_masking.py --predictor {spliceai|pangolin|retina|gtex}

# Insumos del Módulo 7 (reproduce el CSV publicado byte a byte)
scripts/run-in-env.sh python pipeline/run_modulo7_inputs.py

# Calibración contra AONs de eficacia publicada
scripts/run-in-env.sh python pipeline/run_calibration.py --predictor spliceai

# Integridad del vault de documentación
python3 scripts/lint_vault.py
```

### Tests

```bash
scripts/run-in-env.sh python -m pytest tests/ -q
```

**221 pasando, 0 fallando, 0 salteados.** Los valores que los tests verifican son los **medidos** en
corridas documentadas, no inventados — varios tests existen justamente para detectar que un refactor
cambió en silencio un resultado ya publicado. Una auditoría de mutación durante la revisión mató 23
de 29 bugs inyectados (79 %).

---

## Problemas conocidos (de la revisión adversarial)

El proyecto se sometió a un panel de 6 revisores independientes (biología del splicing, estadística,
reproducibilidad, terapéutica de ASO, integridad de código, y un red team hostil). **Siguen
abiertos:**

| ID | Problema | Impacto |
|---|---|---|
| **CRIT-4** | **Bug de orientación de hebra en la Tm.** Biopython exige la hebra de ARN para `R_DNA_NN1`; el código pasa el ASO | El embudo del Módulo 4 pasa de **44 a 16** candidatos, con solo 6 en común. Uno de los tres candidatos finales no habría sobrevivido. **Verificado de forma independiente.** |
| **CRIT-1** | La calibración no aplica el criterio de selección del pipeline, y corre en dirección opuesta | El AUC de 0,974 mide el proxy de enmascarado, no el criterio de selección |
| **CRIT-2** | La regla de "dos bordes" es operacionalmente una regla de un borde | Ningún candidato anula solo el donador, en ningún predictor. **Verificado.** |
| **CRIT-3** | p = 5,96×10⁻⁵ asume independencia | Los 5 AONs eficaces conocidos se solapan sobre un único sitio; el p corregido es **0,03–0,11** |
| **CRIT-6** | Sitios mal etiquetados en `retina_comparacion.json` | La normalización usó el donador del exón 2 etiquetado como exón 3. **Verificado.** |
| **CRIT-5** | Los 4 controles del enmascarado son invariantes a escala | Un predictor sin biología alguna pasa los cuatro |
| **CRIT-7** | El pipeline no puede detectar desplazamiento de sitio de splicing | Puntúa 4 offsets fijos y descarta el resto del perfil |

**Nada aguas abajo del Módulo 4 debe considerarse definitivo hasta resolver CRIT-4.**

### Lo que sobrevivió a la revisión

- El donador críptico `GGG|GTAGGT` → `GAG|GTAGGT`: la variante **instala ella misma** la adenina de
  la posición −2 del consenso sobre un GT intacto. Sin modelo y sin umbral.
- SpliceAI y Pangolin ponen su argmax en **exactamente** −89 y +1, con vecinos en ~1e−5.
- Toda la aritmética: seis revisores, cero errores de cálculo.
- `rank_summary` coincide con `scipy.stats.mannwhitneyu` dígito a dígito.
- La convención térmica 50/50 **no** es cherry-picking: 61 de 101 valores de peso dan el mismo
  frente de Pareto.

---

## Estructura del repositorio

```
pipeline/        los 7 módulos + runners reproducibles
backend/         FastAPI, un router por módulo
frontend/        React + TypeScript, una pestaña por módulo
tests/           221 tests
scripts/         wrapper de entorno, linter de documentación
docs/            informe de avance metodológico (LaTeX + PDF)
data/results/    resultados generados (versionados)
data/reference/  datos externos (~490 MB, NO versionados)
```

La documentación de investigación — 13 ADRs, 15 entradas de bitácora, el dossier de afirmaciones y
el informe de revisión adversarial — vive en un vault de Obsidian aparte, siguiendo el patrón
*LLM Wiki*.

---

## Limitaciones declaradas

Se declaran junto a cada resultado, y no pueden omitirse al comunicarlo:

- **Sin validación experimental.** Cero ASOs sintetizados o ensayados.
- **El proxy de enmascarado con `N` no mide eficacia.** Es binario y total: asume 100 % de ocupación
  y bloqueo perfecto. Condición necesaria, no suficiente.
- **La química PMO no tiene precedente publicado** para esta variante, y no existen tablas
  nearest-neighbor estandarizadas: Tm y ΔG usan un proxy de híbrido ARN/ADN.
- **Los umbrales de severidad off-target son elecciones de diseño sin calibrar.**
- **La concordancia entre predictores no es del todo independiente** — comparten bases de anotación
  públicas.
- **Retina-SpliceAI es un preprint**, entrenado sobre retina completa y no sobre fotorreceptores
  aislados.

---

## Fuentes sobre las que se construye este trabajo

- Peng et al. *IOVS* 2025;66(1):65 — medición por minigén de PE1b/PE1c/PE1d.
- Kaltak et al. *Mol Ther Nucleic Acids* 2023 — el oligo-walk de 32 AONs que produjo QR-1011.
- Jaganathan et al. *Cell* 2019 — SpliceAI. · Zeng & Li 2022 — Pangolin.
- Riepe et al. — Retina-SpliceAI (`github.com/cmbi/Retina-SpliceAI`, GPL-3.0).

---

## Autores

**Sergio Mauricio Nuñez** · **Amyra Sanchez** — YAIS Lab

Construido con asistencia de agentes de IA (Claude, Anthropic) para implementación de software,
ejecución de pipelines y redacción, bajo supervisión de los autores.

## Licencia

Todavía sin definir. Hasta que se agregue un archivo de licencia, todos los derechos quedan
reservados a los autores.
