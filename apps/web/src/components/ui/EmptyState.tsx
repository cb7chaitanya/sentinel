import type { ReactNode } from "react";

interface EmptyStateProps {
  icon?: ReactNode;
  title: string;
  description?: string;
}

export function EmptyState({ icon, title, description }: EmptyStateProps) {
  return (
    <div className="flex h-full flex-col items-center justify-center gap-2 px-6 py-10 text-center">
      {icon ? <span className="text-neutral-700">{icon}</span> : null}
      <p className="text-sm font-medium text-neutral-500">{title}</p>
      {description ? <p className="max-w-xs text-xs text-neutral-600">{description}</p> : null}
    </div>
  );
}
