import type { ReactNode } from "react";

import { BoxIcon, ForkliftIcon, MapIcon, PalletIcon, WorkerIcon } from "@/components/icons";
import { Badge } from "@/components/ui/Badge";
import { EmptyState } from "@/components/ui/EmptyState";
import { Panel } from "@/components/ui/Panel";
import { dwellSeconds, formatDuration, timeAgo } from "@/lib/format";
import type { EntityRead, EntityType, WarehouseState } from "@/types";

const ENTITY_ICON: Record<EntityType, (props: { className?: string }) => ReactNode> = {
  worker: WorkerIcon,
  forklift: ForkliftIcon,
  pallet: PalletIcon,
  box: BoxIcon,
  other: BoxIcon,
};

interface Occupant {
  entity: EntityRead;
  /** Zone entry time for a dwell timer, or `null` to show "last seen" instead (unzoned entities). */
  since: string | null;
}

interface Zone {
  name: string;
  occupants: Occupant[];
}

function buildZones(state: WarehouseState): { zones: Zone[]; unzoned: EntityRead[] } {
  const entityById = new Map(state.entities.map((entity) => [entity.id, entity]));
  const openOccupancy = state.zone_occupancy.filter((occupancy) => occupancy.exited_at === null);
  const occupiedEntityIds = new Set(openOccupancy.map((occupancy) => occupancy.entity_id));

  const zonesByName = new Map<string, Zone>();
  for (const occupancy of openOccupancy) {
    const entity = entityById.get(occupancy.entity_id);
    if (!entity) continue;
    const zone = zonesByName.get(occupancy.zone_name) ?? { name: occupancy.zone_name, occupants: [] };
    zone.occupants.push({ entity, since: occupancy.entered_at });
    zonesByName.set(occupancy.zone_name, zone);
  }

  const unzoned = state.entities.filter((entity) => !occupiedEntityIds.has(entity.id));

  return {
    zones: [...zonesByName.values()].sort((a, b) => a.name.localeCompare(b.name)),
    unzoned,
  };
}

function OccupantChip({ occupant }: { occupant: Occupant }) {
  const Icon = ENTITY_ICON[occupant.entity.entity_type];
  const label = occupant.since
    ? formatDuration(dwellSeconds(occupant.since))
    : timeAgo(occupant.entity.last_seen_at);

  return (
    <div className="flex items-center gap-1.5 rounded-md bg-neutral-900 px-2 py-1 ring-1 ring-inset ring-neutral-800">
      <Icon className="h-3.5 w-3.5 shrink-0 text-neutral-400" />
      <span className="truncate text-[11px] text-neutral-300">{occupant.entity.label}</span>
      <span className="ml-auto shrink-0 font-mono text-[10px] text-neutral-500">{label}</span>
    </div>
  );
}

function ZoneTile({ zone, muted = false }: { zone: Zone; muted?: boolean }) {
  return (
    <div
      className={`flex flex-col gap-1.5 rounded-lg border p-2.5 ${
        muted
          ? "border-dashed border-neutral-800/80 bg-transparent"
          : "border-neutral-800 bg-neutral-900/60"
      }`}
    >
      <div className="flex items-center justify-between gap-2">
        <span className="truncate text-xs font-medium text-neutral-300">{zone.name}</span>
        <Badge tone={muted ? "neutral" : "blue"}>{zone.occupants.length}</Badge>
      </div>
      <div className="flex flex-col gap-1">
        {zone.occupants.map((occupant) => (
          <OccupantChip key={occupant.entity.id} occupant={occupant} />
        ))}
      </div>
    </div>
  );
}

interface WarehouseMapPanelProps {
  state: WarehouseState | null;
}

export function WarehouseMapPanel({ state }: WarehouseMapPanelProps) {
  const { zones, unzoned } =
    state !== null ? buildZones(state) : { zones: [] as Zone[], unzoned: [] as EntityRead[] };
  const isEmpty = zones.length === 0 && unzoned.length === 0;

  return (
    <Panel
      id="map"
      title="Warehouse map"
      icon={<MapIcon className="h-4 w-4" />}
      meta={state ? <Badge tone="blue">{zones.length} zones</Badge> : null}
      className="h-[420px]"
      bodyClassName="overflow-y-auto scrollbar-thin p-3"
    >
      {state === null ? (
        <EmptyState icon={<MapIcon className="h-8 w-8" />} title="Waiting for warehouse state…" />
      ) : isEmpty ? (
        <EmptyState
          icon={<MapIcon className="h-8 w-8" />}
          title="No tracked entities"
          description="Zone occupancy appears here once the vision/events pipeline reports activity."
        />
      ) : (
        <div className="grid grid-cols-2 gap-2 sm:grid-cols-3">
          {zones.map((zone) => (
            <ZoneTile key={zone.name} zone={zone} />
          ))}
          {unzoned.length > 0 ? (
            <ZoneTile
              zone={{
                name: "In transit",
                occupants: unzoned.map((entity) => ({ entity, since: null })),
              }}
              muted
            />
          ) : null}
        </div>
      )}
    </Panel>
  );
}
