// Wire-format types mirroring the shared Pydantic schemas
// (libs/sentinel_common/src/sentinel_common/schemas). Keep in sync manually
// until a generated-client step is introduced.

export type EventType =
  | "zone_breach"
  | "loitering"
  | "forklift_proximity"
  | "ppe_violation"
  | "dwell_time_exceeded";

export interface Camera {
  id: string;
  name: string;
  rtsp_url: string;
  zone: string | null;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface WarehouseEvent {
  id: string;
  camera_id: string;
  event_type: EventType;
  occurred_at: string;
  summary: string;
  metadata: Record<string, string>;
  created_at: string;
  updated_at: string;
}

export interface HealthResponse {
  status: string;
  service: string;
}
