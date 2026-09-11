import type { CSSProperties, InputHTMLAttributes, ReactNode } from "react";

type FormFieldProps = InputHTMLAttributes<HTMLInputElement> & {
  label: string;
  error?: string;
  hint?: string;
  labelExtra?: ReactNode;
  inputClassName?: string;
  /** Applies to the wrapping <label>, e.g. to zero out the default top margin
   * when the field sits in a grid row instead of stacking. */
  wrapperStyle?: CSSProperties;
};

export function FormField({
  label,
  error,
  hint,
  labelExtra,
  inputClassName,
  wrapperStyle,
  className,
  ...inputProps
}: FormFieldProps) {
  return (
    <label className={`auth-field ${className ?? ""}`} style={wrapperStyle}>
      <span className="auth-field-row">
        <span className="auth-label">{label}</span>
        {labelExtra}
      </span>
      <input
        {...inputProps}
        className={`auth-input ${error ? "has-error" : ""} ${inputClassName ?? ""}`}
      />
      {error && <span className="auth-field-error">{error}</span>}
      {!error && hint && <span className="auth-hint">{hint}</span>}
    </label>
  );
}
