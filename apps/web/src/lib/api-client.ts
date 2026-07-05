// Minimal typed fetch wrapper for talking to the gateway. No business
// logic here — just a thin, typed transport that route handlers/components
// build on.

const GATEWAY_URL = process.env.NEXT_PUBLIC_GATEWAY_URL ?? "http://localhost:8000";

export class ApiError extends Error {
  constructor(
    public readonly status: number,
    message: string,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

export async function apiGet<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${GATEWAY_URL}${path}`, {
    ...init,
    headers: { Accept: "application/json", ...init?.headers },
  });

  if (!response.ok) {
    throw new ApiError(response.status, `GET ${path} failed with ${response.status}`);
  }

  return response.json() as Promise<T>;
}

export async function apiPost<T>(path: string, body: unknown, init?: RequestInit): Promise<T> {
  const response = await fetch(`${GATEWAY_URL}${path}`, {
    ...init,
    method: "POST",
    headers: {
      Accept: "application/json",
      "Content-Type": "application/json",
      ...init?.headers,
    },
    body: JSON.stringify(body),
  });

  if (!response.ok) {
    throw new ApiError(response.status, `POST ${path} failed with ${response.status}`);
  }

  return response.json() as Promise<T>;
}

/** Absolute HTTP(S) URL for a gateway path -- used for e.g. an <img> MJPEG source. */
export function gatewayUrl(path: string): string {
  return `${GATEWAY_URL}${path}`;
}

/** ws:// or wss:// URL for a gateway WebSocket path, mirroring the gateway's own scheme. */
export function gatewayWsUrl(path: string): string {
  const wsBase = GATEWAY_URL.replace(/^http/, "ws");
  return `${wsBase}${path}`;
}
