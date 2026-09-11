import { useState } from "react";
import { NavLink, Outlet, useNavigate } from "react-router-dom";
import { useAuth } from "../../context/AuthContext";
import { Logo } from "./Logo";
import "../../styles/app-tokens.css";

export type ShellNavItem = {
  key: string;
  label: string;
  icon: string;
  to: string;
  end?: boolean;
  badge?: number;
};

export type ActorSummaryItem = {
  label: string;
  count: number;
  color: string;
};

type DashboardShellProps = {
  roleClass: "role-admin" | "role-pme" | "role-acheteur" | "role-partenaire";
  brandSub: string;
  navItems: ShellNavItem[];
  actorsSummary?: ActorSummaryItem[];
  helpBox?: boolean;
  extraNavSection?: { label: string; items: ShellNavItem[] };
};

export function DashboardShell({
  roleClass,
  brandSub,
  navItems,
  actorsSummary,
  helpBox,
  extraNavSection,
}: DashboardShellProps) {
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const { clearSession } = useAuth();
  const navigate = useNavigate();

  function closeOnMobile() {
    if (window.innerWidth <= 960) {
      setSidebarOpen(false);
    }
  }

  function handleLogout() {
    clearSession();
    navigate("/login", { replace: true });
  }

  return (
    <div className={`cedra-app ${roleClass}`}>
      <button
        type="button"
        className="hamburger-btn"
        aria-label="Ouvrir le menu"
        onClick={() => setSidebarOpen((v) => !v)}
      >
        <svg viewBox="0 0 24 24">
          <line x1="3" y1="6" x2="21" y2="6"></line>
          <line x1="3" y1="12" x2="21" y2="12"></line>
          <line x1="3" y1="18" x2="21" y2="18"></line>
        </svg>
      </button>
      <div
        className={`sidebar-backdrop ${sidebarOpen ? "show" : ""}`}
        onClick={() => setSidebarOpen(false)}
      ></div>

      <div className="app">
        <aside className={`sidebar ${sidebarOpen ? "open" : ""}`}>
          <div className="brand">
            <Logo variant="icon" size={26} />
            <div>
              <div className="brand-name">Cedra</div>
              <div className="brand-sub">{brandSub}</div>
            </div>
            <button type="button" className="logout-btn" onClick={handleLogout} aria-label="Se déconnecter" title="Se déconnecter">
              <svg viewBox="0 0 24 24">
                <path d="M9 21H5a2 2 0 01-2-2V5a2 2 0 012-2h4"></path>
                <polyline points="16 17 21 12 16 7"></polyline>
                <line x1="21" y1="12" x2="9" y2="12"></line>
              </svg>
            </button>
          </div>

          <nav className="primary">
            {navItems.map((item) => (
              <NavLink
                key={item.key}
                to={item.to}
                end={item.end}
                onClick={closeOnMobile}
                className={({ isActive }) => `nav-item ${isActive ? "active" : ""}`}
              >
                <svg className="ic">
                  <use href={`#${item.icon}`}></use>
                </svg>
                {item.label}
                {typeof item.badge === "number" && item.badge > 0 && <span className="badge">{item.badge}</span>}
              </NavLink>
            ))}
          </nav>

          {actorsSummary && (
            <>
              <div className="side-section-label">ACTEURS</div>
              {actorsSummary.map((a) => (
                <div className="actor-row" key={a.label}>
                  <span className="actor-dot" style={{ background: a.color }}></span> {a.label}
                  <span className="n">{a.count}</span>
                </div>
              ))}
            </>
          )}

          {extraNavSection && (
            <>
              <div className="side-section-label">{extraNavSection.label}</div>
              {extraNavSection.items.map((item) => (
                <NavLink
                  key={item.key}
                  to={item.to}
                  onClick={closeOnMobile}
                  className={({ isActive }) => `nav-item ${isActive ? "active" : ""}`}
                  style={{ fontSize: "11.5px" }}
                >
                  {item.label}
                </NavLink>
              ))}
            </>
          )}

          <div className="sidebar-spacer"></div>

          {helpBox && (
            <div className="help-box">
              Besoin d'aide ? Contactez notre support.
              <a className="btn" href="#">
                Nous contacter
              </a>
            </div>
          )}
        </aside>
        <div>
          <Outlet />
        </div>
      </div>
    </div>
  );
}
