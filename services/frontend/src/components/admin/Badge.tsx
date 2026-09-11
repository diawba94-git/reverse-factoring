import type { ReactNode } from "react";

type BadgeTone = "success" | "warning" | "danger" | "neutral";

export function Badge({ tone, children }: { tone: BadgeTone; children: ReactNode }) {
  return <span className={`admin-badge admin-badge--${tone}`}>{children}</span>;
}
