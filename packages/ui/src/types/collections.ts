export type TimeMode = "timeout_skip" | "timeout_mark" | "no_limit";

export interface CollectionCell {
  item_id: string | null;
  level_index: number;
  image_path: string | null;
  image_url: string | null;
}

export interface CollectionRow {
  row_index: number;
  type_id: string | null;
  type_name: string;
  cells: CollectionCell[];
}

export interface CollectionRecord {
  id: string;
  name: string;
  width: number;
  depth: number;
  is_active: boolean;
  time_mode: TimeMode;
  time_limit_ms: number | null;
  created_at: string;
  updated_at: string;
  rows: CollectionRow[];
  activation: {
    can_activate: boolean;
    errors: string[];
  };
}

export interface CollectionWrite {
  name: string;
  width: number;
  depth: number;
  time_mode: TimeMode;
  time_limit_ms: number | null;
  rows: Array<{ row_index: number; type_name: string }>;
}
