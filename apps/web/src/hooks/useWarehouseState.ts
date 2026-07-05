"use client";

import { useEffect, useState } from "react";

import { apiGet, gatewayWsUrl } from "@/lib/api-client";
import type { WarehouseState } from "@/types";

export type ConnectionStatus = "connecting" | "live" | "reconnecting" | "offline";

const RECONNECT_BASE_DELAY_MS = 1000;
const RECONNECT_MAX_DELAY_MS = 15000;

/**
 * Live warehouse state: an initial REST fetch (so the dashboard isn't blank
 * while the socket connects) followed by the gateway's WebSocket relay, with
 * exponential-backoff reconnect if the socket drops.
 */
export function useWarehouseState(warehouseId: string | null): {
  state: WarehouseState | null;
  status: ConnectionStatus;
} {
  const [state, setState] = useState<WarehouseState | null>(null);
  const [status, setStatus] = useState<ConnectionStatus>("connecting");

  useEffect(() => {
    if (!warehouseId) {
      setStatus("offline");
      return;
    }

    let cancelled = false;
    let reconnectAttempt = 0;
    let reconnectTimer: ReturnType<typeof setTimeout> | undefined;
    let socket: WebSocket | undefined;

    apiGet<WarehouseState>(`/api/v1/state/${warehouseId}`)
      .then((initial) => {
        if (!cancelled) setState(initial);
      })
      .catch(() => {
        // The socket connecting is what actually matters; this is only to
        // avoid a blank first paint.
      });

    function connect(): void {
      setStatus(reconnectAttempt === 0 ? "connecting" : "reconnecting");
      socket = new WebSocket(gatewayWsUrl(`/api/v1/ws/warehouse/${warehouseId}`));

      socket.onopen = () => {
        reconnectAttempt = 0;
        setStatus("live");
      };

      socket.onmessage = (event: MessageEvent<string>) => {
        try {
          setState(JSON.parse(event.data) as WarehouseState);
        } catch {
          // Ignore a malformed frame; the next one corrects the view.
        }
      };

      socket.onclose = () => {
        if (cancelled) return;
        setStatus("reconnecting");
        const delay = Math.min(
          RECONNECT_BASE_DELAY_MS * 2 ** reconnectAttempt,
          RECONNECT_MAX_DELAY_MS,
        );
        reconnectAttempt += 1;
        reconnectTimer = setTimeout(connect, delay);
      };

      socket.onerror = () => {
        socket?.close();
      };
    }

    connect();

    return () => {
      cancelled = true;
      clearTimeout(reconnectTimer);
      socket?.close();
    };
  }, [warehouseId]);

  return { state, status };
}
