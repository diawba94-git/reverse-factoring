export function ErrorBanner({ message }: { message: string }) {
  return <div className="auth-error-banner">{message}</div>;
}
