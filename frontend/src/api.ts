import type {
  AgreementResponse,
  AsoMaskingResponse,
  PredictorId,
  HeuristicFilterResponse,
  OffTargetResponse,
  OligoWalkResponse,
  RankingResponse,
  SequenceResponse,
  SpliceMotifsResponse,
  StructureResponse,
  ThermodynamicsResponse,
} from "./types";

const API_BASE = import.meta.env.VITE_API_BASE ?? "http://localhost:8000";

export async function fetchSequence(
  padding = 200,
  context = 30
): Promise<SequenceResponse> {
  const res = await fetch(
    `${API_BASE}/api/sequence?padding=${padding}&context=${context}`
  );
  if (!res.ok) {
    const body = await res.text();
    throw new Error(`API respondió ${res.status}: ${body}`);
  }
  return res.json();
}

export async function fetchOligoWalk(
  length = 20,
  step = 1,
  flank = 200
): Promise<OligoWalkResponse> {
  const res = await fetch(
    `${API_BASE}/api/oligo-walk?length=${length}&step=${step}&flank=${flank}`
  );
  if (!res.ok) {
    const body = await res.text();
    throw new Error(`API respondió ${res.status}: ${body}`);
  }
  return res.json();
}

export async function fetchSpliceMotifs(
  searchRadius = 10
): Promise<SpliceMotifsResponse> {
  const res = await fetch(
    `${API_BASE}/api/splice-motifs?search_radius=${searchRadius}`
  );
  if (!res.ok) {
    const body = await res.text();
    throw new Error(`API respondió ${res.status}: ${body}`);
  }
  return res.json();
}

export async function fetchHeuristicFilter(
  length = 20,
  step = 1,
  flank = 200
): Promise<HeuristicFilterResponse> {
  const res = await fetch(
    `${API_BASE}/api/heuristic-filter?length=${length}&step=${step}&flank=${flank}`
  );
  if (!res.ok) {
    const body = await res.text();
    throw new Error(`API respondió ${res.status}: ${body}`);
  }
  return res.json();
}

export async function fetchThermodynamics(
  length = 20,
  step = 1,
  flank = 200
): Promise<ThermodynamicsResponse> {
  const res = await fetch(
    `${API_BASE}/api/thermodynamics?length=${length}&step=${step}&flank=${flank}`
  );
  if (!res.ok) {
    const body = await res.text();
    throw new Error(`API respondió ${res.status}: ${body}`);
  }
  return res.json();
}

export async function fetchStructure(
  halfWindow = 150
): Promise<StructureResponse> {
  const res = await fetch(
    `${API_BASE}/api/structure?half_window=${halfWindow}`
  );
  if (!res.ok) {
    const body = await res.text();
    throw new Error(`API respondió ${res.status}: ${body}`);
  }
  return res.json();
}

export async function fetchOffTarget(
  length = 20,
  step = 1,
  flank = 200
): Promise<OffTargetResponse> {
  const res = await fetch(
    `${API_BASE}/api/off-target?length=${length}&step=${step}&flank=${flank}`
  );
  if (!res.ok) {
    const body = await res.text();
    throw new Error(`API respondió ${res.status}: ${body}`);
  }
  return res.json();
}

export async function fetchAsoMasking(
  predictor: PredictorId = "spliceai"
): Promise<AsoMaskingResponse> {
  const res = await fetch(`${API_BASE}/api/aso-masking?predictor=${predictor}`);
  if (!res.ok) {
    const body = await res.text();
    throw new Error(`API respondió ${res.status}: ${body}`);
  }
  return res.json();
}

export async function fetchPredictorAgreement(): Promise<AgreementResponse> {
  const res = await fetch(`${API_BASE}/api/aso-masking/agreement`);
  if (!res.ok) {
    const body = await res.text();
    throw new Error(`API respondió ${res.status}: ${body}`);
  }
  return res.json();
}

export async function fetchRanking(): Promise<RankingResponse> {
  const res = await fetch(`${API_BASE}/api/ranking`);
  if (!res.ok) {
    const body = await res.text();
    throw new Error(`API respondió ${res.status}: ${body}`);
  }
  return res.json();
}
