import { ActivityIcon, AlertIcon, MapIcon } from "@/components/icons";
import { Badge, type BadgeTone } from "@/components/ui/Badge";
import { EmptyState } from "@/components/ui/EmptyState";
import { Panel } from "@/components/ui/Panel";
import { timeAgo } from "@/lib/format";
import type { EventType, WarehouseEvent } from "@/types";

const RULE_EVENT_TYPES = new Set<EventType>([
  "zone_breach",
  "loitering",
  "forklift_proximity",
  "ppe_violation",
  "dwell_time_exceeded",
]);

const ZONE_EVENT_TYPES = new Set<EventType>(["zone_entered", "zone_exited"]);

function iconFor(eventType: EventType) {
  if (RULE_EVENT_TYPES.has(eventType)) return AlertIcon;
  if (ZONE_EVENT_TYPES.has(eventType)) return MapIcon;
  return ActivityIcon;
}

function toneFor(eventType: EventType): BadgeTone {
  return RULE_EVENT_TYPES.has(eventType) ? "amber" : "neutral";
}

interface RecentEventsPanelProps {
  events: WarehouseEvent[] | null;
}

export function RecentEventsPanel({ events }: RecentEventsPanelProps) {
  const sorted = events
    ? [...events].sort(
        (a, b) => new Date(b.occurred_at).getTime() - new Date(a.occurred_at).getTime(),
      )
    : null;

  return (
    <Panel
      id="events"
      title="Recent events"
      icon={<ActivityIcon className="h-4 w-4" />}
      meta={sorted ? <Badge tone="blue">{sorted.length}</Badge> : null}
      className="h-[420px]"
      bodyClassName="overflow-y-auto scrollbar-thin"
    >
      {sorted === null ? (
        <EmptyState icon={<ActivityIcon className="h-8 w-8" />} title="Waiting for warehouse state…" />
      ) : sorted.length === 0 ? (
        <EmptyState
          icon={<ActivityIcon className="h-8 w-8" />}
          title="No recent activity"
          description="Zone transitions and object activity will appear here as they happen."
        />
      ) : (
        <ul className="divide-y divide-neutral-800/70">
          {sorted.map((event) => {
            const Icon = iconFor(event.event_type);
            return (
              <li key={event.id} className="flex items-start gap-2.5 px-4 py-2.5">
                <Icon className="mt-0.5 h-3.5 w-3.5 shrink-0 text-neutral-500" />
                <div className="min-w-0 flex-1">
                  <p className="truncate text-sm text-neutral-200">{event.summary}</p>
                  <div className="mt-0.5 flex items-center gap-1.5">
                    <Badge tone={toneFor(event.event_type)}>{event.event_type}</Badge>
                    {event.zone_name ? <Badge tone="neutral">{event.zone_name}</Badge> : null}
                  </div>
                </div>
                <span className="shrink-0 whitespace-nowrap text-[11px] text-neutral-600">
                  {timeAgo(event.occurred_at)}
                </span>
              </li>
            );
          })}
        </ul>
      )}
    </Panel>
  );
}
