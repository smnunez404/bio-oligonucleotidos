export interface VariantInfo {
  gene: string;
  transcript: string;
  hgvs_c: string;
  hgvs_g_grch38: string;
  chromosome: string;
  position_grch38: number;
  intron: number;
  source: string;
}

export interface RegionInfo {
  start_grch38: number;
  end_grch38: number;
  length: number;
}

export interface ComparisonInfo {
  context_nt: number;
  variant_offset_in_context: number;
  wildtype: string;
  mutant: string;
}

export interface SequenceResponse {
  variant: VariantInfo;
  region: RegionInfo;
  comparison: ComparisonInfo;
}

export interface OligoCandidate {
  start: number;
  end: number;
  target_window: string;
  aso_sequence: string;
  covers_variant: boolean;
  distance_to_variant: number;
}

export interface OligoWalkResponse {
  params: { length: number; step: number; flank: number };
  variant_offset: number;
  scan_start: number;
  scan_end: number;
  intron2_bounds: { start: number; end: number };
  clamped_to_intron: boolean;
  count: number;
  candidates: OligoCandidate[];
}

export interface FilteredCandidate {
  start: number;
  end: number;
  aso_sequence: string;
  covers_variant: boolean;
  distance_to_variant: number;
  gc_fraction: number;
  has_g_run: boolean;
  passed: boolean;
  reasons: string[];
}

export interface DonorCandidate {
  offset_from_variant: number;
  wildtype_motif: string;
  wildtype_score: number;
  mutant_motif: string;
  mutant_score: number;
  wildtype_matches: boolean[];
  mutant_matches: boolean[];
  delta: number;
}

export interface SpliceMotifsResponse {
  search_radius: number;
  exonic_len: number;
  consensus: string;
  method: string;
  candidate_count: number;
  strengthened_count: number;
  candidates: DonorCandidate[];
}

export interface ThermoCandidate {
  start: number;
  end: number;
  aso_sequence: string;
  covers_variant: boolean;
  distance_to_variant: number;
  tm: number;
  dg_hybridization: number;
  dg_self_structure: number;
  dg_homodimer: number;
  accessibility: number | null;
  accessibility_percentile: number | null;
  homodimer_percentile: number | null;
  passed: boolean;
  reasons: string[];
}

export interface ThermodynamicsResponse {
  params: { length: number; step: number; flank: number };
  thresholds: {
    tm_min: number;
    tm_max: number;
    hairpin_dg_limit: number;
    homodimer_dg_limit: number;
  };
  method_caveat: string;
  funnel: {
    generated: number;
    passed_heuristic: number;
    passed_thermo: number;
  };
  analyzed_count: number;
  passed_count: number;
  rejected_count: number;
  candidates: ThermoCandidate[];
}

export interface HeuristicFilterResponse {
  params: {
    length: number;
    step: number;
    flank: number;
    gc_min: number;
    gc_max: number;
  };
  variant_offset: number;
  scan_start: number;
  scan_end: number;
  intron2_bounds: { start: number; end: number };
  clamped_to_intron: boolean;
  total_count: number;
  passed_count: number;
  rejected_count: number;
  candidates: FilteredCandidate[];
}

export interface StructurePoint {
  i: number;
  b: string;
  x: number;
  y: number;
  p: boolean;
  u: number | null;
}

export interface StructureCandidate {
  start: number;
  end: number;
  accessibility_percentile: number | null;
  distance_to_variant: number;
  tm: number;
}

export interface OffTargetHit {
  transcript_id: string;
  gene_id: string | null;
  gene_symbol: string | null;
  pident: number;
  length: number;
  mismatches: number;
  /** Tramo de bases apareadas consecutivas más largo (base de la severidad). */
  longest_perfect_run: number;
  is_target_gene: boolean;
  meets_off_target_rule: boolean;
}

export interface OffTargetWorstHit {
  transcript_id: string;
  gene_id: string | null;
  gene_symbol: string | null;
  pident: number;
  length: number;
  mismatches: number;
  evalue: number;
  bitscore: number;
}

export type OffTargetSeverity = "alto" | "moderado" | "leve" | "sin_señal";

export interface OffTargetCandidate {
  start: number;
  end: number;
  aso_sequence: string;
  covers_variant: boolean;
  distance_to_variant: number;
  severity: OffTargetSeverity;
  severity_label: string;
  /** Mayor tramo contiguo perfecto entre todos los hits: define la severidad. */
  longest_perfect_run: number;
  off_target_count: number;
  distinct_genes_hit: number;
  worst_hit: OffTargetWorstHit | null;
  hits: OffTargetHit[];
  reasons: string[];
}

export interface OffTargetResponse {
  params: { length: number; step: number; flank: number };
  rule: {
    min_alignment_length: number;
    max_mismatches: number;
    target_gene_symbol: string;
    severity_levels: OffTargetSeverity[];
    severity_labels: Record<OffTargetSeverity, string>;
  };
  method_caveat: string;
  funnel: {
    generated: number;
    passed_heuristic: number;
    passed_thermo: number;
    annotated_off_target: number;
  };
  analyzed_count: number;
  severity_counts: Record<OffTargetSeverity, number>;
  candidates: OffTargetCandidate[];
}

export interface StructureResponse {
  window: { start: number; end: number };
  variant_index: number;
  structure: string;
  mfe: number;
  paired_fraction: number;
  donor_range: {
    start: number;
    end: number;
    wildtype_score: number;
    mutant_score: number;
  } | null;
  most_accessible: StructureCandidate | null;
  donor_covering: StructureCandidate[];
  approved_total: number;
  points: StructurePoint[];
}

export type AsoMaskingClass = "bloquea" | "sin_efecto" | "contraproducente";

export interface AsoMaskingCandidate {
  name: string;
  start_rel: number;
  end_rel: number;
  covers_donor: boolean;
  donor_cryptic: number;
  delta_donor: number;
  acceptor_cryptic: number;
  delta_acceptor: number;
  donor_canonical_e3: number;
  delta_canonical: number;
  classification: AsoMaskingClass;
  // Retenciones (fracción del baseline). Son el criterio vivo desde el ADR 0010:
  // los deltas absolutos no son comparables entre predictores.
  retention_donor: number;
  retention_acceptor: number;
  retention_canonical: number;
  verdict: AsoMaskingVerdict;
  borders_abolished: string[];
}

// Veredicto a nivel de pseudoexón (ADR 0012). Distinto de `classification`, que
// mira un solo sitio.
export type AsoMaskingVerdict =
  | "anula_pseudoexon"
  | "sin_efecto"
  | "daña_canonico";

export interface AsoMaskingPredictor {
  id: string;
  label: string;
  note: string;
  available: string[];
}

export interface AsoMaskingThresholds {
  block_retention: number;
  counterproductive_gain: number;
  note: string;
}

export interface AsoMaskingControl {
  name: string;
  label: string;
  donor_cryptic: number;
  delta_donor: number;
  expected: string;
  ok: boolean;
}

export interface AsoMaskingResponse {
  method: string;
  limitation: string;
  predictor: AsoMaskingPredictor;
  baseline: {
    donor_cryptic: number;
    acceptor_cryptic: number;
    donor_canonical_e3: number;
  };
  controls: AsoMaskingControl[];
  thresholds: AsoMaskingThresholds;
  sites: {
    donor_cryptic_offset: number;
    acceptor_cryptic_offset: number;
    pseudoexon_size: number;
    pseudoexon_note: string;
  };
  total: number;
  counts: Record<AsoMaskingClass, number>;
  candidates_covering_acceptor: number;
  acceptor_gap_note: string;
  counts_note: string;
  verdict: {
    counts: Record<AsoMaskingVerdict, number>;
    useful: AsoMaskingCandidate[];
    criterion: string;
    why_it_matters: string;
  };
  candidates: AsoMaskingCandidate[];
}

// --- Módulo 7: ranking multicriterio (frente de Pareto) ---

export type RankingDimensionId =
  | "block_strength"
  | "offtarget_safety"
  | "thermo_quality";

export interface RankingDimension {
  id: RankingDimensionId;
  label: string;
  description: string;
  source: string;
}

export interface RankedCandidate {
  name: string;
  in_front: boolean;
  dominated_by: string[];
  objectives: Record<RankingDimensionId, number>;
  start_rel: number;
  end_rel: number;
  borders_abolished: string[];
  severity: string;
  raw: {
    longest_perfect_run: number;
    accessibility_percentile: number;
    homodimer_percentile: number;
    retention_by_predictor: Record<string, Record<string, number>>;
  };
}

export interface RankingResponse {
  method: string;
  why_not_weights: string;
  gate: string;
  dimensions: RankingDimension[];
  front: string[];
  n_eligible: number;
  n_rejected: number;
  sensitivity: {
    n_eligible: number;
    n_front_3d: number;
    n_front_4d: number;
    front_4d: string[];
    note: string;
  };
  candidates: RankedCandidate[];
  limitation: string;
  provenance_caveat: string;
}

// --- Módulo 6c aplicado al 6b: concordancia entre predictores ---

export type PredictorId = "spliceai" | "pangolin";

export interface AgreementSide {
  donor_cryptic: number;
  retention_donor: number;
  retention_acceptor: number;
  classification: AsoMaskingClass;
  verdict: AsoMaskingVerdict;
  borders_abolished: string[];
}

export interface AgreementCandidate {
  name: string;
  start_rel: number;
  covers_donor: boolean;
  spliceai: AgreementSide;
  pangolin: AgreementSide;
  /** Coinciden en el veredicto a nivel pseudoexón (el criterio del ADR 0012). */
  agree: boolean;
  /** Coinciden mirando solo el donador críptico (el criterio antiguo). */
  agree_by_site: boolean;
}

export interface AgreementResponse {
  n_compared: number;
  n_agree: number;
  agreement_fraction: number;
  n_agree_by_site: number;
  agreement_fraction_by_site: number;
  disagreements: AgreementCandidate[];
  disagreements_by_site: AgreementCandidate[];
  baseline: Record<PredictorId, Record<string, number>>;
  note: string;
  limitation: string;
  per_candidate: AgreementCandidate[];
}
