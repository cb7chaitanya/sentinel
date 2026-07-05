import type { ConnectionStatus } from "@/hooks/useWarehouseState";
import {
  ActivityIcon,
  AlertIcon,
  CameraIcon,
  ChatIcon,
  CloseIcon,
  MapIcon,
  WifiIcon,
  WifiOffIcon,
} from "@/components/icons";
import { shortId } from "@/lib/format";

const NAV_ITEMS = [
  { href: "#camera", label: "Live camera", icon: CameraIcon },
  { href: "#map", label: "Warehouse map", icon: MapIcon },
  { href: "#events", label: "Recent events", icon: ActivityIcon },
  { href: "#alerts", label: "Alerts", icon: AlertIcon },
  { href: "#copilot", label: "Copilot", icon: ChatIcon },
];

const STATUS_LABEL: Record<ConnectionStatus, string> = {
  connecting: "Connecting…",
  live: "Live",
  reconnecting: "Reconnecting…",
  offline: "Offline",
};

const STATUS_DOT: Record<ConnectionStatus, string> = {
  connecting: "bg-amber-400",
  live: "bg-emerald-400",
  reconnecting: "bg-amber-400",
  offline: "bg-neutral-600",
};

interface SidebarProps {
  status: ConnectionStatus;
  warehouseId: string | null;
  mobileOpen: boolean;
  onNavigate: () => void;
}

export function Sidebar({ status, warehouseId, mobileOpen, onNavigate }: SidebarProps) {
  return (
    <aside
      className={`fixed inset-y-0 left-0 z-40 flex w-64 shrink-0 -translate-x-full flex-col border-r border-neutral-800/80 bg-neutral-950 transition-transform duration-200 md:sticky md:top-0 md:h-dvh md:translate-x-0 ${
        mobileOpen ? "translate-x-0" : ""
      }`}
    >
      <div className="flex items-center justify-between px-5 py-5">
        <div className="flex items-center gap-2.5">
          <span className="flex h-6 w-6 items-center justify-center rounded-md bg-indigo-500/15 ring-1 ring-inset ring-indigo-500/40">
            <span className="h-2 w-2 rounded-sm bg-indigo-400" />
          </span>
          <span className="text-sm font-semibold tracking-wide text-neutral-100">SENTINEL</span>
        </div>
        <button
          type="button"
          onClick={onNavigate}
          aria-label="Close navigation"
          className="rounded-md p-1 text-neutral-500 hover:bg-neutral-900 hover:text-neutral-300 md:hidden"
        >
          <CloseIcon className="h-4 w-4" />
        </button>
      </div>

      <nav className="flex-1 space-y-0.5 px-3">
        {NAV_ITEMS.map(({ href, label, icon: Icon }) => (
          <a
            key={href}
            href={href}
            onClick={onNavigate}
            className="flex items-center gap-2.5 rounded-md px-2.5 py-2 text-sm text-neutral-400 transition-colors hover:bg-neutral-900 hover:text-neutral-100"
          >
            <Icon className="h-4 w-4 shrink-0" />
            {label}
          </a>
        ))}
      </nav>

      <div className="space-y-2 border-t border-neutral-800/80 px-4 py-4">
        <div className="flex items-center gap-2 text-xs text-neutral-500">
          {status === "offline" ? (
            <WifiOffIcon className="h-3.5 w-3.5" />
          ) : (
            <WifiIcon className="h-3.5 w-3.5" />
          )}
          <span className={`h-1.5 w-1.5 rounded-full ${STATUS_DOT[status]}`} />
          {STATUS_LABEL[status]}
        </div>
        <div className="truncate font-mono text-[11px] text-neutral-600">
          {warehouseId ? `wh_${shortId(warehouseId)}` : "no warehouse configured"}
        </div>
      </div>
    </aside>
  );
}
