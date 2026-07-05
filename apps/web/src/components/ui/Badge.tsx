import type { ReactNode } from "react";

export type BadgeTone = "neutral" | "blue" | "emerald" | "amber" | "red" | "violet";

const TONE_CLASSES: Record<BadgeTone, string> = {
  neutral: "bg-neutral-800 text-neutral-300 ring-neutral-700",
  blue: "bg-blue-500/10 text-blue-400 ring-blue-500/30",
  emerald: "bg-emerald-500/10 text-emerald-400 ring-emerald-500/30",
  amber: "bg-amber-500/10 text-amber-400 ring-amber-500/30",
  red: "bg-red-500/10 text-red-400 ring-red-500/30",
  violet: "bg-violet-500/10 text-violet-400 ring-violet-500/30",
};

interface BadgeProps {
  tone?: BadgeTone;
  children: ReactNode;
  className?: string;
  dot?: boolean;
}

export function Badge({ tone = "neutral", children, className = "", dot = false }: BadgeProps) {
  return (
    <span
      className={`inline-flex items-center gap-1.5 whitespace-nowrap rounded-md px-1.5 py-0.5 text-[11px] font-medium ring-1 ring-inset ${TONE_CLASSES[tone]} ${className}`}
    >
      {dot ? <span className="h-1.5 w-1.5 shrink-0 rounded-full bg-current" /> : null}
      {children}
    </span>
  );
}
