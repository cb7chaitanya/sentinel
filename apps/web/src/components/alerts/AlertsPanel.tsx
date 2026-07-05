import { AlertIcon } from "@/components/icons";
import { Badge, type BadgeTone } from "@/components/ui/Badge";
import { EmptyState } from "@/components/ui/EmptyState";
import { Panel } from "@/components/ui/Panel";
import { timeAgo } from "@/lib/format";
import type { AlertRead, AlertSeverity, AlertStatus } from "@/types";

const SEVERITY_TONE: Record<AlertSeverity, BadgeTone> = {
  low: "neutral",
  medium: "amber",
  high: "amber",
  critical: "red",
};

const STATUS_TONE: Record<AlertStatus, BadgeTone> = {
  open: "red",
  acknowledged: "amber",
  resolved: "emerald",
};

interface AlertsPanelProps {
  alerts: AlertRead[] | null;
}

export function AlertsPanel({ alerts }: AlertsPanelProps) {
  const sorted = alerts
    ? [...alerts].sort(
        (a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime(),
      )
    : null;
  const openCount = sorted?.filter((alert) => alert.status !== "resolved").length ?? 0;

  return (
    <Panel
      id="alerts"
      title="Alerts"
      icon={<AlertIcon className="h-4 w-4" />}
      meta={sorted ? <Badge tone={openCount > 0 ? "red" : "emerald"}>{openCount} open</Badge> : null}
      className="h-[420px]"
      bodyClassName="overflow-y-auto scrollbar-thin"
    >
      {sorted === null ? (
        <EmptyState icon={<AlertIcon className="h-8 w-8" />} title="Waiting for warehouse state…" />
      ) : sorted.length === 0 ? (
        <EmptyState
          icon={<AlertIcon className="h-8 w-8" />}
          title="No alerts"
          description="Alerts raised by safety rules or the reasoning agent will appear here."
        />
      ) : (
        <ul className="divide-y divide-neutral-800/70">
          {sorted.map((alert) => (
            <li key={alert.id} className="flex flex-col gap-1.5 px-4 py-2.5">
              <div className="flex items-center gap-1.5">
                <Badge tone={SEVERITY_TONE[alert.severity]} dot>
                  {alert.severity}
                </Badge>
                <Badge tone={STATUS_TONE[alert.status]}>{alert.status}</Badge>
                <span className="ml-auto shrink-0 whitespace-nowrap text-[11px] text-neutral-600">
                  {timeAgo(alert.created_at)}
                </span>
              </div>
              <p className="text-sm text-neutral-200">{alert.summary}</p>
            </li>
          ))}
        </ul>
      )}
    </Panel>
  );
}
