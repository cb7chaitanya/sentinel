// Minimal hand-drawn line icons -- deliberately not an icon library
// dependency. Every icon is a plain 24x24 stroke path taking the same
// `className` prop, so callers size/color them with Tailwind like any
// other element (e.g. `className="h-4 w-4 text-neutral-500"`).

import type { ReactNode } from "react";

export interface IconProps {
  className?: string;
}

function base(children: ReactNode, className?: string) {
  return (
    <svg
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth={1.75}
      strokeLinecap="round"
      strokeLinejoin="round"
      className={className}
      aria-hidden="true"
    >
      {children}
    </svg>
  );
}

export function CameraIcon({ className }: IconProps) {
  return base(
    <>
      <path d="M4 8h2.5l1.2-2h8.6l1.2 2H20a1 1 0 0 1 1 1v9a1 1 0 0 1-1 1H4a1 1 0 0 1-1-1V9a1 1 0 0 1 1-1Z" />
      <circle cx="12" cy="13.5" r="3.25" />
    </>,
    className,
  );
}

export function MapIcon({ className }: IconProps) {
  return base(
    <>
      <path d="M9 4 4 6v14l5-2 6 2 5-2V4l-5 2-6-2Z" />
      <path d="M9 4v14M15 6v14" />
    </>,
    className,
  );
}

export function ActivityIcon({ className }: IconProps) {
  return base(<path d="M3 12h4l2 8 4-16 2 8h6" />, className);
}

export function AlertIcon({ className }: IconProps) {
  return base(
    <>
      <path d="M12 3 2 20h20L12 3Z" />
      <path d="M12 10v4M12 17h.01" />
    </>,
    className,
  );
}

export function ChatIcon({ className }: IconProps) {
  return base(
    <path d="M4 5h16v10H8.5L4 19V5Z" />,
    className,
  );
}

export function SendIcon({ className }: IconProps) {
  return base(<path d="m4 12 16-8-6 8 6 8-16-8Z" />, className);
}

export function WifiIcon({ className }: IconProps) {
  return base(
    <>
      <path d="M2 8.5a15 15 0 0 1 20 0" />
      <path d="M5.5 12.5a10 10 0 0 1 13 0" />
      <path d="M9 16.5a5 5 0 0 1 6 0" />
      <path d="M12 20h.01" />
    </>,
    className,
  );
}

export function WifiOffIcon({ className }: IconProps) {
  return base(
    <>
      <path d="M2 8.5c1.9-1.6 4.1-2.6 6.5-3M22 8.5a15 15 0 0 0-4.3-2.7" />
      <path d="M5.5 12.5a10 10 0 0 1 4.6-2.4M18.5 12.5a10 10 0 0 0-2.6-1.9" />
      <path d="M9 16.5a5 5 0 0 1 6 0" />
      <path d="M12 20h.01" />
      <path d="M2 2l20 20" />
    </>,
    className,
  );
}

export function MenuIcon({ className }: IconProps) {
  return base(<path d="M4 6h16M4 12h16M4 18h16" />, className);
}

export function CloseIcon({ className }: IconProps) {
  return base(<path d="M6 6l12 12M18 6 6 18" />, className);
}

export function BoxIcon({ className }: IconProps) {
  return base(
    <>
      <path d="M3 8 12 3l9 5v8l-9 5-9-5V8Z" />
      <path d="M3 8l9 5 9-5M12 13v8" />
    </>,
    className,
  );
}

export function ForkliftIcon({ className }: IconProps) {
  return base(
    <>
      <path d="M4 4v11h6" />
      <path d="M10 8h4v7h-4" />
      <circle cx="7" cy="18" r="1.75" />
      <circle cx="16" cy="18" r="1.75" />
      <path d="M17.75 18h2.25V11" />
    </>,
    className,
  );
}

export function WorkerIcon({ className }: IconProps) {
  return base(
    <>
      <circle cx="12" cy="6" r="2.25" />
      <path d="M7 20v-5.5L9 10h6l2 4.5V20" />
    </>,
    className,
  );
}

export function PalletIcon({ className }: IconProps) {
  return base(
    <>
      <path d="M3 9h18M3 13h18" />
      <path d="M5 9v4M9 9v4M15 9v4M19 9v4" />
      <path d="M4 17h16" />
    </>,
    className,
  );
}
