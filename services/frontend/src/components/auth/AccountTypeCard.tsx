export function AccountTypeCard({
  label,
  description,
  selected,
  onSelect,
}: {
  label: string;
  description: string;
  selected: boolean;
  onSelect: () => void;
}) {
  return (
    <button
      type="button"
      onClick={onSelect}
      className={`auth-account-type-option ${selected ? "is-selected" : ""}`}
      aria-pressed={selected}
    >
      <span className="auth-account-type-dot" />
      <span className="auth-account-type-body">
        <span className="auth-account-type-label">{label}</span>
        <span className="auth-account-type-desc">{description}</span>
      </span>
    </button>
  );
}
