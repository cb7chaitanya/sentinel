"use client";

import { useEffect, useRef, useState } from "react";

import { ChatIcon, SendIcon } from "@/components/icons";
import { Badge } from "@/components/ui/Badge";
import { Panel } from "@/components/ui/Panel";
import { type ChatMessage, useCopilot } from "@/hooks/useCopilot";

const EXAMPLE_QUESTIONS = [
  "Where is pallet P103?",
  "What happened in Zone B?",
  "Why was this alert generated?",
];

function MessageBubble({ message }: { message: ChatMessage }) {
  const isUser = message.role === "user";
  return (
    <div className={`flex ${isUser ? "justify-end" : "justify-start"}`}>
      <div className={`max-w-[85%] ${isUser ? "items-end" : "items-start"} flex flex-col gap-1`}>
        <div
          className={`rounded-lg px-3 py-2 text-sm ${
            isUser
              ? "bg-indigo-500/15 text-indigo-100 ring-1 ring-inset ring-indigo-500/30"
              : message.failed
                ? "bg-red-500/10 text-red-200 ring-1 ring-inset ring-red-500/30"
                : "bg-neutral-900 text-neutral-200 ring-1 ring-inset ring-neutral-800"
          }`}
        >
          {message.pending ? (
            <span className="flex items-center gap-1 text-neutral-500">
              <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-neutral-500" />
              <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-neutral-500 [animation-delay:150ms]" />
              <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-neutral-500 [animation-delay:300ms]" />
            </span>
          ) : (
            message.text
          )}
        </div>
        {message.answer && message.answer.citations.length > 0 ? (
          <div className="flex flex-wrap gap-1 px-0.5">
            {message.answer.citations.map((citation, index) => (
              <Badge key={`${citation.kind}-${citation.reference_id}-${index}`} tone="violet">
                {citation.kind}:{citation.reference_id.slice(0, 8)}
              </Badge>
            ))}
          </div>
        ) : null}
      </div>
    </div>
  );
}

interface ChatPanelProps {
  warehouseId: string | null;
  className?: string;
}

export function ChatPanel({ warehouseId, className = "" }: ChatPanelProps) {
  const { messages, ask, sending } = useCopilot(warehouseId);
  const [draft, setDraft] = useState("");
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: "smooth" });
  }, [messages]);

  function submit() {
    if (!draft.trim() || sending) return;
    void ask(draft);
    setDraft("");
  }

  return (
    <Panel
      id="copilot"
      title="Operations copilot"
      icon={<ChatIcon className="h-4 w-4" />}
      className={`h-[600px] xl:h-[calc(100dvh-3rem)] ${className}`}
      bodyClassName="flex flex-col"
    >
      <div ref={scrollRef} className="scrollbar-thin flex-1 space-y-3 overflow-y-auto px-4 py-3">
        {messages.length === 0 ? (
          <div className="flex h-full flex-col items-center justify-center gap-3 px-2 text-center">
            <ChatIcon className="h-8 w-8 text-neutral-700" />
            <p className="text-sm text-neutral-500">
              Ask about anything the warehouse has actually observed.
            </p>
            <div className="flex flex-col gap-1.5">
              {EXAMPLE_QUESTIONS.map((question) => (
                <button
                  key={question}
                  type="button"
                  onClick={() => setDraft(question)}
                  className="rounded-md border border-neutral-800 px-3 py-1.5 text-xs text-neutral-400 hover:border-neutral-700 hover:text-neutral-200"
                >
                  {question}
                </button>
              ))}
            </div>
          </div>
        ) : (
          messages.map((message) => <MessageBubble key={message.id} message={message} />)
        )}
      </div>

      <div className="flex shrink-0 items-center gap-2 border-t border-neutral-800/80 p-3">
        <input
          value={draft}
          onChange={(event) => setDraft(event.target.value)}
          onKeyDown={(event) => {
            if (event.key === "Enter" && !event.shiftKey) {
              event.preventDefault();
              submit();
            }
          }}
          disabled={!warehouseId}
          placeholder={warehouseId ? "Ask the copilot…" : "No warehouse configured"}
          className="flex-1 rounded-md border border-neutral-800 bg-neutral-900 px-3 py-2 text-sm text-neutral-200 placeholder:text-neutral-600 focus:outline-none focus:ring-1 focus:ring-indigo-500 disabled:opacity-50"
        />
        <button
          type="button"
          onClick={submit}
          disabled={!warehouseId || !draft.trim() || sending}
          aria-label="Send"
          className="flex h-9 w-9 shrink-0 items-center justify-center rounded-md bg-indigo-500 text-white transition-colors hover:bg-indigo-400 disabled:cursor-not-allowed disabled:bg-neutral-800 disabled:text-neutral-600"
        >
          <SendIcon className="h-4 w-4" />
        </button>
      </div>
    </Panel>
  );
}
