"use client";

import { useState } from "react";

import { AlertsPanel } from "@/components/alerts/AlertsPanel";
import { LiveCameraPanel } from "@/components/camera/LiveCameraPanel";
import { ChatPanel } from "@/components/chat/ChatPanel";
import { RecentEventsPanel } from "@/components/events/RecentEventsPanel";
import { MenuIcon } from "@/components/icons";
import { Sidebar } from "@/components/layout/Sidebar";
import { WarehouseMapPanel } from "@/components/map/WarehouseMapPanel";
import { useWarehouseState } from "@/hooks/useWarehouseState";

const WAREHOUSE_ID = process.env.NEXT_PUBLIC_WAREHOUSE_ID || null;

export function DashboardShell() {
  const [mobileNavOpen, setMobileNavOpen] = useState(false);
  const { state, status } = useWarehouseState(WAREHOUSE_ID);

  return (
    <div className="min-h-dvh bg-neutral-950">
      <div className="flex">
        <Sidebar
          status={status}
          warehouseId={WAREHOUSE_ID}
          mobileOpen={mobileNavOpen}
          onNavigate={() => setMobileNavOpen(false)}
        />

        {mobileNavOpen ? (
          <button
            type="button"
            aria-label="Close navigation"
            onClick={() => setMobileNavOpen(false)}
            className="fixed inset-0 z-30 bg-black/60 md:hidden"
          />
        ) : null}

        <div className="min-w-0 flex-1">
          <header className="sticky top-0 z-20 flex items-center gap-3 border-b border-neutral-800/80 bg-neutral-950/90 px-4 py-3 backdrop-blur md:hidden">
            <button
              type="button"
              aria-label="Open navigation"
              onClick={() => setMobileNavOpen(true)}
              className="rounded-md p-1.5 text-neutral-400 hover:bg-neutral-900 hover:text-neutral-100"
            >
              <MenuIcon className="h-5 w-5" />
            </button>
            <span className="text-sm font-semibold tracking-wide text-neutral-100">SENTINEL</span>
          </header>

          <main className="grid gap-4 p-4 md:p-6 xl:grid-cols-12">
            <div className="grid gap-4 lg:grid-cols-2 xl:col-span-8">
              <LiveCameraPanel />
              <WarehouseMapPanel state={state} />
              <RecentEventsPanel events={state?.recent_events ?? null} />
              <AlertsPanel alerts={state?.active_alerts ?? null} />
            </div>
            <div className="xl:col-span-4">
              <ChatPanel warehouseId={WAREHOUSE_ID} className="xl:sticky xl:top-6" />
            </div>
          </main>
        </div>
      </div>
    </div>
  );
}
