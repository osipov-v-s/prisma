import type { SessionAnalysis } from "./analytics";

export interface AvailableTest {
  id: string;
  name: string;
  width: number;
  depth: number;
  time_mode: "timeout_skip" | "timeout_mark" | "no_limit";
  time_limit_ms: number | null;
}

export interface Comparison {
  presentation_index: number;
  level_index: number;
  is_training: boolean;
  left_item_id: string;
  right_item_id: string;
  left_type_id: string;
  right_type_id: string;
  left_type_name: string;
  right_type_name: string;
  selected_type_name: string | null;
  left_image_url: string;
  right_image_url: string;
  selected_item_id: string | null;
  selected_type_id: string | null;
  reaction_time_ms: number | null;
  exceeded_time_limit: boolean;
  timed_out: boolean;
  status: string;
  shown_at: string | null;
  answered_at: string | null;
}

export interface TestSession {
  id: string;
  account_id: string;
  user_name: string;
  collection_id: string | null;
  collection_name: string;
  status: "training" | "ready" | "in_progress" | "completed";
  time_mode: AvailableTest["time_mode"];
  time_limit_ms: number | null;
  random_seed: string;
  started_at: string;
  finished_at: string | null;
  training_total: number;
  training_completed: number;
  main_total: number;
  main_completed: number;
  next_comparison: Comparison | null;
  comparisons: Comparison[] | null;
  analysis: SessionAnalysis | null;
}
