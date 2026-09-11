import { useEffect, useState } from "react";
import { Navigate } from "react-router-dom";
import { useAuth, roleHomePath } from "../../context/AuthContext";
import { DashboardShell } from "../../components/shell/DashboardShell";
import { PARTENAIRE_NAV_ITEMS } from "../../lib/partenaireNav";
import { listerAvancesPartenaire } from "../../lib/partenaireApi";
import { listerAvoirs } from "../../lib/avoirsApi";
import "../../styles/partenaire-dashboard.css";

export function PartenaireSection() {
  const { session } = useAuth();
  const [badgeOpportunites, setBadgeOpportunites] = useState(0);
  const [badgeAvoirs, setBadgeAvoirs] = useState(0);

  const token = session?.accessToken;
  useEffect(() => {
    if (!token) return;
    listerAvancesPartenaire({ statut: "en_attente_validation" }, token)
      .then((avances) => setBadgeOpportunites(avances.length))
      .catch(() => {});
    listerAvoirs({ statut: "confirme_par_acheteur" }, token)
      .then((avoirs) =>
        setBadgeAvoirs(avoirs.filter((a) => a.effet_applique === "solde_reduit" || a.effet_applique === "creance_creee").length),
      )
      .catch(() => {});
  }, [token]);

  if (!session) return <Navigate to="/login" replace />;
  if (session.user.role !== "agent_financier") {
    return <Navigate to={roleHomePath(session.user.role)} replace />;
  }

  const navItems = PARTENAIRE_NAV_ITEMS.map((item) => {
    if (item.key === "opportunites") return { ...item, badge: badgeOpportunites };
    if (item.key === "avoirs") return { ...item, badge: badgeAvoirs };
    return item;
  });

  return (
    <DashboardShell
      roleClass="role-partenaire"
      brandSub="PARTENAIRE FINANCIER"
      navItems={navItems}
      helpBox
    />
  );
}
