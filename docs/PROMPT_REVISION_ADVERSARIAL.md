# Prompt para la sesión de revisión adversarial

> Copiar **todo** el contenido de abajo (desde la línea `---`) y pegarlo como primer mensaje de una
> sesión nueva de Claude Code, abierta en `/home/mauri/Documentos/projects/bio-oligonucleotidos`.
>
> El prompt es autocontenido: no asume ningún contexto de sesiones previas.

---

# Encargo: revisión adversarial de una investigación bioinformática

Sos el **coordinador** de un panel de revisión. No vas a revisar vos: vas a **desplegar seis
agentes especializados**, cada uno con un rol distinto, y después sintetizar sus hallazgos en un
informe único.

Este trabajo lo construyó un agente de IA que actuó simultáneamente como constructor y como
verificador. Esa es exactamente la razón de esta revisión: **los errores que un constructor
encuentra son los que se le ocurrió buscar**. Hay evidencia concreta de que la presión externa
encontró cosas que la autorrevisión no: durante el desarrollo, tres errores de alto impacto (un
binario que se declaró ausente estando instalado, un crash que llegó a producción, y un comando de
verificación de tipos que no verificaba nada) salieron todos porque el usuario preguntó, no porque
el agente los detectara.

Tu trabajo no es confirmar que el trabajo está bien. Tampoco es demolerlo. Es **determinar qué
afirmaciones se sostienen y cuáles no**, con evidencia.

---

## 1. Contexto del proyecto (lo mínimo para orientarse)

Pipeline computacional que diseña candidatos a **oligonucleótido antisentido (ASO)**, química
**PMO**, para bloquear un pseudoexón causado por la variante intrónica profunda **ABCA4
c.161-395G>A**, asociada a la enfermedad de Stargardt tipo 1.

- **Repositorio de código**: `/home/mauri/Documentos/projects/bio-oligonucleotidos`
- **Vault de documentación (Obsidian, markdown plano)**:
  `/home/mauri/Documentos/projects/bio-oligonucleotidos-obsidian`
- 7 módulos, 221 tests, 13 ADRs, 14 entradas de bitácora.
- **Ningún ASO fue sintetizado ni ensayado.** Todo es predicción computacional.

### Punto de entrada obligatorio

**`wiki/estado/2026-08-01-dossier-de-afirmaciones.md`** (en el vault) — contiene las ~28
afirmaciones del proyecto, cada una con su nivel de evidencia, su archivo de respaldo y su comando
de regeneración. Está organizado en bloques A–G. **Todos los agentes deben leerlo primero.**

### Cómo correr cosas

El entorno se resuelve solo con un wrapper. Desde la raíz del repo:

```bash
scripts/run-in-env.sh python -m pytest tests/ -q        # 221 tests
scripts/run-in-env.sh python -m pytest tests/ -q -rs    # con razones de skip
python3 scripts/lint_vault.py                            # integridad del vault
```

Datos ya generados en `data/results/` (CSV y JSON). Regenerarlos requiere predictores neuronales
(minutos de CPU) — **no hace falta regenerar todo**; sí verificar que los números citados coincidan
con los archivos.

---

## 2. Reglas de enfrentamiento (leer antes de desplegar nada)

Estas reglas son **obligatorias para todos los agentes**. Incluilas textualmente en cada prompt que
les pases.

1. **Crítica verificable, no performativa.** No se pide "ser duro". Se pide contrastar cada
   afirmación contra su evidencia. Un hallazgo sin evidencia que lo respalde es ruido, y el ruido
   hace *más* difícil encontrar los problemas reales.
2. **Toda objeción debe citar**: archivo, línea o número concreto, y por qué la evidencia no
   sostiene la afirmación.
3. **Distinguir tres cosas distintas**: (a) la afirmación es falsa, (b) la afirmación es más fuerte
   que su evidencia, (c) la afirmación está bien pero mal comunicada. Son severidades distintas.
4. **Está permitido y es deseable confirmar.** Si una afirmación se sostiene, decilo. Un informe
   que solo lista problemas no permite distinguir lo sólido de lo frágil.
5. **Correr el código.** No revisar solo prosa. Recalcular números, correr los tests, abrir los
   CSV.
6. **Buscar activamente lo que NO está.** Controles ausentes, casos borde no testeados, supuestos
   no declarados. Lo que falta no aparece leyendo lo que hay.
7. **No inventar literatura.** Si se cita un paper o un hecho de dominio, tiene que ser real y
   verificable. Ante duda, marcarlo como "a verificar" en vez de afirmarlo.

### Formato de hallazgo (usar exactamente este)

```
ID: [AGENTE]-[N]
SEVERIDAD: CRÍTICO | MAYOR | MENOR | OBSERVACIÓN | CONFIRMACIÓN
AFIRMACIÓN AFECTADA: [fila del dossier, ej. C4, o "no está en el dossier"]
UBICACIÓN: [archivo:línea o archivo del vault]
QUÉ ENCONTRÉ: [1-3 frases]
EVIDENCIA: [el número, el comando corrido, la salida]
POR QUÉ IMPORTA: [consecuencia concreta]
QUÉ HARÍA: [corrección sugerida, o "declararlo como limitación"]
```

**Severidades**: CRÍTICO = invalida una conclusión central. MAYOR = obliga a debilitar una
afirmación. MENOR = corregible sin cambiar conclusiones. OBSERVACIÓN = mejora opcional.
CONFIRMACIÓN = se verificó y se sostiene.

---

## 3. Los seis agentes

Desplegá los seis **en paralelo**. Pasá a cada uno: el contexto de la sección 1, las reglas de la
sección 2, y su encargo específico de abajo.

---

### AGENTE 1 — Biología del splicing

**Perfil**: biólogo molecular especializado en regulación del splicing y pseudoexones. Revisa el
razonamiento mecanístico, no el código.

**Qué examinar**:
- `wiki/decisiones/0008-enmascarado-n-para-simular-bloqueo-aso.md` — el proxy central del proyecto
- `wiki/decisiones/0012-veredicto-pseudoexon-no-solo-por-sitio.md`
- `wiki/entidades/variante-c161-395G-A.md`, `wiki/conceptos/splicing-y-pseudoexones.md`
- Bloques **B**, **C** y **E** del dossier

**Preguntas que debe responder**:
1. **El proxy de enmascarado**: reemplazar la ventana del ASO por `N` (vector nulo en la
   codificación one-hot) para simular bloqueo estérico de un PMO — ¿es biológicamente defendible?
   ¿Qué fenómenos reales no captura? ¿Hay alguna alternativa mejor que no se consideró?
2. **El criterio de los dos bordes**: el proyecto afirma que anular *cualquiera* de los dos bordes
   de un pseudoexón lo elimina. ¿Es correcto según la literatura de definición de exón? ¿Hay
   contraejemplos?
3. **PE1c y PE1d**: el modelo explica PE1b (91 pb) pero da 0,016 y 0,042 en los aceptores que
   explicarían los otros dos pseudoexones reportados. ¿Qué explica esa discrepancia? ¿Debilita la
   confianza en PE1b?
4. **Los 7 candidatos que anulan el aceptor sin cubrirlo** cayendo sobre el tracto de
   polipirimidina 9-14 nt aguas arriba — ¿es un mecanismo real y esperable, o un artefacto del
   modelo?
5. **Retina**: el predictor de retina se entrenó sobre retina completa, pero ABCA4 se expresa en
   fotorreceptores. ¿Cuánto compromete eso las conclusiones?
6. La coincidencia de 91 pb con el minigén de Peng et al. 2025 — ¿es tan fuerte como el proyecto
   afirma, o hay explicaciones alternativas (p. ej. que ambos métodos hereden el mismo sesgo de
   anotación)?

---

### AGENTE 2 — Estadística y métodos cuantitativos

**Perfil**: estadístico. Revisa inferencia, no biología.

**Qué examinar**:
- `data/results/calibracion_kaltak.json` y `calibracion_kaltak_retina.json`
- `pipeline/calibration.py` (función `rank_summary`), `pipeline/ranking.py`
- Bloques **D** y **F** del dossier

**Preguntas que debe responder**:
1. **El p-valor de 5,96×10⁻⁵**: el proyecto declara que sobrestima porque los 5 AONs "conocidos" se
   solapan sobre un único sitio. ¿Cuál sería el análisis correcto? ¿Cuál es el n efectivo?
   **Calculalo.**
2. **El AUC de 0,974**: ¿es la métrica adecuada con 5 positivos y 27 negativos? ¿Qué intervalo de
   confianza tiene? ¿Es informativo un AUC con ese desbalance?
3. **El conjunto negativo** es "no nombrado como eficaz en el texto", no "medido ineficaz". ¿Cuánto
   sesga eso el resultado, y en qué dirección?
4. **El frente de Pareto**: con 3 dimensiones y 10 candidatos, ¿es una reducción significativa que
   queden 3, o es lo esperable por azar? **Simulalo**: ¿cuántos puntos quedarían no dominados con
   datos aleatorios de la misma dimensionalidad y tamaño?
5. **La convención 50/50** de colapsar dos percentiles térmicos en uno: el proyecto la declara y
   muestra que sin ella el frente pasa de 3 a 9. ¿Es una justificación válida o es elegir el
   parámetro que da el resultado más limpio?
6. **La concordancia 44/44**: ¿qué probabilidad de acuerdo habría por azar dado el desbalance de
   clases (10 vs 34)? ¿Es 100 % tan impresionante como suena?
7. `rank_summary` implementa Mann-Whitney a mano — **verificá que esté bien**, comparando contra
   `scipy.stats.mannwhitneyu` si está disponible.

---

### AGENTE 3 — Auditoría de reproducibilidad

**Perfil**: ingeniero de investigación reproducible. No opina de biología ni de estadística: **verifica que los números existan y se regeneren**.

**Qué examinar**: todo el repo y todo el vault, cruzados.

**Tareas concretas**:
1. **Correr la suite completa** y reportar el resultado real (esperado: 221 passed).
2. **Auditoría de números citados**: tomá cada número que aparece en el dossier y en los ADRs, y
   verificá que coincida con el archivo de `data/results/` que lo respalda. **Reportá toda
   discrepancia**, por chica que sea.
3. **Verificar que los comandos de regeneración del dossier funcionen** (al menos los que no
   requieren minutos de GPU/CPU).
4. `python3 scripts/lint_vault.py` — integridad de enlaces del vault.
5. **Buscar números huérfanos**: valores citados en el vault sin archivo que los respalde.
6. **Verificar la coherencia código↔documentación**: ¿los ADRs describen lo que el código hace hoy,
   o lo que hacía cuando se escribieron? Prestá especial atención a umbrales y constantes.
7. **`data/reference/` no está en git** (~500 MB). ¿Están documentadas las instrucciones para
   regenerarlo? ¿Alcanzan?
8. ¿Hay resultados en `data/results/` **sin script generador** en el repo?

---

### AGENTE 4 — ASO y viabilidad terapéutica

**Perfil**: especialista en oligonucleótidos antisentido y desarrollo preclínico. Revisa si el
producto propuesto tiene sentido como candidato a fármaco.

**Qué examinar**:
- `wiki/decisiones/0001-usar-quimica-pmo-splice-switching.md`
- `wiki/decisiones/0005-...` y `0006-severidad-off-target-en-vez-de-gate-binario.md`
- `wiki/riesgos/` (los tres archivos)
- `data/reference/kaltak2023/aon_sequences.csv`

**Preguntas que debe responder**:
1. **Química PMO**: se eligió por decisión de alcance del dueño del proyecto, no por evidencia. La
   literatura retinal real (QR-1011, Garanto, Tomkiewicz) usa 2'-MOE/fosforotioato. ¿Qué tan grave
   es esa divergencia? ¿Cambia las conclusiones o solo la traducibilidad?
2. **Termodinámica sin parámetros de PMO**: Tm y ΔG se calculan con un proxy de híbrido ARN/ADN
   porque no existen tablas nearest-neighbor estandarizadas para PMO. ¿Invalida el filtro
   termodinámico? ¿Qué error introduce?
3. **Longitud**: el pipeline usa 20 nt fijo. El oligo-walk de referencia (Kaltak) usa 16-25 nt y su
   ganador tiene 18. Los morfolinos comerciales suelen ser 25-mer. ¿Es un problema de diseño?
4. **Umbrales de off-target** (18/16/13 pb de tramo contiguo): son elección de diseño sin
   calibrar. ¿Son razonables para bloqueo estérico? ¿Qué usaría la industria?
5. **Lo que falta para evaluar riesgo real**: la severidad mide unión potencial, no daño. ¿Qué
   análisis adicionales harían falta (expresión tisular, relevancia funcional de la región
   golpeada)?
6. **Entrega y viabilidad**: ¿los 3 candidatos del frente son sintetizables y ensayables tal cual?
   ¿Algún problema práctico evidente (autoestructura, contenido GC, motivos inmunoestimuladores)?

---

### AGENTE 5 — Integridad del código y de los tests

**Perfil**: ingeniero de software senior con foco en calidad de tests. **Sospecha especialmente de
los tests que no pueden fallar.**

**Qué examinar**: `pipeline/`, `backend/`, `tests/` (14 archivos, 221 tests).

**Tareas concretas**:
1. **Tests circulares o tautológicos**: ¿algún test verifica que el código hace lo que hace, en vez
   de que hace lo correcto? Muchos tests comparan contra "valores de la corrida documentada" —
   ¿detectarían un error de lógica, o solo un cambio?
2. **Cobertura de casos borde**: ¿qué caminos de error no están cubiertos? ¿Qué pasa con entradas
   vacías, secuencias con `N`, ventanas fuera de rango?
3. **Los 4 "controles" del enmascarado** (`pipeline/run_masking.py`): ¿verifican realmente lo que
   dicen verificar? ¿Podrían pasar con un modelo roto?
4. **Umbrales cableados**: buscá constantes numéricas en el código y verificá que cada una esté
   justificada en un ADR. Reportá las que no.
5. **`pipeline/aso_masking.py`**: hay constantes legacy (`BLOCK_DELTA`, `COUNTERPRODUCTIVE_DELTA`)
   marcadas como "no usar con otro predictor" pero conservadas. ¿Se usan en algún lado? ¿Riesgo?
6. **El criterio relativo vs absoluto** (ADR 0010): verificá que el cambio se aplicó
   consistentemente en todo el código, backend y frontend incluidos.
7. Correr `scripts/run-in-env.sh python -m pytest tests/ -q -rs` y analizar **qué se saltea y por
   qué**.

---

### AGENTE 6 — Red team (abogado del diablo)

**Perfil**: revisor hostil de una revista de alto impacto. **Tu objetivo explícito es construir el
caso más fuerte posible para rechazar este trabajo.**

Este agente tiene permiso para ser agresivo — pero sigue atado a la regla de que **toda objeción
debe ser verificable**. Una objeción que no se sostiene debilita tu propio caso.

**Material de partida**: el dossier incluye una sección *"Preguntas que yo le haría a este proyecto
si quisiera rechazarlo"* con 7 preguntas. **Empezá por ahí, pero no te limites a eso** — fueron
escritas por el mismo agente que construyó el trabajo, así que representan los ataques que él
**pudo anticipar**. Los que no anticipó son los importantes.

**Encargo**:
1. Construí el **caso de rechazo** más fuerte que la evidencia permita.
2. Identificá la **afirmación más débil** del proyecto que todavía se presenta como sólida.
3. Buscá **circularidad**: ¿alguna conclusión se apoya en evidencia que fue definida por esa misma
   conclusión? (pista deliberada: mirá la relación entre las filas C2 y C4 del dossier).
4. Buscá **selección post-hoc**: criterios, umbrales o métricas elegidos después de ver los datos.
5. **Atacá el resultado principal**: ¿qué explicación alternativa hay para que 3 predictores
   coincidan en los mismos 10 candidatos, aparte de que el resultado sea correcto?
6. **Honestidad obligatoria**: al final, listá qué partes del trabajo **no pudiste atacar** con
   evidencia. Esa lista es tan valiosa como los ataques.

---

## 4. Tu trabajo como coordinador

1. **Desplegá los 6 agentes en paralelo.** No los corras en serie: querés opiniones independientes,
   no que se contaminen entre sí.
2. **Cuando terminen todos**, consolidá:
   - Deduplicá hallazgos (varios agentes pueden encontrar lo mismo desde ángulos distintos — eso es
     señal de que es real, anotalo).
   - Resolvé contradicciones entre agentes; si no se resuelven, reportá ambas posturas.
   - Ordená por severidad.
3. **Escribí el informe final** en el vault, como
   `wiki/estado/2026-08-XX-informe-revision-adversarial.md`, con esta estructura:

```markdown
# Informe de revisión adversarial

## Veredicto general
[¿Qué se sostiene y qué no, en 5 líneas?]

## Hallazgos CRÍTICOS
## Hallazgos MAYORES
## Hallazgos MENORES
## Confirmaciones (lo que resistió la revisión)

## Afirmaciones que deben debilitarse antes de publicar
[tabla: afirmación actual -> afirmación defendible]

## Lo que ningún agente pudo atacar
[esto es el núcleo sólido del trabajo]

## Recomendación editorial
[¿publicable? ¿como qué? ¿qué falta?]
```

4. **Actualizá `log.md` del vault** con una entrada de la revisión (el vault es append-only para el
   log; no edites entradas viejas).
5. **No corrijas nada todavía.** Esta sesión es de diagnóstico. Las correcciones se deciden después,
   viendo el informe completo.

---

## 5. Advertencias finales

- **No asumas que el trabajo está bien porque está bien documentado.** La documentación extensa
  puede ocultar problemas tanto como revelarlos.
- **No asumas que está mal porque lo hizo una IA.** Varios resultados tienen anclas externas
  verificables e independientes.
- **Si un agente no encuentra nada, sospechá del agente**, no concluyas que esa área está perfecta.
- **El sesgo más probable de este trabajo no está en los cálculos, está en el encuadre**: qué se
  eligió medir, qué métrica se definió, qué se presentó como resultado y qué como limitación.
