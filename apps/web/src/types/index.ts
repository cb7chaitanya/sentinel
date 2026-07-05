// Wire-format types mirroring the shared Pydantic schemas and each
// service's own domain models (libs/sentinel_common, services/memory,
// services/ingestion, services/agent). Keep in sync manually until a
// generated-client step is introduced.

export type EntityType = "worker" | "forklift" | "pallet" | "box" | "other";

export type EventType =
  | "zone_breach"
  | "loitering"
  | "forklift_proximity"
  | "ppe_violation"
  | "dwell_time_exceeded"
  | "zone_entered"
  | "zone_exited"
  | "object_moved"
  | "object_stopped"
  | "object_picked";

export type AlertSeverity = "low" | "medium" | "high" | "critical";
export type AlertStatus = "open" | "acknowledged" | "resolved";

export type ConnectionState = "connecting" | "connected" | "reconnecting" | "stopped";

export interface BoundingBox {
  x_min: number;
  y_min: number;
  x_max: number;
  y_max: number;
}

export interface Velocity {
  vx: number;
  vy: number;
}

export interface EntityRead {
  id: string;
  warehouse_id: string;
  camera_id: string;
  track_id: number;
  entity_type: EntityType;
  label: string;
  bounding_box: BoundingBox;
  velocity: Velocity | null;
  first_seen_at: string;
  last_seen_at: string;
  created_at: string;
  updated_at: string;
}

export interface ZoneOccupancyRead {
  id: string;
  warehouse_id: string;
  zone_id: string;
  zone_name: string;
  entity_id: string;
  entered_at: string;
  exited_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface WarehouseEvent {
  id: string;
  camera_id: string;
  event_type: EventType;
  occurred_at: string;
  summary: string;
  warehouse_id: string | null;
  track_id: number | null;
  zone_id: string | null;
  zone_name: string | null;
  dwell_time_seconds: number | null;
  related_track_id: number | null;
  related_label: string | null;
  metadata: Record<string, string>;
  created_at: string;
  updated_at: string;
}

export interface AlertRead {
  id: string;
  warehouse_id: string;
  camera_id: string | null;
  event_id: string | null;
  severity: AlertSeverity;
  summary: string;
  status: AlertStatus;
  resolved_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface WarehouseState {
  warehouse_id: string;
  generated_at: string;
  entities: EntityRead[];
  zone_occupancy: ZoneOccupancyRead[];
  recent_events: WarehouseEvent[];
  active_alerts: AlertRead[];
}

export interface StreamHealth {
  camera_id: string;
  state: ConnectionState;
  fps: number;
  frames_read: number;
  frames_dropped: number;
  reconnect_count: number;
  last_frame_at: string | null;
  connected_since: string | null;
}

export type CitationKind = "event" | "entity" | "inventory_record" | "safety_rule" | "alert";

export interface Citation {
  kind: CitationKind;
  reference_id: string;
  detail: string;
}

export interface CopilotQuestion {
  warehouse_id: string;
  question: string;
  entity_id?: string | null;
  zone_name?: string | null;
  alert_id?: string | null;
}

export interface CopilotAnswer {
  question: string;
  warehouse_id: string;
  generated_at: string;
  answer: string;
  citations: Citation[];
  grounded: boolean;
}

export interface HealthResponse {
  status: string;
  service: string;
}
