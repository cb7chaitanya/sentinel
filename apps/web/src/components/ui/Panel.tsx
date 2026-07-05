import type { ReactNode } from "react";

interface PanelProps {
  id?: string;
  title: string;
  icon?: ReactNode;
  meta?: ReactNode;
  actions?: ReactNode;
  children: ReactNode;
  className?: string;
  bodyClassName?: string;
}

/** The one card shell every dashboard panel uses, for a consistent frame/header/scroll area. */
export function Panel({
  id,
  title,
  icon,
  meta,
  actions,
  children,
  className = "",
  bodyClassName = "",
}: PanelProps) {
  return (
    <section
      id={id}
      className={`flex flex-col overflow-hidden rounded-lg border border-neutral-800/80 bg-neutral-900/40 ${className}`}
    >
      <header className="flex shrink-0 items-center justify-between gap-3 border-b border-neutral-800/80 px-4 py-3">
        <div className="flex min-w-0 items-center gap-2">
          {icon ? <span className="shrink-0 text-neutral-500">{icon}</span> : null}
          <h2 className="truncate text-xs font-semibold uppercase tracking-wider text-neutral-400">
            {title}
          </h2>
          {meta}
        </div>
        {actions ? <div className="flex shrink-0 items-center gap-2">{actions}</div> : null}
      </header>
      <div className={`min-h-0 flex-1 ${bodyClassName}`}>{children}</div>
    </section>
  );
}
