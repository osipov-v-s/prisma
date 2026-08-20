export interface RankedScore {
  type_id: string | number;
  type_name: string;
  score: number;
  percent: number;
}

export interface ConsistencyResult {
  cyclic_triads: number | null;
  maximum_cyclic_triads: number | null;
  zeta: number | null;
  classification: string;
  interpretation: string | null;
}

export interface ModeAnalysis {
  status: string;
  message: string | null;
  overall: RankedScore[] | null;
  coverage: number;
  consistency: ConsistencyResult | null;
  iteration_strategy: string;
  binary_matrix: Array<Array<number | null>> | null;
  pair_time_matrix_ms: Array<Array<number | null>> | null;
  time_weighted_matrix: Array<Array<number | null>> | null;
  validation_total_time_ms: number | null;
}

export interface SessionAnalysis {
  algorithm_version: string;
  choice_only: ModeAnalysis;
  choice_and_time: ModeAnalysis;
  source_responses: unknown[];
}
