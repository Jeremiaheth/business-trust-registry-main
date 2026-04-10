import type { Badge } from "../lib/types";

interface StatusBadgeProps {
  badge: Badge;
}

export function StatusBadge({ badge }: StatusBadgeProps) {
  return <span className={`status-badge tone-${badge.tone}`}>{badge.label}</span>;
}
