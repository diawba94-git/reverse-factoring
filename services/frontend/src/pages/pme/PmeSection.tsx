import { useEffect, useState } from "react";
import { Navigate } from "react-router-dom";
import { useAuth, roleHomePath } from "../../context/AuthContext";
import { PmeProvider, usePme } from "../../context/PmeContext";
import { DashboardShell } from "../../components/shell/DashboardShell";
import { PME_NAV_ITEMS } from "../../lib/pmeNav";
import { listerNotificationsPme } from "../../lib/pmeApi";
import "../../styles/pme-dashboard.css";

export function PmeSection() {
  const { session } = useAuth();
  const [badgeNotifications, setBadgeNotifications] = useState(0);

  const token = session?.accessToken;
  const role = session?.user.role;
  useEffect(() => {
    if (!token || role !== "membre_pme") return;
    listerNotificationsPme(token)
      .then((notifications) => setBadgeNotifications(notifications.filter((n) => !n.lu).length))
      .catch(() => {});
  }, [token, role]);

  if (!session) return <Navigate to="/login" replace />;
  if (session.user.role !== "admin" && session.user.role !== "membre_pme") {
    return <Navigate to={roleHomePath(session.user.role)} replace />;
  }

  const navItems = PME_NAV_ITEMS.map((item) =>
    item.key === "notifications" ? { ...item, badge: badgeNotifications } : item,
  );

  return (
    <PmeProvider>
      <DashboardShell
        roleClass="role-pme"
        brandSub="PME"
        navItems={navItems}
        helpBox
      />
    </PmeProvider>
  );
}

export function PmeGate({ children }: { children: React.ReactNode }) {
  const { isAdmin, pmeId, pmesDisponibles, selectionnerPme } = usePme();

  if (isAdmin && !pmeId) {
    return (
      <>
        <div className="generic-topbar">
          <h1>Sélectionnez une PME</h1>
        </div>
        <main>
          <div className="empty-state" style={{ display: "flex", flexDirection: "column", gap: 12, alignItems: "center" }}>
            <div>En tant qu'administrateur, choisissez d'abord la PME pour laquelle agir.</div>
            <select
              className="field-select"
              style={{ maxWidth: 320, width: "100%", border: "1px solid var(--line)", borderRadius: 7, padding: "9px 11px" }}
              value={pmeId ?? ""}
              onChange={(e) => selectionnerPme(e.target.value)}
            >
              <option value="" disabled>
                Sélectionnez une PME
              </option>
              {pmesDisponibles?.map((p) => (
                <option key={p.id} value={p.id}>
                  {p.raison_sociale}
                </option>
              ))}
            </select>
          </div>
        </main>
      </>
    );
  }

  return <>{children}</>;
}
