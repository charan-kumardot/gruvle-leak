import type { ReactNode } from "react";

export interface EmptyStateProps {
  eyebrow?: string;
  title: string;
  description?: string;
  action?: ReactNode;
  secondary?: ReactNode;
  icon?: ReactNode;
}

export function EmptyState({
  eyebrow,
  title,
  description,
  action,
  secondary,
  icon,
}: EmptyStateProps) {
  return (
    <div className="flex flex-col items-center justify-center rounded-xl border border-dashed border-ink-200 bg-white px-6 py-16 text-center">
      {icon && <div className="mb-4 text-ink-300">{icon}</div>}
      {eyebrow && (
        <p className="mb-2 text-xs font-medium uppercase tracking-wide text-ink-400">
          {eyebrow}
        </p>
      )}
      <h3 className="text-lg font-semibold text-ink-900">{title}</h3>
      {description && (
        <p className="mt-2 max-w-sm text-sm leading-relaxed text-ink-500">{description}</p>
      )}
      {action && <div className="mt-6">{action}</div>}
      {secondary && <div className="mt-3 text-xs text-ink-400">{secondary}</div>}
    </div>
  );
}
