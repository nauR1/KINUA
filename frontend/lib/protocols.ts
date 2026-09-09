export type ROMDefinition = {
  movement: string;
  name: string;
  joint: string;
  plane: string;
  points: string[];
  formula: string;
  direction: number;
  version: string;
  instructions: string;
  limitations: string[];
};
export type ROMRecord = {
  id: string;
  analysis_id: string;
  movement: string;
  side: string;
  minimum: number;
  maximum: number;
  excursion: number;
  peak_value: number;
  peak_frame_index: number;
  peak_timestamp_ms: number;
  confidence: number;
  details: {
    valid_samples: number;
    total_samples: number;
    peak_index: number;
    movement_start_index: number | null;
  };
  assessment_id?: string;
  created_at?: string;
  view?: string;
  provider_version?: string;
  engine_version?: string;
  fps?: number;
  review_state?: string;
};
export type StepDefinition = {
  key: string;
  name: string;
  kind: string;
  optional: boolean;
  available: boolean;
  instructions: string;
  movements?: string[];
  capture_protocol?: string;
};
export type ProtocolDefinition = {
  id: string;
  name: string;
  version: string;
  category_id: string;
  steps: StepDefinition[];
};
export type ProtocolStep = {
  id: string;
  step_key: string;
  state: string;
  revision: number;
  result: string;
  note: string;
  started_at: string | null;
  completed_at: string | null;
  skipped_at: string | null;
  child_assessment_id: string | null;
  child: { status: string; id: string } | null;
  definition: StepDefinition;
};
export type ProtocolRun = {
  id: string;
  assessment_id: string;
  snapshot: ProtocolDefinition;
  version_id: string;
  steps: ProtocolStep[];
};
export type ProtocolCatalog = {
  categories: { id: string; name: string }[];
  versions: {
    id: string;
    definition: ProtocolDefinition;
    version: string;
    protocol: { name: string; category_id: string };
  }[];
};
export const stepLabels: Record<string, string> = {
  not_started: "Não iniciada",
  in_progress: "Em andamento",
  completed: "Concluída",
  skipped: "Ignorada com justificativa",
};
export const sideLabels: Record<string, string> = {
  right: "Direito",
  left: "Esquerdo",
  bilateral: "Bilateral",
};
