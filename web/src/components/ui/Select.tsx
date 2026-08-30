import { forwardRef } from "react";
import type { SelectHTMLAttributes } from "react";

export interface SelectProps extends SelectHTMLAttributes<HTMLSelectElement> {
  label?: string;
  error?: string;
}

export const Select = forwardRef<HTMLSelectElement, SelectProps>(
  ({ label, error, id, className = "", children, ...props }, ref) => {
    const selectId = id ?? props.name;
    return (
      <div className="flex flex-col gap-1.5">
        {label && (
          <label htmlFor={selectId} className="text-sm font-medium text-ink-700">
            {label}
          </label>
        )}
        <select
          ref={ref}
          id={selectId}
          className={`rounded-lg border border-ink-200 bg-white px-3.5 py-2.5 text-sm text-ink-900 focus-visible:border-accent-500 ${
            error ? "border-accent-400" : ""
          } ${className}`}
          {...props}
        >
          {children}
        </select>
        {error && <p className="text-xs text-accent-600">{error}</p>}
      </div>
    );
  }
);

Select.displayName = "Select";
