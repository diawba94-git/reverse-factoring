import type { ReactNode } from "react";
import { Logo } from "../../components/shell/Logo";

export function AuthLayout({ children }: { children: ReactNode }) {
  return (
    <div className="auth-page">
      <div className="auth-logo">
        <Logo variant="icon" size={30} />
        <div className="auth-logo-text">
          <div className="auth-logo-name">Cedra</div>
          <div className="auth-logo-tagline">AFFACTURAGE INVERSÉ</div>
        </div>
      </div>

      {children}

      <div className="auth-page-footer">
        <span>Assistance</span>
        <span>·</span>
        <span>Conditions d'utilisation</span>
        <span>·</span>
        <span>Sénégal · Mali · Côte d'Ivoire</span>
      </div>
    </div>
  );
}
