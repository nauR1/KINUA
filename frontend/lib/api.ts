export async function api<T = unknown>(
  path: string,
  options: RequestInit = {},
): Promise<T> {
  const response = await fetch("/api" + path, {
    ...options,
    credentials: "include",
    headers: {
      "X-Requested-With": "Biometria",
      ...(options.body instanceof FormData
        ? {}
        : { "Content-Type": "application/json" }),
      ...options.headers,
    },
  });
  if (!response.ok) {
    const body = await response
      .json()
      .catch(() => ({ detail: "Não foi possível conectar ao servidor." }));
    const message = Array.isArray(body.detail)
      ? body.detail.map((x: { msg: string }) => x.msg).join("; ")
      : body.detail;
    throw new Error(message || "Falha na solicitação.");
  }
  return response.json();
}
export const post = <T>(path: string, body: unknown) =>
  api<T>(path, { method: "POST", body: JSON.stringify(body) });
export type Patient = {
  id: string;
  name: string;
  birth_date: string;
  details: Record<string, string | number | null>;
};
export type Assessment = {
  id: string;
  patient_id: string;
  kind: string;
  mode: string;
  protocol: string;
  side: string;
  jobs?: ProcessingJob[];
  status: string;
  notes: string;
  conclusion: string;
  created_at: string;
  analyses: Analysis[];
};
export type Measurement = {
  id: string;
  key: string;
  label: string;
  value: number | null;
  unit: string;
  confidence: number;
  details: {
    region: string;
    side: string;
    reason?: string;
    status: string;
    min?: number;
    max?: number;
    amplitude?: number;
    max_index?: number;
    statistic?: string;
    valid_samples?: number;
    total_samples?: number;
  };
};
export type Finding = {
  id: string;
  description: string;
  state: string;
  region: string;
  confidence: number;
  explanation: {
    reason: string;
    sample_index?: number;
    timestamp_ms?: number;
    related_factors: string[];
    suggested_tests: string[];
  };
  reviews: { note: string; state: string; created_at: string }[];
};
export type Analysis = {
  id: string;
  media_id: string;
  provider_version: string;
  biomechanics_version: string;
  rules_version: string;
  created_at: string;
  media: {
    view: string;
    width: number;
    height: number;
    mime: string;
    metadata_json?: { duration_seconds: number };
  };
  motion?: {
    version?: string;
    protocol: string;
    signal: string;
    target_fps: number;
    phase_limitations: string;
    comparison: Record<string, { values: (number | null)[] }>;
    phase_detection: {
      phases: string[];
      cycles: {
        complete: boolean;
        start_index: number;
        peak_index: number;
        end_index: number | null;
      }[];
      events: { type: string; index: number; timestamp_ms: number }[];
    };
  };
  quality: {
    landmark_visibility_mean: number;
    coverage: number;
    messages: string[];
    limitations: string[];
  };
  measurements: Measurement[];
  findings: Finding[];
  frames: {
    landmarks: import("../vision/types").Landmark[];
    frame_index: number;
    timestamp_ms: number;
    phase: string;
    measurements?: {
      values: Record<string, number | null>;
      velocity: Record<string, number | null>;
    };
    quality?: { messages: string[] };
  }[];
};
export type ProcessingJob = {
  id: string;
  media_id: string;
  state: string;
  progress: number;
  error: string;
  updated_at: string;
  options: {
    fps: number;
    camera_level_confirmed: boolean;
    view_confirmed: boolean;
  };
};
