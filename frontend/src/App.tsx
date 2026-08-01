import { useEffect, useState } from "react";
import {
  fetchHeuristicFilter,
  fetchAsoMasking,
  fetchPredictorAgreement,
  fetchRanking,
  fetchOffTarget,
  fetchOligoWalk,
  fetchSequence,
  fetchSpliceMotifs,
  fetchStructure,
  fetchThermodynamics,
} from "./api";
import type {
  AgreementResponse,
  AsoMaskingResponse,
  PredictorId,
  RankingResponse,
  HeuristicFilterResponse,
  OffTargetResponse,
  OligoWalkResponse,
  SequenceResponse,
  SpliceMotifsResponse,
  StructureResponse,
  ThermodynamicsResponse,
} from "./types";
import { VariantCard } from "./components/VariantCard";
import { SequenceViewer } from "./components/SequenceViewer";
import { DnaHelix3D } from "./components/DnaHelix3D";
import { GeneStructureDiagram } from "./components/GeneStructureDiagram";
import { DonorMotifCard } from "./components/DonorMotifCard";
import { ProteinViewer } from "./components/ProteinViewer";
import { OligoWalkTrack } from "./components/OligoWalkTrack";
import { OligoWalkTable } from "./components/OligoWalkTable";
import { FilterSummary } from "./components/FilterSummary";
import { FilterTable } from "./components/FilterTable";
import { PipelineFunnel } from "./components/PipelineFunnel";
import { ThermoTable } from "./components/ThermoTable";
import { OffTargetTable } from "./components/OffTargetTable";
import { TensionCallout } from "./components/TensionCallout";
import { CausalChain } from "./components/CausalChain";
import { ManualAnalogy } from "./components/ManualAnalogy";
import { RnaFoldViewer } from "./components/RnaFoldViewer";
import { EvidenceLevels } from "./components/EvidenceLevels";
import { PipelineStepper } from "./components/PipelineStepper";
import { ModuleIntro } from "./components/ModuleIntro";
import { AsoMaskingControls } from "./components/AsoMaskingControls";
import { AsoMaskingFindings } from "./components/AsoMaskingFindings";
import { AsoMaskingScatter } from "./components/AsoMaskingScatter";
import { AsoMaskingTable } from "./components/AsoMaskingTable";
import { PredictorToggle } from "./components/PredictorToggle";
import { PredictorAgreement } from "./components/PredictorAgreement";
import { ParetoFront } from "./components/ParetoFront";
import { RankingTable } from "./components/RankingTable";
import { InfoTip } from "./components/InfoTip";
import { glossary } from "./glossary";
import "./App.css";

type Tab =
  | "sequence"
  | "mechanism"
  | "protein"
  | "oligowalk"
  | "filters"
  | "thermo"
  | "offtarget"
  | "asomasking"
  | "ranking"
  | "explain";

const MODULE_OF_TAB: Record<Tab, number> = {
  sequence: 1,
  mechanism: 1,
  protein: 1,
  oligowalk: 2,
  filters: 3,
  thermo: 4,
  offtarget: 5,
  asomasking: 6,
  ranking: 7,
  explain: 0,
};

function App() {
  const [data, setData] = useState<SequenceResponse | null>(null);
  const [oligoData, setOligoData] = useState<OligoWalkResponse | null>(null);
  const [filterData, setFilterData] = useState<HeuristicFilterResponse | null>(
    null
  );
  const [motifData, setMotifData] = useState<SpliceMotifsResponse | null>(null);
  const [thermoData, setThermoData] = useState<ThermodynamicsResponse | null>(
    null
  );
  const [thermoError, setThermoError] = useState<string | null>(null);
  const [offTargetData, setOffTargetData] = useState<OffTargetResponse | null>(
    null
  );
  const [offTargetError, setOffTargetError] = useState<string | null>(null);
  const [structureData, setStructureData] = useState<StructureResponse | null>(
    null
  );
  const [error, setError] = useState<string | null>(null);
  const [oligoError, setOligoError] = useState<string | null>(null);
  const [filterError, setFilterError] = useState<string | null>(null);
  const [tab, setTab] = useState<Tab>("sequence");

  const [maskData, setMaskData] = useState<AsoMaskingResponse | null>(null);
  const [maskError, setMaskError] = useState<string | null>(null);
  const [maskSelected, setMaskSelected] = useState<string | null>(null);
  const [predictor, setPredictor] = useState<PredictorId>("spliceai");
  const [maskLoading, setMaskLoading] = useState(false);
  const [agreement, setAgreement] = useState<AgreementResponse | null>(null);
  const [rankData, setRankData] = useState<RankingResponse | null>(null);
  const [rankError, setRankError] = useState<string | null>(null);
  const [rankSelected, setRankSelected] = useState<string | null>(null);

  useEffect(() => {
    fetchSequence()
      .then(setData)
      .catch((err) => setError(err.message));
    fetchOligoWalk()
      .then(setOligoData)
      .catch((err) => setOligoError(err.message));
    fetchHeuristicFilter()
      .then(setFilterData)
      .catch((err) => setFilterError(err.message));
    fetchSpliceMotifs().then(setMotifData).catch(() => setMotifData(null));
    fetchThermodynamics()
      .then(setThermoData)
      .catch((err) => setThermoError(err.message));
    fetchOffTarget()
      .then(setOffTargetData)
      .catch((err) => setOffTargetError(err.message));
    fetchPredictorAgreement()
      .then(setAgreement)
      .catch(() => setAgreement(null)); // sin los dos CSV no hay concordancia: no es un error de la pestaña
    fetchRanking()
      .then(setRankData)
      .catch((err) => setRankError(err.message));
    fetchStructure().then(setStructureData).catch(() => setStructureData(null));
  }, []);

  // El enmascarado se recarga al cambiar de predictor. Va en su propio efecto
  // para que alternar SpliceAI/Pangolin no vuelva a pedir los otros 8 endpoints.
  useEffect(() => {
    let vigente = true;
    setMaskLoading(true);
    setMaskError(null);
    fetchAsoMasking(predictor)
      .then((d) => {
        if (vigente) setMaskData(d);
      })
      .catch((err) => {
        if (vigente) setMaskError(err.message);
      })
      .finally(() => {
        if (vigente) setMaskLoading(false);
      });
    // Si el usuario cambia de predictor dos veces seguidas, la respuesta lenta
    // de la primera no debe pisar a la segunda.
    return () => {
      vigente = false;
    };
  }, [predictor]);

  return (
    <div className="app">
      <header className="app-header">
        <h1>bio-oligonucleotidos</h1>
        <p className="muted">
          Diseño in silico de un "parche molecular" (ASO) que corrija un error
          de lectura en el gen ABCA4, causante de la enfermedad de Stargardt
          tipo 1.
        </p>
      </header>

      <PipelineStepper current={MODULE_OF_TAB[tab]} />

      <nav className="tabs">
        <button
          className={tab === "explain" ? "tab active" : "tab"}
          onClick={() => setTab("explain")}
        >
          📖 Entender el proyecto
        </button>
        <button
          className={tab === "sequence" ? "tab active" : "tab"}
          onClick={() => setTab("sequence")}
        >
          Secuencia
        </button>
        <button
          className={tab === "mechanism" ? "tab active" : "tab"}
          onClick={() => setTab("mechanism")}
        >
          ¿Qué falla?
        </button>
        <button
          className={tab === "protein" ? "tab active" : "tab"}
          onClick={() => setTab("protein")}
        >
          Proteína (PDB 7M1Q)
        </button>
        <button
          className={tab === "oligowalk" ? "tab active" : "tab"}
          onClick={() => setTab("oligowalk")}
        >
          Oligo-Walk
        </button>
        <button
          className={tab === "filters" ? "tab active" : "tab"}
          onClick={() => setTab("filters")}
        >
          Filtros
        </button>
        <button
          className={tab === "thermo" ? "tab active" : "tab"}
          onClick={() => setTab("thermo")}
        >
          Termodinámica
        </button>
        <button
          className={tab === "offtarget" ? "tab active" : "tab"}
          onClick={() => setTab("offtarget")}
        >
          Off-target
        </button>
        <button
          className={tab === "asomasking" ? "tab active" : "tab"}
          onClick={() => setTab("asomasking")}
        >
          Bloqueo del ASO
        </button>
        <button
          className={tab === "ranking" ? "tab active" : "tab"}
          onClick={() => setTab("ranking")}
        >
          Ranking final
        </button>
      </nav>

      <main className="app-main">
        {tab === "sequence" && (
          <>
            <ModuleIntro
              title="Módulo 1 — Secuencia objetivo"
              goal="Objetivo: conseguir el fragmento exacto de ADN/ARN que vamos a usar como materia prima para diseñar el parche molecular."
              detail="Acá no se diseña nada todavía — solo se obtiene, de una base de datos pública (Ensembl), el pedazo de gen ABCA4 donde está la mutación, y se construyen dos versiones para comparar: cómo se ve normalmente (wild-type) y cómo queda con el error genético (mutante). Los módulos que siguen van a trabajar sobre esta secuencia."
            />
            {error && (
              <div className="card error">
                <h2>No se pudo cargar</h2>
                <p>{error}</p>
                <p className="muted">
                  ¿Está corriendo el backend?{" "}
                  <code>uvicorn backend.main:app --port 8000</code>
                </p>
              </div>
            )}
            {!data && !error && <p className="muted">Cargando secuencia…</p>}
            {data && (
              <>
                <VariantCard variant={data.variant} region={data.region} />
                <SequenceViewer comparison={data.comparison} />
                <DnaHelix3D
                  sequence={data.comparison.wildtype}
                  variantIndex={data.comparison.variant_offset_in_context}
                  mutantBase={
                    data.comparison.mutant[
                      data.comparison.variant_offset_in_context
                    ]
                  }
                />
              </>
            )}
          </>
        )}

        {tab === "mechanism" && (
          <>
            <ModuleIntro
              title="¿Qué falla exactamente?"
              goal="Objetivo: entender qué le hace la mutación al proceso de splicing — el porqué detrás de la secuencia del Módulo 1."
              detail="La secuencia por sí sola no dice mucho si no sabés qué hace la célula con ella. Este esquema muestra qué pasa normalmente (el intrón se recorta) y qué pasa con la mutación (un pedazo del intrón queda pegado por error — un 'pseudoexón')."
            />
            <GeneStructureDiagram />
            {motifData && <DonorMotifCard data={motifData} />}
          </>
        )}

        {tab === "protein" && (
          <>
            <ModuleIntro
              title="Contexto — ¿Por qué importa esta mutación?"
              goal="Esto no es un módulo del pipeline: es para entender qué se rompe si el error genético no se corrige."
              detail="La secuencia del Módulo 1 eventualmente se traduce en una proteína. Acá ves cómo es esa proteína (ABCA4) en la vida real, medida en laboratorio — para conectar 'un cambio de una letra en el ADN' con 'una proteína que deja de funcionar y daña la vista'."
            />
            <ProteinViewer />
          </>
        )}

        {tab === "oligowalk" && (
          <>
            <ModuleIntro
              title="Módulo 2 — Oligo-Walk"
              goal="Objetivo: generar TODOS los parches candidatos posibles, uno por cada posición — sin descartar ninguno todavía."
              detail="Esto es fuerza bruta a propósito: en vez de adivinar un diseño, se recorre la región alrededor de la mutación con una ventana de 20 letras que se desplaza de a una posición, generando un candidato por cada desplazamiento. Ninguno se filtra acá — eso es tarea del Módulo 3 (pestaña 'Filtros')."
            />
            {oligoError && (
              <div className="card error">
                <h2>No se pudo cargar</h2>
                <p>{oligoError}</p>
              </div>
            )}
            {!oligoData && !oligoError && (
              <p className="muted">Generando candidatos…</p>
            )}
            {oligoData && (
              <>
                <div className="card">
                  <h2>
                    <InfoTip text={glossary.oligoWalk}>
                      Resultado del Oligo-Walk
                    </InfoTip>
                  </h2>
                  <dl className="fact-grid">
                    <dt>Candidatos generados</dt>
                    <dd>{oligoData.count}</dd>
                    <dt>Longitud de cada oligo</dt>
                    <dd>{oligoData.params.length} nt</dd>
                    <dt>Paso entre ventanas</dt>
                    <dd>{oligoData.params.step} nt</dd>
                    <dt>Región escaneada</dt>
                    <dd>
                      ±{oligoData.params.flank} nt alrededor de la variante (
                      {oligoData.scan_end - oligoData.scan_start} nt en total)
                    </dd>
                    <dt>
                      <InfoTip text={glossary.intronBounds}>Límite real del intrón</InfoTip>
                    </dt>
                    <dd>
                      {oligoData.clamped_to_intron
                        ? "⚠️ la búsqueda pedida se recortó para no invadir el exón vecino"
                        : "✅ la búsqueda quedó cómodamente dentro del intrón"}
                    </dd>
                  </dl>
                </div>
                <OligoWalkTrack
                  candidates={oligoData.candidates}
                  scanStart={oligoData.scan_start}
                  scanEnd={oligoData.scan_end}
                  variantOffset={oligoData.variant_offset}
                />
                <OligoWalkTable candidates={oligoData.candidates} />
              </>
            )}
          </>
        )}

        {tab === "filters" && (
          <>
            <ModuleIntro
              title="Módulo 3 — Filtro heurístico"
              goal="Objetivo: descartar rápido a los candidatos con un problema obvio, antes de gastar cómputo en análisis más caros."
              detail="Dos reglas simples y rápidas de calcular: el porcentaje de GC tiene que estar en un rango razonable (ni muy bajo ni muy alto), y no puede haber una racha de 4+ letras G seguidas (riesgo de que el parche se doble sobre sí mismo). Sobrevivir este filtro no significa 'buen candidato' todavía — solo 'sin un defecto obvio'."
            />
            {filterError && (
              <div className="card error">
                <h2>No se pudo cargar</h2>
                <p>{filterError}</p>
              </div>
            )}
            {!filterData && !filterError && (
              <p className="muted">Aplicando filtro…</p>
            )}
            {filterData && (
              <>
                <FilterSummary
                  total={filterData.total_count}
                  passed={filterData.passed_count}
                  rejected={filterData.rejected_count}
                />
                <FilterTable candidates={filterData.candidates} />
              </>
            )}
          </>
        )}
        {tab === "explain" && (
          <>
            <ModuleIntro
              title="Entender el proyecto de punta a punta"
              goal="Objetivo: que cualquier persona, sin formación en biología, entienda qué se busca, qué se encontró, y por qué queda una decisión que los datos no resuelven solos."
              detail="Todo lo que ves acá está calculado con datos reales del proyecto, no son ilustraciones genéricas. Si algo no se entiende, tocá los íconos ⓘ."
            />
            <CausalChain />
            <ManualAnalogy />
            {thermoData && (
              <PipelineFunnel
                generated={thermoData.funnel.generated}
                passedHeuristic={thermoData.funnel.passed_heuristic}
                passedThermo={thermoData.funnel.passed_thermo}
              />
            )}
            {structureData && <RnaFoldViewer data={structureData} />}
            {thermoData && (
              <TensionCallout
                candidates={thermoData.candidates}
                donorRange={[5001, 5008]}
              />
            )}
            <div className="card">
              <h2>Por qué la decisión final es "por criterio"</h2>
              <p>
                Para poner los candidatos en un ranking hace falta{" "}
                <strong>un solo número por candidato</strong>. Y para eso hay
                que decidir cuánto vale "ser alcanzable" comparado con "estar en
                el lugar correcto". <strong>No existe una tasa de cambio
                objetiva entre esas dos cosas.</strong>
              </p>
              <p className="muted">
                Es como comprar un departamento: podés medir el precio, los
                metros y los minutos de viaje con total precisión — pero ningún
                dato te dice si 10 m² más valen 15 minutos más de viaje. Eso es
                una preferencia, no un cálculo.
              </p>
              <p>Y acá los datos tampoco pueden desempatar, por tres razones:</p>
              <ol className="reason-list">
                <li>
                  <strong>La accesibilidad es un modelo, no una medición.</strong>{" "}
                  Estimamos el plegado con un programa; en una célula real hay
                  proteínas pegadas y todo se mueve.
                </li>
                <li>
                  <strong>No sabemos si "cerca" alcanza.</strong> A veces tapar
                  una zona vecina también funciona. Para esta mutación, nadie lo
                  publicó.
                </li>
                <li>
                  <strong>No hay respuesta conocida contra la cual comparar.</strong>{" "}
                  No existe ningún parche publicado para esta variante, así que
                  no podemos verificar si el pipeline "acierta".
                </li>
              </ol>
              <p className="caveat">
                💰 <strong>Por qué importa:</strong> el paso siguiente cuesta
                dinero y tiempo real — hay que sintetizar los parches y probarlos
                en células. No se pueden probar los 44: se prueban 3 o 5.
                Elegir cuáles es la decisión, y determina qué se testea de verdad.
              </p>
            </div>
            <EvidenceLevels />
            <div className="card">
              <h2>Lo que este proyecto NO es</h2>
              <ul className="notlist">
                <li>❌ No estamos fabricando ningún medicamento.</li>
                <li>❌ No estamos probando nada en células ni en personas.</li>
                <li>
                  ❌ No es una terapia — es una <strong>propuesta de candidatos</strong>{" "}
                  para que alguien la pruebe.
                </li>
                <li>
                  ✅ Sí es una herramienta que reduce trabajo manual de meses a
                  segundos, y deja documentado y trazable por qué cada candidato
                  sobrevivió o se descartó.
                </li>
              </ul>
            </div>
          </>
        )}

        {tab === "thermo" && (
          <>
            <ModuleIntro
              title="Módulo 4 — Termodinámica y accesibilidad"
              goal="Objetivo: de los que pasaron el filtro rápido, quedarse con los que además se pegan bien, no se enredan solos, y apuntan a una zona del ARN que esté realmente alcanzable."
              detail="Acá entran los cálculos caros: qué tan fuerte se pega el parche (Tm y energía), si se dobla sobre sí mismo o se pega a otra copia suya (lo que lo inutilizaría), y si la zona que queremos tapar está expuesta o escondida dentro de un pliegue del ARN. Se calcula con ViennaRNA sobre el ARN real."
            />
            {thermoError && (
              <div className="card error">
                <h2>No se pudo cargar</h2>
                <p>{thermoError}</p>
              </div>
            )}
            {!thermoData && !thermoError && (
              <p className="muted">Calculando termodinámica…</p>
            )}
            {thermoData && (
              <>
                <PipelineFunnel
                  generated={thermoData.funnel.generated}
                  passedHeuristic={thermoData.funnel.passed_heuristic}
                  passedThermo={thermoData.funnel.passed_thermo}
                />
                <TensionCallout
                  candidates={thermoData.candidates}
                  donorRange={[
                    thermoData.candidates.length > 0 ? 5001 : 0,
                    5008,
                  ]}
                />
                <ThermoTable
                  candidates={thermoData.candidates}
                  donorRange={[5001, 5008]}
                />
                <p className="caveat">
                  ⚠️ <strong>Limitación del método:</strong>{" "}
                  {thermoData.method_caveat}
                </p>
              </>
            )}
          </>
        )}

        {tab === "offtarget" && (
          <>
            <ModuleIntro
              title="Módulo 5 — Off-target contra el transcriptoma humano"
              goal="Objetivo: de los que pasaron termodinámica, detectar cuáles podrían pegarse por error a un ARN de OTRO gen -- un efecto secundario no buscado."
              detail="Se usa BLAST (el buscador estándar de similitud de secuencias en bioinformática) para comparar cada candidato contra los ~411 mil transcritos humanos conocidos (Ensembl, cDNA + ncRNA). Si aparece una coincidencia larga y con pocas diferencias en un gen que no sea ABCA4, el candidato queda marcado para revisión."
            />
            {offTargetError && (
              <div className="card error">
                <h2>No se pudo cargar</h2>
                <p>{offTargetError}</p>
              </div>
            )}
            {!offTargetData && !offTargetError && (
              <p className="muted">Corriendo BLAST contra el transcriptoma humano… (puede tardar unos segundos)</p>
            )}
            {offTargetData && (
              <>
                <PipelineFunnel
                  generated={offTargetData.funnel.generated}
                  passedHeuristic={offTargetData.funnel.passed_heuristic}
                  passedThermo={offTargetData.funnel.passed_thermo}
                  annotatedOffTarget={offTargetData.funnel.annotated_off_target}
                />
                <div className="card">
                  <h2>Regla de corte usada</h2>
                  <p className="muted">
                    Un hit en OTRO gen cuenta como off-target si tiene al menos{" "}
                    <strong>{offTargetData.rule.min_alignment_length} pb</strong> de
                    homología contigua con{" "}
                    <strong>{offTargetData.rule.max_mismatches} mismatches o menos</strong>.
                  </p>
                  <p className="muted">
                    Todas las isoformas del gen blanco (
                    <strong>{offTargetData.rule.target_gene_symbol}</strong>) se excluyen
                    del conteo -- pegarse ahí es el objetivo, no un efecto secundario.
                  </p>
                </div>
                <OffTargetTable candidates={offTargetData.candidates} />
                <p className="caveat">
                  ⚠️ <strong>Limitación del método:</strong>{" "}
                  {offTargetData.method_caveat}
                </p>
              </>
            )}
          </>
        )}
        {tab === "asomasking" && (
          <>
            <ModuleIntro
              title="Módulo 6b — ¿Cada parche apaga el sitio falso?"
              goal="Objetivo: por primera vez, preguntar si el parche SIRVE, no solo si es un buen oligo. Los módulos 2 a 5 miden propiedades del parche; este mide su efecto."
              detail="Un PMO no corta el ARN ni lo modifica: se pega encima y lo tapa. Para simular eso, reemplazamos la ventana del parche por la letra N, que el predictor lee como 'acá no hay información legible', y le volvemos a preguntar dónde ve sitios de splicing. Es la analogía de poner cinta opaca sobre un renglón y preguntarle al lector qué entiende ahora."
            />
            {maskError && (
              <div className="card error">
                <h2>No se pudo cargar</h2>
                <p>{maskError}</p>
              </div>
            )}
            {!maskData && !maskError && (
              <p className="muted">Cargando la simulación de bloqueo…</p>
            )}
            {maskData && (
              <>
                <PredictorToggle
                  predictor={maskData.predictor}
                  value={predictor}
                  onChange={setPredictor}
                  loading={maskLoading}
                />
                {agreement && <PredictorAgreement data={agreement} />}
                <AsoMaskingControls data={maskData} />
                <AsoMaskingFindings data={maskData} />
                <AsoMaskingScatter
                  data={maskData}
                  selected={maskSelected}
                  onSelect={setMaskSelected}
                />
                <AsoMaskingTable
                  data={maskData}
                  selected={maskSelected}
                  onSelect={setMaskSelected}
                />
                <p className="caveat">
                  ⚠️ <strong>Limitación del método:</strong> {maskData.limitation}
                </p>

              </>
            )}
          </>
        )}

        {tab === "ranking" && (
          <>
            <ModuleIntro
              title="Módulo 7 — ¿Cuáles convendría sintetizar primero?"
              goal="Objetivo: ordenar los candidatos que SÍ anulan el pseudoexón, combinando lo que midieron los módulos anteriores: cuánto bloquean, qué tan poco se parecen a otros genes, y qué tan buen oligo son."
              detail="No se promedian los tres criterios en un puntaje único, porque están en unidades distintas y no hay ningún dato que diga cuánto vale uno en términos de otro. En vez de eso se usa un frente de Pareto: se marcan los candidatos que ningún otro supera en las tres cosas a la vez. Es como elegir un celular por precio, cámara y batería: podés descartar los que son peores en todo, pero entre los que ganan en algo distinto, la elección ya es tuya."
            />
            {rankError && (
              <div className="card error">
                <h2>No se pudo cargar</h2>
                <p>{rankError}</p>
              </div>
            )}
            {!rankData && !rankError && (
              <p className="muted">Calculando el ranking…</p>
            )}
            {rankData && (
              <>
                <div className="card">
                  <h2>Por qué no hay un puntaje único</h2>
                  <p>{rankData.why_not_weights}</p>
                  <p className="muted">
                    De los {rankData.n_eligible + rankData.n_rejected} candidatos
                    que llegaron al Módulo 6b, <strong>{rankData.n_rejected}</strong>{" "}
                    no anulan el pseudoexón y por eso no compiten.{" "}
                    <strong>{rankData.n_eligible}</strong> sí, y de esos{" "}
                    <strong>{rankData.front.length}</strong> quedan en el frente.
                  </p>
                </div>

                <ParetoFront
                  data={rankData}
                  selected={rankSelected}
                  onSelect={setRankSelected}
                />
                <RankingTable
                  data={rankData}
                  selected={rankSelected}
                  onSelect={setRankSelected}
                />

                <div className="card">
                  <h2>Análisis de sensibilidad</h2>
                  <p>
                    Colapsar accesibilidad y homodímero en un solo número es una
                    convención (un promedio 50/50), no un resultado. Está medido
                    cuánto pesa esa decisión: con las dos separadas, el frente
                    pasa de <strong>{rankData.sensitivity.n_front_3d}</strong> a{" "}
                    <strong>{rankData.sensitivity.n_front_4d}</strong> de{" "}
                    {rankData.sensitivity.n_eligible} candidatos — o sea, deja de
                    descartar y por lo tanto deja de informar.
                  </p>
                  <p className="muted">{rankData.sensitivity.note}</p>
                </div>

                <p className="caveat">
                  ⚠️ <strong>Limitación:</strong> {rankData.limitation}
                </p>
              </>
            )}
          </>
        )}
      </main>

      <footer className="app-footer muted">
        Módulos 1–7 · pipeline completo. Ningún resultado está validado
        experimentalmente.
      </footer>
    </div>
  );
}

export default App;
