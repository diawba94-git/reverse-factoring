import { useEffect, useState } from "react";
import { Navigate } from "react-router-dom";
import { useAuth, roleHomePath } from "../../context/AuthContext";
import { DashboardShell, type ActorSummaryItem } from "../../components/shell/DashboardShell";
import { ADMIN_NAV_ITEMS } from "../../lib/adminNav";
import { detecterDoublons } from "../../lib/doublonsApi";
import { listerLitiges } from "../../lib/litigesApi";
import { apiFetch } from "../../lib/apiClient";
import type { UtilisateurOut } from "../../lib/adminApi";
import "../../styles/admin-dashboard.css";

export function AdminSection() {
  const { session } = useAuth();
  const [doublonsCount, setDoublonsCount] = useState(0);
  const [litigesCount, setLitigesCount] = useState(0);
  const [actorsSummary, setActorsSummary] = useState<ActorSummaryItem[]>();

  const token = session?.accessToken;

  useEffect(() => {
    if (!token) return;
    detecterDoublons(token).then((c) => setDoublonsCount(c.length)).catch(() => {});
    listerLitiges({ statut: "ouvert" }, token).then((l) => setLitigesCount(l.length)).catch(() => {});
    Promise.all([
      apiFetch<{ id: string }[]>("/entreprises?type=PME", { token }),
      apiFetch<{ id: string }[]>("/entreprises?type=GRANDE_ENTREPRISE", { token }),
      apiFetch<{ id: string }[]>("/entreprises?type=PARTENAIRE_FINANCIER", { token }),
      apiFetch<UtilisateurOut[]>("/utilisateurs?role=admin", { token }),
    ])
      .then(([pme, acheteurs, partenaires, admins]) => {
        setActorsSummary([
          { label: "PME", count: pme.length, color: "var(--green)" },
          { label: "Acheteurs", count: acheteurs.length, color: "var(--blue)" },
          { label: "Partenaires", count: partenaires.length, color: "var(--violet)" },
          { label: "Admins", count: admins.length, color: "var(--amber)" },
        ]);
      })
      .catch(() => {});
  }, [token]);

  if (!session) return <Navigate to="/login" replace />;
  if (session.user.role !== "admin") return <Navigate to={roleHomePath(session.user.role)} replace />;

  const navItems = ADMIN_NAV_ITEMS.map((item) => {
    if (item.key === "doublons") return { ...item, badge: doublonsCount };
    if (item.key === "litiges") return { ...item, badge: litigesCount };
    return item;
  });

  return (
    <DashboardShell
      roleClass="role-admin"
      brandSub="ADMINISTRATION"
      navItems={navItems}
      actorsSummary={actorsSummary}
    />
  );
}
