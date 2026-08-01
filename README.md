# Diseño in silico de un ASO (química PMO) para la variante ABCA4 c.161-395G>A

Pipeline computacional para diseñar candidatos a oligonucleótido antisentido que
corrijan un error de splicing causado por la variante intrónica profunda
**ABCA4 c.161-395G>A**, asociada a **enfermedad de Stargardt tipo 1 (STGD1)**.

> **Estado: investigación en curso, resultados NO validados experimentalmente.**
> Todo lo que produce este repo son predicciones computacionales. Ningún candidato
> se midió en célula. Las limitaciones de cada módulo están declaradas en el código,
> en los ADR del vault y en la sección [Limitaciones](#limitaciones) de acá abajo.

---

## La hipótesis, en una analogía

Un gen es un texto con párrafos útiles (**exones**) separados por relleno
(**intrones**) que la célula recorta antes de leer. La maquinaria que recorta busca
marcas de "acá empieza" y "acá termina".

La variante c.161-395G>A cambia **una sola letra** en medio del relleno del intrón 2,
y eso alcanza para crear una marca nueva donde no había ninguna. La maquinaria se
confunde, conserva un trozo de relleno de **91 pb** (un **pseudoexón**) y el texto
resultante queda corrido: la proteína sale mal.

La estrategia del **ASO** es pegar un parche de ~20 letras encima de la marca falsa
para que la maquinaria no la vea y vuelva a cortar bien. Este repo busca **dónde
pegar el parche**.

---

## Los tres entornos, y por qué son tres

**Esto es lo primero que hay que entender para reproducir cualquier resultado.**
Los dos predictores de splicing usan frameworks que no conviven (TensorFlow vs
PyTorch, con conflictos de OpenMP y de numpy), y la termodinámica necesita una
librería C aparte.

| entorno | qué corre | dependencia dura |
|---|---|---|
| `bio-oligo` | Módulos 1-5 y 7, backend, figuras, tests | ViennaRNA 2.7.2 + BLAST+ 2.17.0 (conda) |
| `spliceai` | Módulos 6 y 6b con SpliceAI | TensorFlow 2.21, `setuptools==75.8.0` |
| `pangolin` | Módulos 6c y 6b con Pangolin | PyTorch 2.13, `KMP_AFFINITY=disabled` |

El entorno `spliceai` corre **tres juegos de pesos** con la misma arquitectura SpliceAI-10k
(`pipeline.splice_neural.WEIGHT_SETS`):

| `--predictor` | pesos | tejido |
|---|---|---|
| `spliceai` | Illumina, dentro del paquete `spliceai` | ninguno (agnóstico) |
| `retina` | [Retina-SpliceAI](https://github.com/cmbi/Retina-SpliceAI), 503 muestras de retina humana | **retina** |
| `gtex` | mismo trabajo, entrenado en GTEx | control sin retina |

Los pesos de `retina`/`gtex` (87 MB) no están en git: se copian desde el repo de origen a
`data/reference/retina_spliceai/models/`. El juego `gtex` existe para **aislar el efecto del
tejido**: comparar retina contra el SpliceAI original mezclaría tejido y procedimiento de
entrenamiento.

```bash
# entorno por defecto
conda create -n bio-oligo python=3.11
conda install -n bio-oligo -c conda-forge -c bioconda viennarna blast
conda run -n bio-oligo pip install -r requirements/bio-oligo.txt

# predictores (uno cada uno, no en el mismo entorno)
conda create -n spliceai python=3.11 && conda run -n spliceai pip install -r requirements/spliceai.txt
conda create -n pangolin python=3.11 && conda run -n pangolin pip install -r requirements/pangolin.txt
```

### `scripts/run-in-env.sh` — para no depender de haber activado el entorno

Cualquier comando del proyecto se puede correr con:

```bash
scripts/run-in-env.sh python -m pytest tests/ -q
scripts/run-in-env.sh python pipeline/run_modulo7_inputs.py
scripts/run-in-env.sh blastn -version
```

Busca el entorno `bio-oligo` por `BIO_OLIGO_ENV`, `conda`, `micromamba` y las rutas
habituales, y exporta `PATH`, `PYTHONPATH` y `KMP_AFFINITY`. `.claude/launch.json`
lo usa para el backend.

**Por qué hace falta:** no alcanza con tener el intérprete correcto. El Módulo 5
busca `blastn` con `shutil.which`, así que un `python` con las dependencias pero sin
el `PATH` del entorno hace que `/api/off-target` devuelva 503 **aunque BLAST esté
instalado**. Ese error de diagnóstico ya pasó (2026-07-31) y costó dar por ausente
un binario que estaba ahí.

### `scripts/lint_vault.py` — revisa el vault de Obsidian

```bash
python3 scripts/lint_vault.py
```

Enlaces rotos, páginas huérfanas y fuentes de `raw/` sin ficha. Ignora los `[[...]]`
que están dentro de bloques o spans de código, porque Obsidian tampoco los
interpreta — un chequeo ingenuo marca como roto el ejemplo de la propia convención
en `AGENTS.md` y enseña a desconfiar del lint.

### Dos trampas que arruinan una corrida sin avisar

1. **`KMP_AFFINITY=disabled` es obligatorio para Pangolin.** Sin esa variable,
   importar `torch` aborta con un error de OpenMP que no menciona la causa.
   `pipeline/pangolin_cross.require_affinity_disabled()` lo verifica y falla con
   mensaje claro.
2. **Pangolin solo puntúa las bases centrales.** Descuenta 5000 nt de contexto a
   cada lado y devuelve `len(seq) - 10000` scores. Con una región de 10.001 nt
   devolvería **un solo punto**, sin error. De ahí que las corridas usen
   `padding >= 6000`. Hay un test que verifica exactamente eso.

---

## Los módulos

| # | qué hace | entorno | ADR |
|---|---|---|---|
| 1 | Trae la región del intrón 2 de Ensembl y confirma la coordenada de la variante | `bio-oligo` | — |
| 2 | Barrido de ventanas de 20 nt (paso 1) sobre la región candidata | `bio-oligo` | 0001 |
| 3 | Filtros heurísticos (GC, corridas de G, complejidad) | `bio-oligo` | 0001 |
| 4 | Termodinámica: accesibilidad del ARN blanco (ViennaRNA) | `bio-oligo` | 0004 |
| 5 | Off-target: BLAST+ contra el transcriptoma humano, con severidad graduada | `bio-oligo` | 0005, 0006 |
| 6 | Validación neural del splicing con SpliceAI | `spliceai` | 0003, 0007 |
| 6b | Simulación del bloqueo del ASO por enmascarado con N | `spliceai` + `pangolin` | 0008, 0010 |
| 6c | Validación cruzada con Pangolin (segundo predictor independiente) | `pangolin` | 0009 |
| 7 | Ranking multicriterio de los candidatos | `bio-oligo` | 0011 |

---

## Cómo se regenera cada resultado

Todos los comandos se corren desde la raíz del repo con `PYTHONPATH=.`.

### `data/results/pangolin_scores.csv` y `pangolin_profile.json` — Módulo 6c
```bash
KMP_AFFINITY=disabled PYTHONPATH=. conda run -n pangolin \
    python pipeline/run_pangolin_cross.py
```
~3 min. Corre el **control positivo antes que nada** y aborta si los cuatro sitios
canónicos no son los cuatro picos más altos del perfil.

### `data/results/modulo6b_windows.json` — las 44 ventanas del embudo
```bash
PYTHONPATH=. conda run -n bio-oligo python pipeline/run_masking.py --emit-windows
```
Materializa qué candidatos sobrevivieron los Módulos 2 → 3 → 4. Va en un archivo
porque el embudo necesita ViennaRNA (`bio-oligo`) y el enmascarado necesita los
pesos del predictor (`spliceai`/`pangolin`), y los entornos son disjuntos. Efecto
secundario deseable: los dos predictores evalúan **las mismas 44 ventanas por
construcción**, no por coincidencia.

### `data/results/modulo6b_masking*.csv` — Módulo 6b, con cada predictor
```bash
# requiere modulo6b_windows.json
PYTHONPATH=. conda run -n spliceai python pipeline/run_masking.py --predictor spliceai
KMP_AFFINITY=disabled PYTHONPATH=. conda run -n pangolin \
    python pipeline/run_masking.py --predictor pangolin
```
~5 min y ~15 min respectivamente (49 inferencias cada uno). **Orden de operaciones
deliberado:** corre los 4 controles del método primero y **aborta sin escribir el
CSV** si alguno falla, así no puede existir un archivo de resultados cuyo método no
haya sido validado en la misma corrida y con el mismo predictor.

### Dependencias externas que NO están en el repo

- **Transcriptoma humano** para el Módulo 5 (~120 MB comprimido, ~150 MB de índice
  BLAST). Se baja de Ensembl y se indexa; ver `data/reference/README.md`.
- **Pesos de los predictores**: vienen dentro de los paquetes `spliceai` (~90 MB) y
  `pangolin` (~177 MB). No hay que bajarlos aparte.

---

## La plataforma visual

```bash
PYTHONPATH=. conda run -n bio-oligo uvicorn backend.main:app --reload   # :8000
cd frontend && npm install && npm run dev                              # :5173
```

El backend sirve los CSV ya calculados: **no** recalcula nada por request (una
corrida de enmascarado son minutos). Si falta un archivo de resultados, el endpoint
devuelve 503 con el comando exacto que lo genera.

---

## Tests

```bash
scripts/run-in-env.sh python -m pytest tests/ -q
```

**203 pasando, 0 fallando, 0 salteados.** Si aparecen tests "salteados por BLAST no
instalado", el problema es el entorno, no el código: ver la sección siguiente.

Corren en `bio-oligo` y **no cargan pesos de ningún predictor**: donde hace falta un
predictor se inyecta un scorer determinista (`CallableScorer`). Los valores numéricos
que aparecen en los tests son los **medidos** en las corridas documentadas, no
inventados — varios tests existen para detectar que un refactor cambió un resultado
ya publicado.

---

## Limitaciones

Estas se declaran en cada resultado y no se pueden omitir al comunicarlo:

- **Nada está validado en célula.** Todo el repo son predicciones.
- **Ningún predictor tiene modelo de retina.** SpliceAI no modela tejido; los cuatro
  tejidos de Pangolin son corazón, hígado, cerebro y testículo. Lo interpretable es
  **la posición** de los picos y **el signo** del cambio, no la magnitud.
- **El acuerdo entre los dos predictores no es del todo independiente**: ambos se
  entrenaron en buena parte sobre las mismas bases públicas de anotaciones.
- **El enmascarado con N es binario y total**: asume ocupación del 100 % de las
  moléculas y bloqueo perfecto. Es condición **necesaria, no suficiente**.
- **El off-target se evalúa contra el transcriptoma, no contra el genoma completo.**
- **Ningún candidato final cubre el aceptor críptico**: de los 20 del barrido que lo
  cubrían, 16 cayeron en filtros heurísticos y 4 en termodinámica.

---

## Documentación

El razonamiento, las decisiones y su evidencia viven en el vault de Obsidian que
acompaña a este repo (`bio-oligonucleotidos-obsidian`):

- `wiki/decisiones/` — ADR: qué se decidió, por qué, y qué alternativas se
  descartaron.
- `wiki/bitacora/` — qué se hizo cada día, con los números medidos.
- `wiki/riesgos/` — lo que puede invalidar un resultado.
- `wiki/estado/auditoria-publicabilidad.md` — qué falta para un manuscrito.
- `index.md` — punto de entrada.
