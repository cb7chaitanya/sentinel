"use client";

import { useEffect, useState } from "react";

import { CameraIcon } from "@/components/icons";
import { Badge, type BadgeTone } from "@/components/ui/Badge";
import { EmptyState } from "@/components/ui/EmptyState";
import { Panel } from "@/components/ui/Panel";
import { apiGet, gatewayUrl } from "@/lib/api-client";
import { shortId } from "@/lib/format";
import type { ConnectionState, StreamHealth } from "@/types";

const STREAMS_POLL_INTERVAL_MS = 5000;

const STATE_TONE: Record<ConnectionState, BadgeTone> = {
  connected: "emerald",
  connecting: "amber",
  reconnecting: "amber",
  stopped: "neutral",
};

export function LiveCameraPanel() {
  const [streams, setStreams] = useState<StreamHealth[] | null>(null);
  const [selected, setSelected] = useState<string | null>(null);
  const [feedFailed, setFeedFailed] = useState(false);

  useEffect(() => {
    let cancelled = false;

    async function poll() {
      try {
        const result = await apiGet<StreamHealth[]>("/api/v1/cameras/streams");
        if (cancelled) return;
        setStreams(result);
        setSelected((current) => current ?? result[0]?.camera_id ?? null);
      } catch {
        if (!cancelled) setStreams((current) => current ?? []);
      }
    }

    void poll();
    const interval = setInterval(poll, STREAMS_POLL_INTERVAL_MS);
    return () => {
      cancelled = true;
      clearInterval(interval);
    };
  }, []);

  useEffect(() => {
    setFeedFailed(false);
  }, [selected]);

  const selectedHealth = streams?.find((stream) => stream.camera_id === selected) ?? null;

  return (
    <Panel
      id="camera"
      title="Live camera"
      icon={<CameraIcon className="h-4 w-4" />}
      meta={
        selectedHealth ? (
          <Badge tone={STATE_TONE[selectedHealth.state]} dot>
            {selectedHealth.state}
          </Badge>
        ) : null
      }
      actions={
        streams && streams.length > 0 ? (
          <select
            value={selected ?? ""}
            onChange={(event) => setSelected(event.target.value)}
            className="rounded-md border border-neutral-800 bg-neutral-900 px-2 py-1 text-xs text-neutral-300 focus:outline-none focus:ring-1 focus:ring-indigo-500"
          >
            {streams.map((stream) => (
              <option key={stream.camera_id} value={stream.camera_id}>
                cam_{shortId(stream.camera_id)}
              </option>
            ))}
          </select>
        ) : null
      }
      className="h-[420px]"
      bodyClassName="relative flex items-center justify-center bg-black"
    >
      {streams === null ? (
        <EmptyState icon={<CameraIcon className="h-8 w-8" />} title="Loading cameras…" />
      ) : streams.length === 0 ? (
        <EmptyState
          icon={<CameraIcon className="h-8 w-8" />}
          title="No cameras configured"
          description="Set CAMERA_SOURCES on the ingestion service to connect an RTSP stream, webcam, or video file."
        />
      ) : selected && !feedFailed ? (
        // eslint-disable-next-line @next/next/no-img-element -- MJPEG multipart streams aren't compatible with next/image.
        <img
          key={selected}
          src={gatewayUrl(`/api/v1/cameras/${selected}/mjpeg`)}
          alt="Live camera feed"
          className="h-full w-full object-contain"
          onError={() => setFeedFailed(true)}
        />
      ) : (
        <EmptyState
          icon={<CameraIcon className="h-8 w-8" />}
          title="No live feed"
          description="This camera is configured but not currently streaming."
        />
      )}

      {selectedHealth ? (
        <div className="absolute bottom-2 right-2 flex items-center gap-1.5 rounded-md bg-black/60 px-2 py-1 font-mono text-[11px] text-neutral-300 backdrop-blur">
          {selectedHealth.fps.toFixed(1)} fps
        </div>
      ) : null}
    </Panel>
  );
}
