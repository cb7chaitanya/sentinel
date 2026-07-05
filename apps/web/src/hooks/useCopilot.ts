"use client";

import { useCallback, useState } from "react";

import { apiPost } from "@/lib/api-client";
import type { CopilotAnswer } from "@/types";

export interface ChatMessage {
  id: string;
  role: "user" | "assistant";
  text: string;
  answer?: CopilotAnswer;
  pending?: boolean;
  failed?: boolean;
}

export function useCopilot(warehouseId: string | null): {
  messages: ChatMessage[];
  ask: (question: string) => Promise<void>;
  sending: boolean;
} {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [sending, setSending] = useState(false);

  const ask = useCallback(
    async (question: string) => {
      const trimmed = question.trim();
      if (!warehouseId || !trimmed) return;

      const pendingId = crypto.randomUUID();
      setMessages((prev) => [
        ...prev,
        { id: crypto.randomUUID(), role: "user", text: trimmed },
        { id: pendingId, role: "assistant", text: "", pending: true },
      ]);
      setSending(true);

      try {
        const answer = await apiPost<CopilotAnswer>("/api/v1/copilot/ask", {
          warehouse_id: warehouseId,
          question: trimmed,
        });
        setMessages((prev) =>
          prev.map((message) =>
            message.id === pendingId
              ? { id: pendingId, role: "assistant", text: answer.answer, answer }
              : message,
          ),
        );
      } catch {
        setMessages((prev) =>
          prev.map((message) =>
            message.id === pendingId
              ? {
                  id: pendingId,
                  role: "assistant",
                  text: "Something went wrong reaching the copilot.",
                  failed: true,
                }
              : message,
          ),
        );
      } finally {
        setSending(false);
      }
    },
    [warehouseId],
  );

  return { messages, ask, sending };
}
